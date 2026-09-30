# AI API 中转站列表 - 一键更新脚本 (PowerShell 版本)
# Windows 10/11 推荐使用

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI API 中转站列表 - 一键更新脚本" -ForegroundColor Cyan
Write-Host "  PowerShell 版本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

Write-Host "[1/3] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host ""
Write-Host "[2/3] 发现 API Base URL 并测试延迟..." -ForegroundColor Yellow
python discover_and_update.py --workers 15 --timeout 12

if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 发现 API Base URL 失败" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host ""
Write-Host "[3/3] 更新完成！" -ForegroundColor Green
Write-Host ""
Write-Host "结果已保存到 README.md" -ForegroundColor Green
Write-Host ""
Read-Host "按 Enter 退出"
