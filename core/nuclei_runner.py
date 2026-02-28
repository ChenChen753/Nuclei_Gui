import subprocess
import json
import os
import tempfile
import threading
import datetime as import_datetime
import traceback
import platform
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

def get_nuclei_path():
    """
    跨平台获取 Nuclei 可执行文件路径
    优先级：bin目录下的二进制文件 > 系统PATH中的nuclei
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    bin_dir = os.path.join(project_root, 'bin')
    
    # 根据操作系统确定二进制文件名
    system = platform.system().lower()
    if system == 'windows':
        nuclei_binary = 'nuclei.exe'
    elif system == 'darwin':  # macOS
        nuclei_binary = 'nuclei_darwin'
    elif system == 'linux':
        nuclei_binary = 'nuclei_linux'
    else:
        nuclei_binary = 'nuclei'  # 默认
    
    # 检查 bin 目录下是否有对应的二进制文件
    bin_nuclei_path = os.path.join(bin_dir, nuclei_binary)
    if os.path.exists(bin_nuclei_path):
        # 确保文件有执行权限（Unix系统）
        if system in ['darwin', 'linux']:
            try:
                os.chmod(bin_nuclei_path, 0o755)
            except OSError:
                pass
        log_debug(f"使用 bin 目录下的 Nuclei: {bin_nuclei_path}")
        return bin_nuclei_path
    
    # 检查系统PATH中是否有nuclei
    try:
        result = subprocess.run(['which', 'nuclei'] if system != 'windows' else ['where', 'nuclei'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            system_nuclei = result.stdout.strip().split('\n')[0]
            log_debug(f"使用系统 PATH 中的 Nuclei: {system_nuclei}")
            return system_nuclei
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    
    # 如果都没找到，返回默认的nuclei命令，让系统尝试执行
    log_debug(f"未找到 Nuclei 二进制文件，使用默认命令: nuclei")
    return 'nuclei'

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
        # 使用跨平台的 Nuclei 路径检测
        nuclei_cmd = get_nuclei_path()
        
        log_debug(f"使用 Nuclei 路径: {nuclei_cmd}")
        log_debug(f"当前操作系统: {platform.system()}")
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

            # POC 处理 - 使用临时文件避免命令行长度限制
            tmp_template_path = None
            if len(self.templates) == 1:
                # 单个模板直接用 -t 参数
                cmd.extend(["-t", self.templates[0]])
            else:
                # 多个模板写入临时文件，使用 -t 指向文件
                # 注意：nuclei 支持 -t 参数指向包含模板路径列表的文件
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as tmp_template:
                    tmp_template_path = tmp_template.name
                    for t in self.templates:
                        tmp_template.write(t + '\n')
                log_debug(f"模板列表写入临时文件: {tmp_template_path}, 共 {len(self.templates)} 个模板")
                cmd.extend(["-t", tmp_template_path])

            if self.custom_args:
                cmd.extend(self.custom_args)
            
            log_debug(f"启动 subprocess: {' '.join(cmd)}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            env = os.environ.copy()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
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
            # 清理临时目标文件
            if tmp_target_path and os.path.exists(tmp_target_path):
                try:
                    os.remove(tmp_target_path)
                except OSError:
                    pass
            # 清理临时模板文件
            if tmp_template_path and os.path.exists(tmp_template_path):
                try:
                    os.remove(tmp_template_path)
                except OSError:
                    pass
