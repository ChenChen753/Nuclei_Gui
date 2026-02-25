#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nuclei 设置助手
提供多种安装方式和状态检测
"""

import os
import platform
import subprocess
import shutil
from pathlib import Path

def get_system_info():
    """获取系统信息"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if machine in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'arm64'
    else:
        arch = 'amd64'
    
    return system, arch

def get_nuclei_binary_name():
    """获取 nuclei 二进制文件名"""
    system, _ = get_system_info()
    if system == 'windows':
        return 'nuclei.exe'
    elif system == 'darwin':
        return 'nuclei_darwin'
    elif system == 'linux':
        return 'nuclei_linux'
    else:
        return 'nuclei'

def check_bin_nuclei():
    """检查 bin 目录中的 nuclei"""
    bin_dir = Path("bin")
    binary_name = get_nuclei_binary_name()
    nuclei_path = bin_dir / binary_name
    
    if nuclei_path.exists():
        try:
            # 测试是否可执行
            result = subprocess.run([str(nuclei_path), '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"bin/{binary_name}", version
        except:
            pass
    
    return False, None, None

def check_system_nuclei():
    """检查系统中的 nuclei"""
    try:
        result = subprocess.run(['nuclei', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            
            # 获取 nuclei 路径
            system = platform.system().lower()
            which_cmd = 'where' if system == 'windows' else 'which'
            path_result = subprocess.run([which_cmd, 'nuclei'], 
                                       capture_output=True, text=True, timeout=5)
            
            if path_result.returncode == 0:
                nuclei_path = path_result.stdout.strip().split('\n')[0]
                return True, nuclei_path, version
    except Exception:
        pass
        pass
    
    return False, None, None

def copy_system_nuclei_to_bin():
    """将系统中的 nuclei 复制到 bin 目录"""
    has_system, system_path, version = check_system_nuclei()
    
    if not has_system:
        return False, "系统中未找到 nuclei"
    
    try:
        bin_dir = Path("bin")
        bin_dir.mkdir(exist_ok=True)
        
        binary_name = get_nuclei_binary_name()
        target_path = bin_dir / binary_name
        
        # 复制文件
        shutil.copy2(system_path, target_path)
        
        # 设置执行权限（Unix系统）
        system, _ = get_system_info()
        if system != 'windows':
            os.chmod(target_path, 0o755)
        
        return True, f"成功复制到 bin/{binary_name}"
        
    except Exception as e:
        return False, f"复制失败: {e}"

def get_download_instructions():
    """获取手动下载说明"""
    system, arch = get_system_info()
    binary_name = get_nuclei_binary_name()
    
    instructions = f"""
手动安装 Nuclei 步骤:

1. 访问 GitHub 发布页面:
   https://github.com/projectdiscovery/nuclei/releases

2. 下载适合您系统的版本:
   nuclei_*_{system}_{arch}.zip

3. 解压下载的文件

4. 将可执行文件复制到项目的 bin/ 目录下

5. 重命名为: {binary_name}

6. 重新运行此脚本检查安装状态

替代方案:
- 使用 Go 安装: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
- 使用包管理器安装后运行: python setup_nuclei.py --copy-system
"""
    return instructions

def main():
    """主函数"""
    import sys
    
    print("Nuclei 安装状态检查")
    print("=" * 40)
    
    # 检查 bin 目录中的 nuclei
    has_bin, bin_path, bin_version = check_bin_nuclei()
    
    if has_bin:
        print(f"[OK] 找到 Nuclei: {bin_path}")
        print(f"版本: {bin_version}")
        return True
    
    print("[INFO] bin 目录中未找到 Nuclei")
    
    # 检查系统中的 nuclei
    has_system, system_path, system_version = check_system_nuclei()
    
    if has_system:
        print(f"[INFO] 系统中找到 Nuclei: {system_path}")
        print(f"版本: {system_version}")
        
        # 检查是否有 --copy-system 参数
        if '--copy-system' in sys.argv:
            success, message = copy_system_nuclei_to_bin()
            if success:
                print(f"[OK] {message}")
                return True
            else:
                print(f"[FAIL] {message}")
        else:
            print("\n可以运行以下命令将系统 Nuclei 复制到项目:")
            print("python setup_nuclei.py --copy-system")
            return True
    
    # 都没找到，提供安装说明
    print("[FAIL] 未找到 Nuclei")
    print(get_download_instructions())
    return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        exit(1)
    except Exception as e:
        print(f"\n程序异常: {e}")
        exit(1)