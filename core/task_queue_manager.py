"""
扫描任务队列管理器 - 支持多任务排队、暂停/恢复/取消、优先级、断点续扫
独立模块，不修改现有扫描逻辑
"""
import json
import os
import time
import uuid
import heapq
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QWaitCondition, QTimer, QCoreApplication

from core.logger import get_logger

logger = get_logger("task_queue")


class TaskPriority(IntEnum):
    """任务优先级（数值越小优先级越高）"""
    CRITICAL = 0    # 紧急
    HIGH = 1        # 高
    NORMAL = 2      # 普通
    LOW = 3         # 低
    BACKGROUND = 4  # 后台


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "等待中"
    RUNNING = "运行中"
    PAUSED = "已暂停"
    COMPLETED = "已完成"
    CANCELLED = "已取消"
    FAILED = "失败"
    SCHEDULED = "已计划"


@dataclass
class CheckpointData:
    """断点续扫检查点数据"""
    scanned_targets: List[str] = field(default_factory=list)
    remaining_targets: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    last_update: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CheckpointData':
        return cls(**data)


@dataclass
class ScanTask:
    """扫描任务数据类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    targets: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    progress: int = 0  # 0-100
    result_count: int = 0
    vuln_count: int = 0
    error_message: str = ""
    custom_args: Dict = field(default_factory=dict)
    checkpoint: Optional[CheckpointData] = None
    retry_count: int = 0
    max_retries: int = 3
    tags: List[str] = field(default_factory=list)
    
    def __lt__(self, other):
        """用于优先级队列比较"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'targets': self.targets,
            'templates': self.templates,
            'status': self.status.value,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'scht': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'progress': self.progress,
            'result_count': self.result_count,
            'vuln_count': self.vuln_count,
            'error_message': self.error_message,
            'checkpoint': self.checkpoint.to_dict() if self.checkpoint else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'tags': self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScanTask':
        """从字典创建任务"""
        task = cls()
        task.id = data.get('id', task.id)
        task.name = data.get('name', '')
        task.targets = data.get('targets', [])
        task.templates = data.get('templates', [])
        task.status = TaskStatus(data.get('status', TaskStatus.PENDING.value))
        task.priority = TaskPriority(data.get('priority', TaskPriority.NORMAL.value))
        
        if data.get('created_at'):
            task.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            task.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            task.completed_at = datetime.fromisoformat(data['completed_at'])
        if data.get('scheduled_at'):
            task.scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        
        task.progress = data.get('progress', 0)
        task.result_count = data.get('result_count', 0)
        task.vuln_count = data.get('vuln_count', 0)
        task.results = data.get('results', []) # 导入结果
        task.error_message = data.get('error_message', '')
        task.custom_args = data.get('custom_args', {})
        
        if data.get('checkpoint'):
            task.checkpoint = CheckpointData.from_dict(data['checkpoint'])
        
        task.retry_count = data.get('retry_count', 0)
        task.max_retries = data.get('max_retries', 3)
        task.tags = data.get('tags', [])
        
        return task


