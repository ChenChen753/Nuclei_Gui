"""
远程更新模块 - 从 GitHub 检查并下载更新
支持自动检查更新和手动检查更新
更新时保留本地数据库和用户数据
"""
import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
from urllib.parse import urlparse
import requests
from PyQt5.QtCore import QThread, pyqtSignal

from i18n import tr
from core.paths import app_dir, log_dir, user_data_dir

# 项目信息
GITHUB_REPO = "ChenChen753/Nuclei_Gui"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "2.5.5"

PACKAGE_SOURCE = "source"
PACKAGE_WINDOWS_EXE = "windows_exe"
PACKAGE_UNSUPPORTED_BINARY = "unsupported_binary"

# 更新时需要保留的文件/目录（不会被覆盖）
PRESERVE_FILES = [
    "scan_history.db",
    "history.db",
    "debug_tracing.log",
    "config.json",
    "settings.json",
    ".env",
]

PRESERVE_DIRS = [
    "bin",
    "poc_library/custom",
    "poc_library/user_generated",
    "logs",
]


def get_current_version():
    """获取当前版本号"""
    return CURRENT_VERSION


def get_update_package_type():
    """根据当前运行方式选择更新包类型。"""
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            return PACKAGE_WINDOWS_EXE
        return PACKAGE_UNSUPPORTED_BINARY
    return PACKAGE_SOURCE


def _find_windows_exe_asset(assets):
    """从 GitHub Release assets 中选择 Windows GUI exe。"""
    preferred_names = ("nuclei_gui", "nuclei-gui", "nuclei gui", "nucleigui")

    for asset in assets:
        name = asset.get("name", "")
        lower_name = name.lower()
        if not lower_name.endswith(".exe"):
            continue

        url = asset.get("browser_download_url", "")
        if not url:
            continue

        if any(keyword in lower_name for keyword in preferred_names):
            return url

    return ""


def _is_windows_exe_url(download_url):
    """判断下载地址是否指向 Windows exe 资产。"""
    if not download_url:
        return False

    path = urlparse(download_url).path.lower()
    return path.endswith(".exe")


def normalize_update_package_type(download_url, package_type=None):
    """根据运行环境和下载地址兜底修正更新包类型。"""
    if (
        sys.platform == "win32"
        and getattr(sys, "frozen", False)
        and _is_windows_exe_url(download_url)
    ):
        return PACKAGE_WINDOWS_EXE

    if package_type:
        return package_type

    return PACKAGE_SOURCE


def get_system_proxies():
    """获取系统代理设置"""
    proxies = {}

    # 从环境变量获取代理
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

    if http_proxy:
        proxies['http'] = http_proxy
    if https_proxy:
        proxies['https'] = https_proxy

    # 如果没有环境变量，尝试从 Windows 注册表获取
    if not proxies and sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
                proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
                if proxy_enable:
                    proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
                    if proxy_server:
                        if not proxy_server.startswith('http'):
                            proxy_server = f'http://{proxy_server}'
                        proxies['http'] = proxy_server
                        proxies['https'] = proxy_server
        except (WindowsError, FileNotFoundError, OSError):
            pass

    return proxies if proxies else None


def compare_versions(v1, v2):
    """
    比较版本号
    返回: 1 如果 v1 > v2, -1 如果 v1 < v2, 0 如果相等
    """
    def parse_version(v):
        # 移除 'v' 前缀
        v = v.lstrip('v').lstrip('V')
        parts = []
        for part in v.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        return parts

    p1 = parse_version(v1)
    p2 = parse_version(v2)

    # 补齐长度
    max_len = max(len(p1), len(p2))
    p1.extend([0] * (max_len - len(p1)))
    p2.extend([0] * (max_len - len(p2)))

    for a, b in zip(p1, p2):
        if a > b:
            return 1
        elif a < b:
            return -1
    return 0


