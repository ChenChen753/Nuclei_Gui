#!/bin/bash
# -*- coding: utf-8 -*-
# Nuclei GUI Scanner 启动脚本 (macOS/Linux)

echo "Nuclei GUI Scanner - 跨平台漏洞扫描工具"
echo "=========================================="

# 检查 Python 版本
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ 错误: 未找到 Python 解释器"
        echo "请安装 Python 3.8+ 后重试"
        exit 1
    fi
    
    # 检查 Python 版本
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "✅ 找到 Python $PYTHON_VERSION"
    
    # 检查版本是否满足要求 (3.8+)
    if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        echo "❌ 错误: Python 版本过低，需要 3.8 或更高版本"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    echo "正在检查依赖..."
    
    if ! $PYTHON_CMD -c "import PyQt5" 2>/dev/null; then
        echo "❌ 缺少依赖: PyQt5"
        echo "正在安装依赖..."
        $PYTHON_CMD -m pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "❌ 依赖安装失败，请手动执行: $PYTHON_CMD -m pip install -r requirements.txt"
            exit 1
        fi
    fi
    
    echo "✅ 依赖检查完成"
}

# 检查 Nuclei
check_nuclei() {
    echo "正在检查 Nuclei 扫描引擎..."
    
    # 检查 bin 目录下的二进制文件
    OS_TYPE=$(uname -s | tr '[:upper:]' '[:lower:]')
    if [ "$OS_TYPE" = "darwin" ]; then
        NUCLEI_BINARY="bin/nuclei_darwin"
    else
        NUCLEI_BINARY="bin/nuclei_linux"
    fi
    
    if [ -f "$NUCLEI_BINARY" ]; then
        echo "✅ 找到 Nuclei: $NUCLEI_BINARY"
        # 确保有执行权限
        chmod +x "$NUCLEI_BINARY" 2>/dev/null
    elif command -v nuclei &> /dev/null; then
        echo "✅ 找到系统 Nuclei: $(which nuclei)"
    else
        echo "⚠️  未找到 Nuclei 扫描引擎"
        echo "是否要自动下载 Nuclei？(y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo "正在下载 Nuclei..."
            $PYTHON_CMD download_nuclei.py
            if [ $? -eq 0 ]; then
                echo "✅ Nuclei 下载完成"
            else
                echo "❌ Nuclei 下载失败，程序仍可运行但无法扫描"
            fi
        else
            echo "⚠️  跳过 Nuclei 下载，程序仍可运行但无法扫描"
        fi
    fi
}

# 主函数
main() {
    # 切换到脚本所在目录
    cd "$(dirname "$0")" || exit 1
    
    echo "当前目录: $(pwd)"
    echo "操作系统: $(uname -s) $(uname -m)"
    echo ""
    
    # 执行检查
    check_python
    check_dependencies
    check_nuclei
    
    echo ""
    echo "🚀 启动 Nuclei GUI Scanner..."
    echo "如需退出，请按 Ctrl+C"
    echo ""
    
    # 启动程序
    exec $PYTHON_CMD main.py "$@"
}

# 信号处理
trap 'echo -e "\n\n👋 程序已退出"; exit 0' INT TERM

# 运行主函数
main "$@"