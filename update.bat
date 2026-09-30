@echo off
echo ========================================
echo  AI API 中转站列表 - 一键更新脚本
echo  Windows 版本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 已安装

echo.
echo [2/3] 发现 API Base URL 并测试延迟...
python discover_and_update.py --workers 15 --timeout 12

if errorlevel 1 (
    echo [错误] 发现 API Base URL 失败
    pause
    exit /b 1
)

echo.
echo [3/3] 更新完成！
echo.
echo 结果已保存到 README.md
echo.
pause
