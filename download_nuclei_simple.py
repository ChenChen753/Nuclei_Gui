#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 Nuclei 下载脚本 - 用于测试
直接下载已知版本，避免 API 调用问题
"""

import os
import platform
import requests
import zipfile
import tempfile
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

def download_nuclei_simple():
    """简化版下载函数"""
    print("Nuclei 简化下载工具")
    print("=" * 30)
    
    # 获取系统信息
    system, arch = get_system_info()
    print(f"检测到系统: {system}-{arch}")
    
    # 清除可能的代理环境变量
    proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    original_env = {}
    for var in proxy_env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    try:
        # 创建 bin 目录
        bin_dir = Path("bin")
        bin_dir.mkdir(exist_ok=True)
        
        # 根据系统构建下载链接
        version = "v3.7.0"
        if system == 'windows':
            filename = f"nuclei_3.7.0_windows_{arch}.zip"
            binary_name = 'nuclei.exe'
        elif system == 'darwin':
            filename = f"nuclei_3.7.0_macOS_{arch}.zip"
            binary_name = 'nuclei_darwin'
        elif system == 'linux':
            filename = f"nuclei_3.7.0_linux_{arch}.zip"
            binary_name = 'nuclei_linux'
        else:
            raise Exception(f"不支持的操作系统: {system}")
        
        download_url = f"https://github.com/projectdiscovery/nuclei/releases/download/{version}/{filename}"
        
        print(f"下载链接: {download_url}")
        print(f"目标文件: {binary_name}")
        
        print("正在下载...")
        
        # 创建session，完全禁用代理
        session = requests.Session()
        session.proxies = {"http": None, "https": None}
        session.trust_env = False  # 不信任环境变量
        
        print("尝试直连下载...")
        response = session.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        print("连接成功！")
        
        # 下载到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        # 输出GUI能识别的进度格式
                        print(f"正在下载... {percent:.1f}%")
                        if percent % 10 == 0:  # 每10%输出一次状态
                            print(f"下载进度: {percent:.1f}%")
            tmp_path = tmp_file.name
        
        print("\n正在解压...")
        
        # 解压文件
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith(('nuclei.exe', 'nuclei')):
                    # 提取文件
                    zip_ref.extract(file_info, bin_dir)
                    extracted_path = bin_dir / file_info.filename
                    final_path = bin_dir / binary_name
                    
                    # 重命名
                    if extracted_path != final_path:
                        if final_path.exists():
                            final_path.unlink()
                        extracted_path.rename(final_path)
                    
                    # 设置执行权限（Unix系统）
                    if not binary_name.endswith('.exe'):
                        os.chmod(final_path, 0o755)
                    
                    print(f"[OK] Nuclei 安装成功!")
                    print(f"安装位置: {final_path}")
                    
                    # 清理临时文件
                    try:
                        os.unlink(tmp_path)
                    except (OSError, PermissionError):
                        # 如果无法删除临时文件，忽略错误
                        pass
                    return True
        
        print("[FAIL] 在压缩包中未找到 nuclei 可执行文件")
        try:
            os.unlink(tmp_path)
        except (OSError, PermissionError):
            pass
        return False
        
    except Exception as e:
        print(f"[FAIL] 下载失败: {e}")
        return False
    finally:
        # 恢复原始环境变量
        for var, value in original_env.items():
            os.environ[var] = value

if __name__ == "__main__":
    try:
        success = download_nuclei_simple()
        if success:
            print("\n[OK] 下载完成！")
            exit(0)
        else:
            print("\n[FAIL] 下载失败")
            exit(1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        exit(1)
    except Exception as e:
        print(f"\n程序异常: {e}")
        exit(1)