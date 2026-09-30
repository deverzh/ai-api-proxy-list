#!/bin/bash

echo "========================================"
echo "  AI API 中转站列表 - 一键更新脚本"
echo "  Mac / Linux 版本"
echo "========================================"
echo

cd "$(dirname "$0")"

echo "[1/3] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[错误] 未找到 Python，请先安装 Python 3.8+"
        read -p "按 Enter 退出"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi
echo "[OK] Python 已安装"

echo
echo "[2/3] 发现 API Base URL 并测试延迟..."
$PYTHON_CMD discover_and_update.py --workers 15 --timeout 12

if [ $? -ne 0 ]; then
    echo "[错误] 发现 API Base URL 失败"
    read -p "按 Enter 退出"
    exit 1
fi

echo
echo "[3/3] 更新完成！"
echo
echo "结果已保存到 README.md"
echo
read -p "按 Enter 退出"
