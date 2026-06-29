@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
start "" http://127.0.0.1:7862
python app.py
pause