class UpdateCheckThread(QThread):
    """检查更新线程"""
    check_finished = pyqtSignal(bool, str, str, str, str)  # has_update, latest_version, download_url, release_notes, package_type
    error_signal = pyqtSignal(str)

    def __init__(self, timeout=10):
        super().__init__()
        self.timeout = timeout

    def run(self):
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Nuclei-GUI-Updater'
            }

            # 获取系统代理
            proxies = get_system_proxies()

            response = requests.get(GITHUB_API_URL, headers=headers, timeout=self.timeout, proxies=proxies)

            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('tag_name', '').lstrip('v')
                release_notes = data.get('body', tr("update.no_release_notes"))

                package_type = get_update_package_type()
                assets = data.get('assets', [])

                if package_type == PACKAGE_WINDOWS_EXE:
                    download_url = _find_windows_exe_asset(assets)
                elif package_type == PACKAGE_SOURCE:
                    download_url = data.get('zipball_url', '')
                else:
                    self.error_signal.emit(tr("update.binary_update_unsupported"))
                    return

                # 比较版本
                current = get_current_version()
                has_update = compare_versions(latest_version, current) > 0

                if has_update and not download_url:
                    self.error_signal.emit(tr("update.no_compatible_asset"))
                    return

                self.check_finished.emit(has_update, latest_version, download_url, release_notes, package_type)
            elif response.status_code == 404:
                self.error_signal.emit(tr("update.no_release_found"))
            elif response.status_code == 403:
                self.error_signal.emit(tr("update.api_rate_limited"))
            else:
                self.error_signal.emit(tr("update.request_failed_http", code=response.status_code))

        except requests.exceptions.Timeout:
            self.error_signal.emit(tr("update.check_timeout"))
        except requests.exceptions.ConnectionError:
            self.error_signal.emit(tr("update.connection_failed"))
        except Exception as e:
            self.error_signal.emit(tr("update.check_failed", error=str(e)))


