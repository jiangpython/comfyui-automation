@echo off
chcp 65001 >nul
title ComfyUI 自动化系统
color 0A

echo.
echo ======================================
echo    🎨 ComfyUI 自动化系统 v3.3
echo ======================================
echo.

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo ❌ 虚拟环境不存在！
    echo 💡 请先运行以下命令创建虚拟环境：
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    pause
    exit /b 1
)

:: 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

:: 检查是否首次运行
if not exist "data\database" (
    echo 📁 首次运行，创建目录结构...
    mkdir data\database 2>nul
    mkdir output 2>nul
    mkdir output\static 2>nul
    mkdir output\static\css 2>nul
    mkdir output\static\js 2>nul
)

:: 显示选择菜单
:menu
echo.
echo 📋 选择启动方式：
echo    1. 🚀 快速启动 (新手推荐)
echo    2. 🎯 完整功能 (高级用户)
echo    3. 🧪 系统测试
echo    4. 📊 数据分析
echo    0. ❌ 退出
echo.

set /p choice="请选择 (0-4): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :quick
if "%choice%"=="2" goto :full
if "%choice%"=="3" goto :test
if "%choice%"=="4" goto :analysis

echo ❌ 无效选择，请重试
goto :menu

:quick
echo 🚀 启动快速模式...
python quick_start.py
goto :menu

:full
echo 🎯 启动完整功能...
python main.py --interactive
goto :menu

:test
echo 🧪 运行系统测试...
python simple_test.py
pause
goto :menu

:analysis
echo 📊 启动分析工具...
python analysis_cli.py dashboard
pause
goto :menu

:end
echo.
echo 👋 感谢使用 ComfyUI 自动化系统！
echo.
pause