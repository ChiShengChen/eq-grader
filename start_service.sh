#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$HOME/Documents/Projects/eq-grader"
VENV_PATH="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/uvicorn.log"
APP_MODULE="app.main:app"
HOST="0.0.0.0"
PORT="8000"

cd "$PROJECT_DIR"

# 停止舊的服務
echo "正在停止舊的服務..."
pkill -f "uvicorn $APP_MODULE" || true
sleep 1

# 檢查虛擬環境是否存在
if [ ! -d "$VENV_PATH" ] || [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "錯誤: 找不到虛擬環境 $VENV_PATH"
    exit 1
fi

# 啟動新服務
echo "正在啟動服務 (埠號: $PORT)..."
source "$VENV_PATH/bin/activate"
nohup python -m uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
PID=$!

echo "服務已在背景啟動。"
echo "日誌檔案位置: $LOG_FILE"
echo "PID: $PID"