class TaskQueueWorker(QThread):
    """任务队列执行线程"""
    
    # 信号
    task_started = pyqtSignal(str)  # 任务ID
    task_progress = pyqtSignal(str, int)  # 任务ID, 进度
    task_completed = pyqtSignal(str, dict)  # 任务ID, 结果
    task_failed = pyqtSignal(str, str)  # 任务ID, 错误信息
    log_signal = pyqtSignal(str)  # 日志
    result_found = pyqtSignal(str, dict)  # 任务ID, 单个漏洞结果
    
    def __init__(self, task: ScanTask, scan_config: Dict = None):
        super().__init__()
        self.task = task
        self.scan_config = scan_config or {}
        self._is_paused = False
        self._is_cancelled = False
        self._pause_mutex = QMutex()
        self._pause_condition = QWaitCondition()
        self._scan_thread = None
    
    def run(self):
        """执行任务"""
        self.task.status = TaskStatus.RUNNING
        self.task.started_at = datetime.now()
        self.task_started.emit(self.task.id)
        self.log_signal.emit(f"[DEBUG] Worker 线程已启动 (TaskID: {self.task.id})")

        try:
            # 导入扫描线程
            self.log_signal.emit("[DEBUG] 正在导入 NucleiScanThread...")
            from core.nuclei_runner import NucleiScanThread
            self.log_signal.emit("[DEBUG] NucleiScanThread 导入成功")

            # 检查是否取消
            if self._is_cancelled:
                self.log_signal.emit("[DEBUG] 任务已取消，终止执行")
                self.task.status = TaskStatus.CANCELLED
                return

            # 调试：打印 targets 和 templates 信息
            self.log_signal.emit(f"[DEBUG] Targets 类型: {type(self.task.targets)}")
            self.log_signal.emit(f"[DEBUG] Targets 数量: {len(self.task.targets)}")
            if self.task.targets:
                self.log_signal.emit(f"[DEBUG] 第一个 Target: {self.task.targets[0]}")
                self.log_signal.emit(f"[DEBUG] 第一个 Target 类型: {type(self.task.targets[0])}")
            else:
                self.log_signal.emit("[WARNING] Targets 列表为空!")

            self.log_signal.emit(f"[DEBUG] Templates 数量: {len(self.task.templates)}")
            if self.task.templates:
                self.log_signal.emit(f"[DEBUG] 第一个 Template: {self.task.templates[0]}")
            else:
                self.log_signal.emit("[WARNING] Templates 列表为空!")

            self.log_signal.emit(f"[DEBUG] 正在创建 NucleiScanThread...")

            # 处理 custom_args：如果是字典则转换为列表，如果是列表则直接使用
            custom_args = self.task.custom_args
            if isinstance(custom_args, dict):
                # 将字典转换为命令行参数列表
                args_list = []
                for key, value in custom_args.items():
                    if value is True:
                        args_list.append(f"-{key}")
                    elif value is not False and value is not None:
                        args_list.append(f"-{key}")
                        args_list.append(str(value))
                custom_args = args_list
            elif not isinstance(custom_args, list):
                custom_args = []

            # 创建扫描线程
            self._scan_thread = NucleiScanThread(
                targets=self.task.targets,
                templates=self.task.templates,
                rate_limit=self.scan_config.get('rate_limit', 150),
                bulk_size=self.scan_config.get('bulk_size', 25),
                custom_args=custom_args,
                use_native_scanner=self.scan_config.get('use_native_scanner', False)
            )
            self.log_signal.emit(f"[DEBUG] NucleiScanThread 创建成功, Templates: {len(self.task.templates)}, 第一个: {self.task.templates[0] if self.task.templates else 'None'}")
            
            # 连接信号
            results = []
            vuln_count = [0]
            
            def on_result(result):
                results.append(result)
                vuln_count[0] += 1
                self.task.vuln_count = vuln_count[0]
                self.result_found.emit(self.task.id, result)
            
            def on_progress(current, total, msg):
                if total > 0:
                    progress = int(current / total * 100)
                    self.task.progress = progress
                    self.task_progress.emit(self.task.id, progress)
            
            def on_log(msg):
                self.log_signal.emit(f"[{self.task.name}] {msg}")
            
            self._scan_thread.result_signal.connect(on_result)
            self._scan_thread.progress_signal.connect(on_progress)
            self._scan_thread.log_signal.connect(on_log)

            # 连接 finished_signal 以便调试
            def on_finished():
                self.log_signal.emit("[DEBUG] NucleiScanThread finished_signal 收到")

            self._scan_thread.finished_signal.connect(on_finished)

            self.log_signal.emit("[DEBUG] 正在启动 NucleiScanThread.start()...")
            # 启动扫描
            self._scan_thread.start()
            self.log_signal.emit("[DEBUG] NucleiScanThread.start() 已调用")

            # 调试：写入文件
            def debug_log(msg):
                try:
                    with open("task_worker_debug.log", "a", encoding="utf-8") as f:
                        from datetime import datetime
                        f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')}] {msg}\n")
                except:
                    pass

            debug_log("NucleiScanThread.start() 已调用")

            # 等待完成，同时支持暂停和取消
            loop_count = 0
            while self._scan_thread.isRunning():
                loop_count += 1
                if loop_count % 100 == 0:  # 每5秒输出一次
                    self.log_signal.emit(f"[DEBUG] 等待扫描完成... (循环 {loop_count})")
                    debug_log(f"等待扫描完成... (循环 {loop_count}), isRunning={self._scan_thread.isRunning()}")

                # 检查暂停
                self._pause_mutex.lock()
                while self._is_paused and not self._is_cancelled:
                    self.task.status = TaskStatus.PAUSED
                    self._pause_condition.wait(self._pause_mutex)
                    if not self._is_paused:
                        self.task.status = TaskStatus.RUNNING
                self._pause_mutex.unlock()

                # 检查取消
                if self._is_cancelled:
                    self._scan_thread.stop()
                    self._scan_thread.wait(5000)
                    self.task.status = TaskStatus.CANCELLED
                    return

                # 短暂等待
                if self._scan_thread.wait(50):
                    # 线程已结束
                    self.log_signal.emit("[DEBUG] wait() 返回 True，线程已结束")
                    break

                # 处理事件循环
                QCoreApplication.processEvents()
            
            self.log_signal.emit("[DEBUG] 子线程 isRunning() 返回 False, 循环结束")
            
            # 任务完成
            self.task.status = TaskStatus.COMPLETED
            self.task.completed_at = datetime.now()
            self.task.progress = 100
            self.task.result_count = len(results)
            
            self.task_completed.emit(self.task.id, {
                'results': results,
                'vuln_count': vuln_count[0],
            })
            
        except Exception as e:
            self.task.status = TaskStatus.FAILED
            self.task.error_message = str(e)
            self.task_failed.emit(self.task.id, str(e))
    
    def pause(self):
        """暂停任务"""
        self._pause_mutex.lock()
        self._is_paused = True
        self._pause_mutex.unlock()
    
    def resume(self):
        """恢复任务"""
        self._pause_mutex.lock()
        self._is_paused = False
        self._pause_condition.wakeAll()
        self._pause_mutex.unlock()
    
    def cancel(self):
        """取消任务"""
        self._is_cancelled = True
        if self._is_paused:
            self.resume()  # 先恢复以便退出等待


