@echo off
chcp 65001 >nul
echo 正在启动 Streamlit OCR 辨识工具...
echo.
cd /d "%~dp0"
streamlit run app.py
pause
