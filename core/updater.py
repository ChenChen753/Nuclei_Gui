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
import requests
from PyQt5.QtCore import QThread, pyqtSignal

# 项目信息
GITHUB_REPO = "ChenChen753/Nuclei_Gui"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "2.4.2"

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
    "poc_library/custom",
    "poc_library/user_generated",
    "logs",
]


def get_current_version():
    """获取当前版本号"""
    return CURRENT_VERSION


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
    check_finished = pyqtSignal(bool, str, str, str)  # has_update, latest_version, download_url, release_notes
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
                release_notes = data.get('body', '无更新说明')

                # 查找下载链接 (zip 源码包)
                download_url = ""
                assets = data.get('assets', [])

                # 优先查找 zip 资源
                for asset in assets:
                    if asset['name'].endswith('.zip'):
                        download_url = asset['browser_download_url']
                        break

                # 如果没有 assets，使用源码 zip
                if not download_url:
                    download_url = data.get('zipball_url', '')

                # 比较版本
                current = get_current_version()
                has_update = compare_versions(latest_version, current) > 0

                self.check_finished.emit(has_update, latest_version, download_url, release_notes)
            elif response.status_code == 404:
                self.error_signal.emit("未找到发布版本")
            elif response.status_code == 403:
                self.error_signal.emit("API 请求限制，请稍后再试")
            else:
                self.error_signal.emit(f"请求失败: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            self.error_signal.emit("检查更新超时，请检查网络连接")
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("网络连接失败，请检查网络设置")
        except Exception as e:
            self.error_signal.emit(f"检查更新失败: {str(e)}")


class UpdateDownloadThread(QThread):
    """下载并安装更新线程"""
    progress_signal = pyqtSignal(int, str)  # percent, message
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, download_url, version):
        super().__init__()
        self.download_url = download_url
        self.version = version
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        temp_dir = None
        temp_zip = None

        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            self.progress_signal.emit(5, "正在准备下载...")

            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="nuclei_gui_update_")
            temp_zip = os.path.join(temp_dir, "update.zip")

            # 下载文件
            self.progress_signal.emit(10, "正在下载更新包...")

            headers = {'User-Agent': 'Nuclei-GUI-Updater'}
            proxies = get_system_proxies()
            response = requests.get(self.download_url, headers=headers, stream=True, timeout=60, proxies=proxies)

            if response.status_code != 200:
                self.finished_signal.emit(False, f"下载失败: HTTP {response.status_code}")
                return

            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        self.finished_signal.emit(False, "更新已取消")
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = int(10 + (downloaded / total_size) * 50)
                            self.progress_signal.emit(percent, f"正在下载... {downloaded // 1024} KB")

            self.progress_signal.emit(60, "正在解压更新包...")

            # 解压文件
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 找到解压后的根目录
            extracted_items = os.listdir(extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                source_dir = os.path.join(extract_dir, extracted_items[0])
            else:
                source_dir = extract_dir

            self.progress_signal.emit(70, "正在备份保留文件...")

            # 备份需要保留的文件
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

            self.progress_signal.emit(80, "正在更新文件...")

            # 复制新文件（排除保留的文件和目录）
            for item in os.listdir(source_dir):
                if self._is_cancelled:
                    self.finished_signal.emit(False, "更新已取消")
                    return

                src = os.path.join(source_dir, item)
                dst = os.path.join(project_root, item)

                # 跳过保留的文件
                if item in PRESERVE_FILES:
                    continue

                # 跳过保留的目录（但允许合并）
                skip = False
                for preserve_dir in PRESERVE_DIRS:
                    if item == preserve_dir.split('/')[0]:
                        # 对于 poc_library 这样的目录，需要特殊处理
                        if os.path.isdir(src):
                            self._merge_directory(src, dst, PRESERVE_DIRS)
                            skip = True
                            break

                if skip:
                    continue

                # 复制文件或目录
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            self.progress_signal.emit(90, "正在恢复保留文件...")

            # 恢复保留的文件
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

            self.progress_signal.emit(100, "更新完成！")
            self.finished_signal.emit(True, f"更新到 v{self.version} 成功！请重启程序以应用更新。")

        except Exception as e:
            self.finished_signal.emit(False, f"更新失败: {str(e)}")

        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

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
