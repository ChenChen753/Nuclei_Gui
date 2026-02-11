@echo off
setlocal

:: 获取当前脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "BIN_DIR=%SCRIPT_DIR%bin"

:: 检测是否安装了 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python，请先安装 Python 并添加到 PATH 环境变量。
    pause
    exit /b 1
)

:: 检测 bin 目录是否存在
if exist "%BIN_DIR%\nuclei.exe" (
    :: 将 bin 目录添加到 PATH (临时)
    set "PATH=%BIN_DIR%;%PATH%"
)

:: 静默安装依赖 (如果有 requirements.txt)
if exist "%SCRIPT_DIR%requirements.txt" (
    pip install -r "%SCRIPT_DIR%requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple -q >nul 2>&1
)

:: 使用 pythonw 启动主程序 (隐藏命令行窗口)
start "" pythonw "%SCRIPT_DIR%main.py"

endlocal
