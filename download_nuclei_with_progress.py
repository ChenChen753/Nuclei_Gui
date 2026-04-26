#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带进度条的 Nuclei 下载脚本
支持实时进度更新和多种网络配置
"""

import os
import platform
import requests
import zipfile
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import tr, init_language

SCRIPT_DIR = Path(__file__).resolve().parent
BIN_DIR = SCRIPT_DIR / "bin"
DEFAULT_VERSION = "v3.8.0"
LATEST_RELEASE_API = "https://api.github.com/repos/projectdiscovery/nuclei/releases/latest"
USER_AGENT = "Nuclei-GUI-Downloader"

def get_system_info():
    """获取系统信息"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if machine in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'arm64'
    elif machine.startswith('arm'):
        arch = 'arm'
    else:
        arch = 'amd64'
    
    return system, arch

def print_progress(message, percent=None):
    """打印进度信息"""
    if percent is not None:
        print(f"PROGRESS:{percent}:{message}")
    else:
        print(f"STATUS:{message}")
    sys.stdout.flush()


def create_session(proxies=None, trust_env=False):
    """创建下载会话，统一 User-Agent 和代理行为。"""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.trust_env = trust_env
    if proxies:
        session.proxies.update(proxies)
    return session


def get_latest_version():
    """获取最新 Nuclei 版本，失败时使用已知稳定版本。"""
    try:
        session = create_session(trust_env=False)
        response = session.get(LATEST_RELEASE_API, timeout=20)
        response.raise_for_status()
        tag_name = response.json().get("tag_name", "").strip()
        if tag_name.startswith("v"):
            return tag_name
    except Exception:
        pass
    return DEFAULT_VERSION


def install_from_zip(zip_path, bin_dir, binary_name, system):
    """从下载的 zip 中安装 nuclei 可执行文件，返回最终路径或 None。"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.filelist:
            if file_info.filename.endswith(('nuclei.exe', 'nuclei')):
                zip_ref.extract(file_info, bin_dir)
                extracted_path = bin_dir / file_info.filename
                final_path = bin_dir / binary_name

                if extracted_path != final_path:
                    if final_path.exists():
                        final_path.unlink()
                    extracted_path.rename(final_path)

                # 设置权限
                if system != 'windows':
                    os.chmod(final_path, 0o755)

                return final_path
    return None

def download_with_progress():
    """带进度的下载函数"""
    # 不修改全局代理环境变量；每个 requests session 自己决定是否信任系统代理。
    
    system, arch = get_system_info()
    
    print_progress(tr("download.detecting_system"), 5)
    print_progress(tr("download.system_info", system=system, arch=arch))
    
    # 创建项目 bin 目录，避免从其他工作目录启动时写错位置
    bin_dir = BIN_DIR
    bin_dir.mkdir(exist_ok=True)
    
    # 下载信息
    version = get_latest_version()
    if system == 'windows':
        filename = f"nuclei_{version[1:]}_windows_{arch}.zip"
        binary_name = 'nuclei.exe'
    elif system == 'darwin':
        filename = f"nuclei_{version[1:]}_macOS_{arch}.zip"
        binary_name = 'nuclei_darwin'
    elif system == 'linux':
        filename = f"nuclei_{version[1:]}_linux_{arch}.zip"
        binary_name = 'nuclei_linux'
    else:
        print_progress(tr("download.unsupported_os"), 0)
        return False
    
    # GitHub 镜像站点；官方 GitHub 放首位，其他镜像作为兼容性兜底
    mirror_sites = [
        "https://github.com",
        "https://hub.fastgit.xyz",
        "https://github.com.cnpmjs.org",
        "https://download.fastgit.org"
    ]
    
    # 代理配置 - 优先直连
    proxy_configs = [
        ("direct", None, False),
        ("system", None, True),
        ("127.0.0.1:7890", {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}, False),
        ("127.0.0.1:1080", {"http": "http://127.0.0.1:1080", "https": "http://127.0.0.1:1080"}, False),
        ("127.0.0.1:8080", {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}, False),
    ]
    
    print_progress(tr("download.starting"), 10)
    
    for mirror_idx, mirror in enumerate(mirror_sites):
        download_url = f"{mirror}/projectdiscovery/nuclei/releases/download/{version}/{filename}"
        print_progress(tr("download.trying_mirror", mirror=mirror), 15 + mirror_idx * 5)
        
        for proxy_name, proxies, trust_env in proxy_configs:
            tmp_path = None
            try:
                session = create_session(proxies, trust_env)
                if proxies:
                    print_progress(tr("download.using_proxy", proxies=proxies))
                else:
                    print_progress(tr("download.direct_connect"))
                
                # 开始下载
                response = session.get(download_url, stream=True, timeout=60, allow_redirects=True)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                print_progress(tr("download.downloading_file"), 30)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    downloaded = 0
                    last_percent = 29
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = min(90, 30 + int((downloaded / total_size) * 60))
                                if percent > last_percent:
                                    last_percent = percent
                                    print_progress(tr("download.downloading_progress", downloaded=downloaded, total=total_size), percent)
                    
                    tmp_path = tmp_file.name
                
                print_progress(tr("download.extracting"), 90)
                
                final_path = install_from_zip(Path(tmp_path), bin_dir, binary_name, system)
                if final_path:
                    print_progress(tr("download.install_complete", path=final_path), 100)

                    return True
                
                if tmp_path:
                    os.unlink(tmp_path)
                print_progress(tr("download.nuclei_not_found_in_zip"), 0)
                return False
                
            except requests.exceptions.RequestException as e:
                print_progress(tr("download.network_error", error=e))
                continue
            except Exception as e:
                print_progress(tr("download.failed", error=e))
                continue
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
    
    print_progress(tr("download.all_methods_failed"), 0)
    
    return False

def main():
    """主函数"""
    print_progress(tr("download.tool_started"), 0)
    
    try:
        success = download_with_progress()
        if success:
            print_progress(tr("download.install_success"), 100)
            return True
        else:
            print_progress(tr("download.download_failed"), 0)
            return False
    except Exception as e:
        print_progress(tr("download.program_error", error=e), 0)
        return False

if __name__ == "__main__":
    # Load language setting for subprocess
    try:
        from core.settings_manager import get_settings
        init_language(get_settings().get_language())
    except Exception:
        init_language('zh_CN')

    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print_progress(tr("download.user_cancelled"), 0)
        exit(1)
    except Exception as e:
        print_progress(tr("download.program_error", error=e), 0)
        exit(1)
