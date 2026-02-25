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

def download_with_progress():
    """带进度的下载函数"""
    # 清除可能的代理环境变量
    proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    original_env = {}
    for var in proxy_env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    system, arch = get_system_info()
    
    print_progress("检测系统信息", 5)
    print_progress(f"系统: {system}-{arch}")
    
    # 创建 bin 目录
    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)
    
    # 下载信息
    version = "v3.7.0"
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
        print_progress("不支持的操作系统", 0)
        return False
    
    # GitHub 镜像站点
    mirror_sites = [
        "https://github.com",
        "https://hub.fastgit.xyz",
        "https://github.com.cnpmjs.org",
        "https://download.fastgit.org"
    ]
    
    # 代理配置 - 优先直连
    proxy_configs = [
        {"http": None, "https": None},  # 显式禁用代理
        None,  # 系统默认
        {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
        {"http": "http://127.0.0.1:1080", "https": "http://127.0.0.1:1080"},
        {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"},
    ]
    
    print_progress("开始下载", 10)
    
    for mirror_idx, mirror in enumerate(mirror_sites):
        download_url = f"{mirror}/projectdiscovery/nuclei/releases/download/{version}/{filename}"
        print_progress(f"尝试镜像站: {mirror}", 15 + mirror_idx * 5)
        
        for proxy_idx, proxies in enumerate(proxy_configs):
            try:
                session = requests.Session()
                if proxies:
                    session.proxies.update(proxies)
                    print_progress(f"使用代理: {proxies}")
                else:
                    print_progress("直连下载")
                
                # 获取文件大小
                response = session.head(download_url, timeout=30)
                if response.status_code != 200:
                    continue
                
                total_size = int(response.headers.get('content-length', 0))
                
                # 开始下载
                response = session.get(download_url, stream=True, timeout=60)
                response.raise_for_status()
                
                print_progress("开始下载文件", 30)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = min(90, 30 + int((downloaded / total_size) * 60))
                                print_progress(f"下载中... {downloaded}/{total_size} 字节", percent)
                    
                    tmp_path = tmp_file.name
                
                print_progress("下载完成，开始解压", 90)
                
                # 解压文件
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
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
                            
                            os.unlink(tmp_path)
                            print_progress(f"安装完成: {final_path}", 100)
                            
                            # 恢复原始环境变量
                            for var, value in original_env.items():
                                os.environ[var] = value
                            
                            return True
                
                os.unlink(tmp_path)
                print_progress("压缩包中未找到 nuclei 文件", 0)
                return False
                
            except requests.exceptions.RequestException as e:
                print_progress(f"网络错误: {e}")
                continue
            except Exception as e:
                print_progress(f"下载失败: {e}")
                continue
    
    print_progress("所有下载方式都失败了", 0)
    
    # 恢复原始环境变量
    for var, value in original_env.items():
        os.environ[var] = value
    
    return False

def main():
    """主函数"""
    print_progress("Nuclei 下载工具启动", 0)
    
    try:
        success = download_with_progress()
        if success:
            print_progress("下载安装成功", 100)
            return True
        else:
            print_progress("下载失败", 0)
            return False
    except Exception as e:
        print_progress(f"程序异常: {e}", 0)
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print_progress("用户取消操作", 0)
        exit(1)
    except Exception as e:
        print_progress(f"程序异常: {e}", 0)
        exit(1)