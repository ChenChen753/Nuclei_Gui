import subprocess
import json
import os
import tempfile
import threading
import datetime as import_datetime
import traceback
from PyQt5.QtCore import QThread, pyqtSignal

# 导入日志模块
from core.logger import get_logger, log_exception

# 获取模块日志器
logger = get_logger("scanner")

def log_debug(msg):
    """文件调试日志"""
    try:
        with open("debug_tracing.log", "a", encoding='utf-8') as f:
            timestamp = import_datetime.datetime.now().strftime("%H:%M:%S.%f")
            f.write(f"[{timestamp}] {msg}\n")
    except (IOError, OSError):
        pass

class NucleiScanThread(QThread):
    """
    Nuclei 扫描线程
    """
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int, str)
    
    # 分批阈值
    BATCH_THRESHOLD = 100
    BATCH_SIZE = 50
    
    def __init__(self, targets, templates, rate_limit=150, bulk_size=25, custom_args=None, use_native_scanner=False):
        super().__init__()
        self.targets = self._normalize_targets(targets)
        self.templates = templates
        self.rate_limit = rate_limit
        self.bulk_size = bulk_size
        self.custom_args = custom_args or []
        self.use_native_scanner = use_native_scanner
        self._is_running = True
        self._is_paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._lock = threading.Lock()
        self.process = None
        self.native_scanner = None
        self.scanned_target_index = 0
        self.current_batch_index = 0
        
        log_debug(f"Init: {len(targets)} targets, {len(templates)} templates")
    
    def _normalize_targets(self, targets):
        log_debug(f"_normalize_targets 输入: 类型={type(targets)}, 数量={len(targets) if targets else 0}")
        if targets:
            log_debug(f"_normalize_targets 第一个元素: {targets[0]}, 类型={type(targets[0])}")
        normalized = []
        for target in targets:
            if not isinstance(target, str):
                log_debug(f"_normalize_targets 跳过非字符串: {target}, 类型={type(target)}")
                continue
            target = target.strip()
            if not target: continue
            if not target.startswith(('http://', 'https://')):
                target = 'http://' + target
            normalized.append(target)
        log_debug(f"_normalize_targets 输出: 数量={len(normalized)}")
        return normalized

    def run(self):
        log_debug("run() 方法被调用")
        try:
            self.log_signal.emit(f"[DEBUG] UI信道测试: run入口")
            
            if self.use_native_scanner:
                log_debug("模式: Native Scanner")
                self.run_native_mode()
                return

            log_debug(f"模式: Nuclei Batch (Targets={len(self.targets)})")
            self.run_batch_mode()
            log_debug("run() 执行完毕")
            
        except Exception as e:
            err = traceback.format_exc()
            log_debug(f"run() 异常: {e}\n{err}")
            self.log_signal.emit(f"[ERROR] 线程异常: {e}")
            self.finished_signal.emit()

    def run_native_mode(self):
        # 原生模式暂不调试
        pass

    def stop(self):
        log_debug("stop() 被调用")
        with self._lock:
            self._is_running = False
            if self.process:
                try:
                    self.process.terminate()
                except OSError:
                    pass
            self._pause_event.set()

    def pause(self):
        log_debug("pause() 被调用")
        with self._lock:
            if self._is_running and not self._is_paused:
                self._is_paused = True
                self._pause_event.clear()
                return True
        return False
    
    def resume(self):
        log_debug("resume() 被调用")
        with self._lock:
            if self._is_running and self._is_paused:
                self._is_paused = False
                self._pause_event.set()
                return True
        return False
    
    def is_paused(self):
        with self._lock:
            return self._is_paused

    def run_batch_mode(self):
        log_debug("run_batch_mode 开始")
        total_targets = len(self.targets)

        # 直接一次性扫描所有目标，不再分批
        log_debug(f"准备扫描所有 {total_targets} 个目标")
        self.run_single_mode(self.targets)
        log_debug("扫描完成")

        self.finished_signal.emit()

    def run_single_mode(self, targets):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        nuclei_cmd = "nuclei"
        bin_nuclei = os.path.join(project_root, 'bin', 'nuclei.exe')
        if os.path.exists(bin_nuclei):
            nuclei_cmd = bin_nuclei

        log_debug(f"使用 Nuclei 路径: {nuclei_cmd}")
        log_debug(f"目标数量: {len(targets)}, 模板数量: {len(self.templates)}")

        # 检查模板是否为空
        if not self.templates:
            self.log_signal.emit("[WARNING] 没有指定 POC 模板，扫描将跳过")
            log_debug("WARNING: templates 列表为空!")
            return

        try:
            cmd = [nuclei_cmd]
            
            tmp_target_path = None
            if len(targets) == 1:
                cmd.extend(["-u", targets[0]])
            else:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as tmp_target:
                    tmp_target_path = tmp_target.name
                    for t in targets:
                        tmp_target.write(t + '\n')
                cmd.extend(["-l", tmp_target_path])

            cmd.extend([
                "-jsonl",
                "-rl", str(self.rate_limit),
                "-bs", str(self.bulk_size),
                "-stats",
                "-stats-interval", "3"
            ])
            
            # POC 处理
            for t in self.templates:
                cmd.extend(["-t", t])
                
            if self.custom_args:
                cmd.extend(self.custom_args)
            
            log_debug(f"启动 subprocess: {' '.join(cmd)}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            env = os.environ.copy()
            bin_dir = os.path.join(project_root, 'bin')
            env["PATH"] = bin_dir + os.pathsep + env["PATH"]
            env["PYTHONIOENCODING"] = "utf-8"
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='ignore',
                env=env
            )
            
            log_debug(f"Subprocess PID: {self.process.pid}")
            
            for line in iter(self.process.stdout.readline, ''):
                if not self._is_running:
                    break
                line = line.strip()
                if line:
                    log_debug(f"Output: {line[:100]}") # 记录部分输出证明有动静
                    try:
                        result = json.loads(line)
                        if 'template-id' in result:
                            self.result_signal.emit(result)
                        elif 'percent' in result:
                            # 解析 nuclei stats 输出的进度
                            # nuclei stats 格式可能包含: percent, requests, total, hosts 等
                            percent = result.get('percent', 0)
                            # 确保 percent 是有效数值
                            try:
                                percent = float(percent)
                                # 限制在 0-99 范围内，100% 由 finished_signal 处理
                                percent = max(0, min(99, int(percent)))
                            except (ValueError, TypeError):
                                percent = 0

                            # 只有当进度大于0时才发送，避免重置进度条
                            if percent > 0:
                                self.progress_signal.emit(percent, 100, f"扫描进度")
                    except json.JSONDecodeError:
                        # 非 JSON 输出
                        self.log_signal.emit(line)

            self.process.wait()
            log_debug("Subprocess wait() 返回")
            
        except Exception as e:
            log_debug(f"run_single_mode 异常: {e}\n{traceback.format_exc()}")
            logger.error(f"run_single_mode 异常: {e}")
        finally:
            if tmp_target_path and os.path.exists(tmp_target_path):
                try:
                    os.remove(tmp_target_path)
                except OSError:
                    pass