class UpdateDownloadThread(QThread):
    """下载并安装更新线程"""
    progress_signal = pyqtSignal(int, str)  # percent, message
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, download_url, version, package_type=PACKAGE_SOURCE):
        super().__init__()
        self.download_url = download_url
        self.version = version
        self.package_type = normalize_update_package_type(download_url, package_type)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        temp_dir = None

        try:
            self.progress_signal.emit(5, tr("update.preparing_download"))
            temp_dir = tempfile.mkdtemp(prefix="nuclei_gui_update_")

            if self.package_type == PACKAGE_WINDOWS_EXE:
                self._install_windows_exe_update(temp_dir)
            else:
                self._install_source_update(temp_dir)

        except Exception as e:
            self.finished_signal.emit(False, tr("update.failed", error=str(e)))

        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

    def _download_file(self, target_path, start_percent=10, end_percent=60):
        """下载更新文件到指定路径。"""
        self.progress_signal.emit(start_percent, tr("update.downloading"))

        headers = {'User-Agent': 'Nuclei-GUI-Updater'}
        proxies = get_system_proxies()
        response = requests.get(self.download_url, headers=headers, stream=True, timeout=60, proxies=proxies)

        if response.status_code != 200:
            self.finished_signal.emit(False, tr("update.download_failed_http", code=response.status_code))
            return False

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self._is_cancelled:
                    self.finished_signal.emit(False, tr("update.cancelled"))
                    return False

                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = int(start_percent + (downloaded / total_size) * (end_percent - start_percent))
                        self.progress_signal.emit(percent, tr("update.downloading_progress", size=downloaded // 1024))

        return True

    def _install_source_update(self, temp_dir):
        """安装源码 zip 更新。"""
        project_root = str(app_dir())
        temp_zip = os.path.join(temp_dir, "update.zip")

        if not self._download_file(temp_zip):
            return

        if not zipfile.is_zipfile(temp_zip):
            if sys.platform == "win32" and self._looks_like_windows_exe(temp_zip):
                self.package_type = PACKAGE_WINDOWS_EXE
                self._install_windows_exe_update(temp_dir, downloaded_exe=temp_zip)
                return

            self.finished_signal.emit(False, tr("update.invalid_source_zip"))
            return

        self.progress_signal.emit(60, tr("update.extracting"))

        extract_dir = os.path.join(temp_dir, "extracted")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        extracted_items = os.listdir(extract_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
            source_dir = os.path.join(extract_dir, extracted_items[0])
        else:
            source_dir = extract_dir

        self.progress_signal.emit(70, tr("update.backing_up"))

        backup_dir = os.path.join(temp_dir, "backup")
        os.makedirs(backup_dir, exist_ok=True)

        for file in PRESERVE_FILES:
            src = os.path.join(project_root, file)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, file)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

        for dir_path in PRESERVE_DIRS:
            src = os.path.join(project_root, dir_path)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, dir_path)
                shutil.copytree(src, dst, dirs_exist_ok=True)

        self.progress_signal.emit(80, tr("update.updating_files"))

        for item in os.listdir(source_dir):
            if self._is_cancelled:
                self.finished_signal.emit(False, tr("update.cancelled"))
                return

            src = os.path.join(source_dir, item)
            dst = os.path.join(project_root, item)

            if item in PRESERVE_FILES:
                continue

            skip = False
            for preserve_dir in PRESERVE_DIRS:
                if item == preserve_dir.split('/')[0]:
                    if os.path.isdir(src):
                        self._merge_directory(src, dst, PRESERVE_DIRS)
                        skip = True
                        break

            if skip:
                continue

            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        self.progress_signal.emit(90, tr("update.restoring_files"))

        for file in PRESERVE_FILES:
            src = os.path.join(backup_dir, file)
            if os.path.exists(src):
                dst = os.path.join(project_root, file)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

        for dir_path in PRESERVE_DIRS:
            src = os.path.join(backup_dir, dir_path)
            if os.path.exists(src):
                dst = os.path.join(project_root, dir_path)
                shutil.copytree(src, dst, dirs_exist_ok=True)

        self.progress_signal.emit(100, tr("update.complete"))
        self.finished_signal.emit(True, tr("update.success", version=self.version))

    def _install_windows_exe_update(self, temp_dir, downloaded_exe=None):
        """下载 Windows exe，并启动独立替换脚本等待当前进程退出后覆盖。"""
        if sys.platform != "win32" or not getattr(sys, "frozen", False):
            self.finished_signal.emit(False, tr("update.binary_update_unsupported"))
            return

        current_exe = os.path.abspath(sys.executable)
        update_root = user_data_dir().joinpath("pending_update")
        update_root.mkdir(parents=True, exist_ok=True)
        safe_version = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(self.version))
        work_dir = tempfile.mkdtemp(prefix=f"v{safe_version}_", dir=str(update_root))
        next_exe = os.path.join(work_dir, f"Nuclei_GUI_v{self.version}.exe")
        script_path = os.path.join(work_dir, "apply_update.ps1")
        log_path = str(log_dir().joinpath("update_apply.log"))

        if downloaded_exe is None and not self._download_file(next_exe, 10, 90):
            return
        if downloaded_exe is not None:
            shutil.copy2(downloaded_exe, next_exe)

        if not self._looks_like_windows_exe(next_exe):
            self.finished_signal.emit(False, tr("update.invalid_windows_exe"))
            return

        self.progress_signal.emit(92, tr("update.preparing_binary_replace"))
        self._write_windows_replace_script(script_path, next_exe, current_exe, os.getpid(), log_path)

        creation_flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation_flags |= subprocess.CREATE_NO_WINDOW
        env = os.environ.copy()
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

        subprocess.Popen(
            [
                "cmd.exe",
                "/c",
                "start",
                "",
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-File",
                script_path,
            ],
            close_fds=True,
            creationflags=creation_flags,
            cwd=work_dir,
            env=env,
        )

        self.progress_signal.emit(100, tr("update.complete"))
        self.finished_signal.emit(True, tr("update.binary_ready", version=self.version))

    def _write_windows_replace_script(self, script_path, source_exe, target_exe, pid, log_path):
        """写入 Windows exe 替换脚本。"""
        temp_dir = os.path.dirname(script_path)
        script = f"""$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$src = {self._quote_powershell_literal(source_exe)}
$dst = {self._quote_powershell_literal(target_exe)}
$tempDir = {self._quote_powershell_literal(temp_dir)}
$workDir = Split-Path -Parent $dst
$pidToWait = {pid}
$logPath = {self._quote_powershell_literal(log_path)}
$backupPath = "$dst.old"
$env:PYINSTALLER_RESET_ENVIRONMENT = "1"

function Write-UpdateLog {{
    param([string]$Message)
    try {{
        $logDir = Split-Path -Parent $logPath
        if (-not (Test-Path -LiteralPath $logDir)) {{
            New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        }}
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        Add-Content -LiteralPath $logPath -Value "[$stamp] $Message" -Encoding UTF8
    }} catch {{}}
}}

function Get-FileSha256 {{
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}}

Write-UpdateLog "Updater started. Source=$src Target=$dst Pid=$pidToWait"

try {{
    $process = Get-Process -Id $pidToWait -ErrorAction SilentlyContinue
    if ($process) {{
        Write-UpdateLog "Waiting for process $pidToWait to exit"
        Wait-Process -Id $pidToWait -Timeout 180 -ErrorAction Stop
    }} else {{
        Write-UpdateLog "Process $pidToWait is already closed"
    }}
}} catch {{
    Write-UpdateLog "Wait-Process warning: $($_.Exception.Message)"
}}

try {{
    if (-not (Test-Path -LiteralPath $src)) {{
        throw "Source exe does not exist: $src"
    }}
    if (-not (Test-Path -LiteralPath $workDir)) {{
        New-Item -ItemType Directory -Force -Path $workDir | Out-Null
    }}
    $sourceHash = Get-FileSha256 $src
    $sourceSize = (Get-Item -LiteralPath $src).Length
    Write-UpdateLog "Source ready. Size=$sourceSize SHA256=$sourceHash"
}} catch {{
    Write-UpdateLog "Source validation failed: $($_.Exception.Message)"
    exit 1
}}

$replaced = $false
$lastError = ""
for ($i = 1; $i -le 90; $i++) {{
    $movedOld = $false
    try {{
        if (Test-Path -LiteralPath $backupPath) {{
            Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
        }}
        if (Test-Path -LiteralPath $dst) {{
            Move-Item -LiteralPath $dst -Destination $backupPath -Force -ErrorAction Stop
            $movedOld = $true
        }}
        Copy-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop
        $targetHash = Get-FileSha256 $dst
        $targetSize = (Get-Item -LiteralPath $dst).Length
        if ($targetHash -ne $sourceHash -or $targetSize -ne $sourceSize) {{
            throw "Verification failed. TargetSize=$targetSize TargetSHA256=$targetHash"
        }}
        $replaced = $true
        Write-UpdateLog "Replacement succeeded on attempt $i"
        break
    }} catch {{
        $lastError = $_.Exception.Message
        Write-UpdateLog "Replacement attempt $i failed: $lastError"
        if ($movedOld -and -not (Test-Path -LiteralPath $dst) -and (Test-Path -LiteralPath $backupPath)) {{
            try {{
                Move-Item -LiteralPath $backupPath -Destination $dst -Force -ErrorAction Stop
                Write-UpdateLog "Restored backup after failed attempt $i"
            }} catch {{
                Write-UpdateLog "Backup restore failed: $($_.Exception.Message)"
            }}
        }}
        Start-Sleep -Seconds 1
    }}
}}

if (-not $replaced) {{
    Write-UpdateLog "Failed to replace $dst. LastError=$lastError"
    exit 1
}}

try {{
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $dst
    $psi.WorkingDirectory = $workDir
    $psi.UseShellExecute = $false
    $psi.EnvironmentVariables["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Write-UpdateLog "Restarted updated executable"
}} catch {{
    Write-UpdateLog "Failed to restart updated executable: $($_.Exception.Message)"
}}

try {{
    Remove-Item -LiteralPath $src -Force -ErrorAction SilentlyContinue
}} catch {{
    Write-UpdateLog "Failed to remove downloaded exe: $($_.Exception.Message)"
}}

try {{
    if (Test-Path -LiteralPath $backupPath) {{
        Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    }}
}} catch {{
    Write-UpdateLog "Failed to remove backup exe: $($_.Exception.Message)"
}}

Write-UpdateLog "Updater finished"
"""
        with open(script_path, "w", encoding="utf-8-sig", newline="\r\n") as f:
            f.write(script)

    def _quote_powershell_literal(self, value):
        """生成 PowerShell 单引号字面量。"""
        return "'" + str(value).replace("'", "''") + "'"

    def _looks_like_windows_exe(self, path):
        """通过 MZ 文件头判断是否为 Windows exe。"""
        try:
            with open(path, "rb") as f:
                return f.read(2) == b"MZ"
        except OSError:
            return False

    def _merge_directory(self, src, dst, preserve_dirs):
        """合并目录，保留指定的子目录"""
        if not os.path.exists(dst):
            shutil.copytree(src, dst)
            return

        for item in os.listdir(src):
            src_item = os.path.join(src, item)
            dst_item = os.path.join(dst, item)

            # 检查是否是需要保留的子目录
            rel_path = os.path.relpath(dst_item, os.path.dirname(os.path.dirname(dst)))
            should_preserve = any(rel_path.startswith(p) for p in preserve_dirs)

            if should_preserve:
                continue

            if os.path.isdir(src_item):
                if os.path.exists(dst_item):
                    shutil.rmtree(dst_item)
                shutil.copytree(src_item, dst_item)
            else:
                shutil.copy2(src_item, dst_item)