class TaskQueueManager(QObject):
    """任务队列管理器"""
    
    # 信号
    queue_updated = pyqtSignal()  # 队列更新
    task_added = pyqtSignal(str)  # 任务添加
    task_removed = pyqtSignal(str)  # 任务移除
    task_status_changed = pyqtSignal(str, str)  # 任务ID, 新状态
    
    def __init__(self, max_concurrent: int = 1):
        """
        初始化任务队列管理器
        
        参数:
            max_concurrent: 最大并发任务数（默认为1，即串行执行）
        """
        super().__init__()
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, ScanTask] = {}
        self._workers: Dict[str, TaskQueueWorker] = {}
        self._queue: List[str] = []  # 任务ID队列
        self._scan_config = {}
    
    def set_scan_config(self, config: Dict):
        """设置扫描配置"""
        self._scan_config = config
    
    def add_task(self, name: str, targets: List[str], templates: List[str],
                 priority: TaskPriority = TaskPriority.NORMAL,
                 custom_args: Dict = None,
                 scheduled_at: datetime = None,
                 tags: List[str] = None,
                 auto_start: bool = False) -> str:
        """
        添加任务到队列
        
        参数:
            name: 任务名称
            targets: 目标列表
            templates: POC 模板路径列表
            priority: 任务优先级
            custom_args: 自定义参数
            scheduled_at: 定时执行时间
            tags: 任务标签
            auto_start: 是否自动启动任务（默认False，仅加入队列不启动）
        
        返回:
            任务ID
        """
        task = ScanTask(
            name=name,
            targets=targets,
            templates=templates,
            priority=priority,
            custom_args=custom_args or {},
            scheduled_at=scheduled_at,
            tags=tags or [],
            status=TaskStatus.SCHEDULED if scheduled_at else TaskStatus.PENDING
        )
        
        self._tasks[task.id] = task
        self._queue.append(task.id)
        
        self.task_added.emit(task.id)
        self.queue_updated.emit()
        
        logger.info(f"任务已添加: {task.id} - {name} (优先级: {priority.name}, 自动启动: {auto_start})")
        
        # 只有设置了 auto_start=True 且不是定时任务时才自动启动
        if auto_start and not scheduled_at:
            self._try_start_next()
        
        return task.id
    
    def register_external_task(self, task_id: str, name: str, targets: List[str], 
                                templates: List[str], status: TaskStatus = TaskStatus.RUNNING) -> str:
        """
        注册外部启动的任务（如通过 start_scan 直接启动的扫描）
        用于让任务管理页面能够显示和跟踪这些任务
        
        参数:
            task_id: 任务ID（可自定义或使用默认生成）
            name: 任务名称
            targets: 目标列表
            templates: POC 模板路径列表
            status: 任务状态（默认为运行中）
        
        返回:
            任务ID
        """
        task = ScanTask(
            id=task_id,
            name=name,
            targets=targets,
            templates=templates,
            status=status,
        )
        task.started_at = datetime.now()
        
        self._tasks[task.id] = task
        self._queue.append(task.id)
        
        self.task_added.emit(task.id)
        self.queue_updated.emit()
        
        logger.info(f"外部任务已注册: {task.id} - {name} (状态: {status.value})")
        return task.id
    
    def update_task_progress(self, task_id: str, progress: int, vuln_count: int = None):
        """更新任务进度"""
        task = self._tasks.get(task_id)
        if task:
            task.progress = progress
            if vuln_count is not None:
                task.vuln_count = vuln_count
            self.queue_updated.emit()
    
    def update_task_status(self, task_id: str, status: TaskStatus, error_message: str = None):
        """更新任务状态"""
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
                task.progress = 100
            if error_message:
                task.error_message = error_message
            self.task_status_changed.emit(task_id, status.value)
            self.queue_updated.emit()
    
    def change_priority(self, task_id: str, new_priority: TaskPriority) -> bool:
        """修改任务优先级"""
        task = self._tasks.get(task_id)
        if not task or task.status not in [TaskStatus.PENDING, TaskStatus.SCHEDULED]:     return False
        
        task.priority = new_priority
        self.queue_updated.emit()
        logger.info(f"任务 {task_id} 优先级已修改为 {new_priority.name}")
        return True
    
    def get_worker(self, task_id: str):
        """获取任务的工作线程"""
        return self._workers.get(task_id)
    
    def _try_start_next(self):
        """尝试启动下一个等待中的任务（按优先级排序）"""
        # 统计运行中的任务数
        running_count = sum(
            1 for t in self._tasks.values()
            if t.status == TaskStatus.RUNNING
        )
        
        if running_count >= self.max_concurrent:
            return
        
        # 找到下一个等待中的任务（按优先级排序）
        pending_tasks = [
            self._tasks[task_id] for task_id in self._queue
            if task_id in self._tasks and self._tasks[task_id].status == TaskStatus.PENDING
        ]
        
        if pending_tasks:
            # 按优先级和创建时间排序
            pending_tasks.sort(key=lambda t: (t.priority, t.created_at))
            self._start_task(pending_tasks[0].id)
    
    def start_task(self, task_id: str, pre_start_callback: Callable = None) -> bool:
        """手动启动任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
            
        if task.status == TaskStatus.RUNNING:
            return False
            
        # 如果任务已完成或失败，重置状态以便重新运行
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.status = TaskStatus.PENDING
            task.progress = 0
            task.result_count = 0
            task.vuln_count = 0
            # 这里的重置可能需要更全面，例如清除 results？
            # 暂时保持简单，ScanTask 内部会更新 started_at
            
        self._start_task(task_id, pre_start_callback)
        return True
    
    def _start_task(self, task_id: str, pre_start_callback: Callable = None):
        """启动任务"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        worker = TaskQueueWorker(task, self._scan_config)
        worker.task_started.connect(self._on_task_started)
        worker.task_progress.connect(self._on_task_progress)
        worker.task_completed.connect(self._on_task_completed)
        worker.task_failed.connect(self._on_task_failed)
        
        self._workers[task_id] = worker
        
        # 在启动前执行回调（用于 UI 绑定信号，防止丢失初始化日志）
        if pre_start_callback:
            try:
                pre_start_callback(task_id)
            except Exception as e:
                logger.error(f"任务启动回调执行失败: {e}")
        
        worker.start()
    
    def _on_task_started(self, task_id: str):
        """任务开始"""
        self.task_status_changed.emit(task_id, TaskStatus.RUNNING.value)
        self.queue_updated.emit()
    
    def _on_task_progress(self, task_id: str, progress: int):
        """任务进度更新"""
        self.queue_updated.emit()
    
    def _on_task_completed(self, task_id: str, result: Dict):
        """任务完成"""
        logger.info(f"任务完成: {task_id}")
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.progress = 100  # 确保进度设为100
            task.completed_at = datetime.now()
            # 保存结果
            if result and 'results' in result:
                task.results = result['results']
                task.result_count = len(task.results)
                task.vuln_count = result.get('vuln_count', 0)

        # 先发出状态变更信号，让 UI 有机会处理
        self.task_status_changed.emit(task_id, TaskStatus.COMPLETED.value)
        self.queue_updated.emit()

        # 延迟清理 worker，确保所有信号处理完成
        if task_id in self._workers:
            worker = self._workers.pop(task_id)
            # 使用 deleteLater 让事件循环处理完所有待处理的信号后再删除
            worker.deleteLater()

        # 尝试启动下一个任务
        self._try_start_next()
    
    def _on_task_failed(self, task_id: str, error: str):
        """任务失败"""
        logger.error(f"任务失败: {task_id}, 错误: {error}")
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error

        # 先发出状态变更信号
        self.task_status_changed.emit(task_id, TaskStatus.FAILED.value)
        self.queue_updated.emit()

        # 延迟清理 worker
        if task_id in self._workers:
            worker = self._workers.pop(task_id)
            worker.deleteLater()

        # 尝试启动下一个任务
        self._try_start_next()
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        worker = self._workers.get(task_id)
        if worker:
            worker.pause()
            self.task_status_changed.emit(task_id, TaskStatus.PAUSED.value)
            self.queue_updated.emit()
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        worker = self._workers.get(task_id)
        if worker:
            worker.resume()
            self.task_status_changed.emit(task_id, TaskStatus.RUNNING.value)
            self.queue_updated.emit()
            return True
        return False
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # 如果任务正在运行，停止 worker
        worker = self._workers.get(task_id)
        if worker:
            worker.cancel()
            worker.wait(5000)
            self._workers.pop(task_id, None)
        
        task.status = TaskStatus.CANCELLED
        self.task_status_changed.emit(task_id, TaskStatus.CANCELLED.value)
        self.queue_updated.emit()
        
        # 尝试启动下一个任务
        self._try_start_next()
        return True
    
    def start_task_manually(self, task_id: str) -> bool:
        """
        手动启动等待中的任务
        
        参数:
            task_id: 任务ID
        
        返回:
            是否成功启动
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"任务 {task_id} 不存在")
            return False
        
        if task.status != TaskStatus.PENDING:
            logger.warning(f"任务 {task_id} 状态为 {task.status.value}，无法启动")
            return False
        
        # 检查是否已达到最大并发数
        running_count = sum(
            1 for t in self._tasks.values()
            if t.status == TaskStatus.RUNNING
        )
        
        if running_count >= self.max_concurrent:
            logger.warning(f"已达到最大并发数 {self.max_concurrent}，无法启动更多任务")
            return False
        
        self._start_task(task_id)
        logger.info(f"任务 {task_id} 已手动启动")
        return True
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[ScanTask]:
        """获取指定状态的任务列表"""
        return [t for t in self._tasks.values() if t.status == status]
    
    def remove_task(self, task_id: str) -> bool:
        """从队列中移除任务（仅限已完成/已取消/失败的任务）"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            return False  # 运行中的任务需要先取消
        
        if task_id in self._queue:
            self._queue.remove(task_id)
        self._tasks.pop(task_id, None)
        
        self.task_removed.emit(task_id)
        self.queue_updated.emit()
        return True
    
    def get_task(self, task_id: str) -> Optional[ScanTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScanTask]:
        """获取所有任务（按队列顺序）"""
        return [self._tasks[tid] for tid in self._queue if tid in self._tasks]
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        tasks = self.get_all_tasks()
        return {
            'total': len(tasks),
            'pending': sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            'running': sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            'paused': sum(1 for t in tasks if t.status == TaskStatus.PAUSED),
            'completed': sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            'cancelled': sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
            'failed': sum(1 for t in tasks if t.status == TaskStatus.FAILED),
        }
    
    def clear_completed(self):
        """清除已完成的任务"""
        completed_ids = [
            tid for tid, task in self._tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]
        ]
        for tid in completed_ids:
            self.remove_task(tid)


# 单例模式
_queue_manager_instance = None

def get_task_queue_manager() -> TaskQueueManager:
    """获取任务队列管理器单例"""
    global _queue_manager_instance
    
    if _queue_manager_instance is None:
        _queue_manager_instance = TaskQueueManager()
    
    return _queue_manager_instance
