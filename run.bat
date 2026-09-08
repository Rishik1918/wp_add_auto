@echo off
title WhatsApp One-Time Link Gateway
cd /d "%~dp0"
echo ========================================================
echo       WhatsApp One-Time Invite Gateway Server
echo ========================================================
echo.
echo [1/2] Checking and installing requirements...
python -m pip install -r requirements.txt --quiet
echo.
echo [2/2] Starting server...
echo.
echo Admin Panel is available at: http://localhost:5000/admin
echo Press Ctrl+C in this window to stop the server.
echo ========================================================
echo.
python app.py
pause
