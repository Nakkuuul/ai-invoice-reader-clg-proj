@echo off
cd /d "%~dp0"
if not exist .venv (
  py -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
if not exist .env copy .env.example .env >nul
.venv\Scripts\python -m streamlit run app.py
