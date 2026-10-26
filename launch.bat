@echo off
cd /d "%~dp0"
title Windows 98 AI Skills Explorer
echo Starting Windows 98 Skills Explorer Server...
start "" python server.py
timeout /t 1 /nobreak >nul
echo Opening in default browser...
start http://localhost:1998
