#!/bin/bash
# Internal-accounting launcher (Mac)
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

APP_URL="http://127.0.0.1:7862"
export PYTHONIOENCODING=utf-8

if [ ! -f "app.py" ]; then
  echo "[ERROR] app.py not found in: $APP_DIR"
  read -p "Press Enter to close."
  exit 1
fi

echo "====================================================="
echo "  内部管理会計ツール"
echo "====================================================="
echo "Working dir: $APP_DIR"
echo "App URL    : $APP_URL"
echo ""

if [ ! -f ".venv/bin/python" ]; then
  echo "[Setup] Creating virtual environment..."
  python3 -m venv .venv || { echo "[ERROR] venv 作成に失敗"; read -p "Enter"; exit 1; }
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt || { echo "[ERROR] 依存パッケージのインストール失敗"; read -p "Enter"; exit 1; }
else
  source .venv/bin/activate
fi

python -c "import flask" 2>/dev/null || pip install -r requirements.txt

(sleep 4 && open "$APP_URL") &

echo "[Launch] ブラウザを4秒後に自動で開きます ..."
python -u app.py
echo "アプリ終了 (rc=$?)"
read -p "Press Enter to close."
