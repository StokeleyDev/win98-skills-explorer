@echo off
setlocal
cd /d "%~dp0"
title Windows 98 AI Skills Explorer

rem Prefer the Python launcher, fall back to python on PATH.
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3.10 or newer is required: https://www.python.org/downloads/
  pause
  exit /b 1
)

rem Already running? Just open the browser.
powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1', 1998); exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 goto open

echo Starting Windows 98 Skills Explorer Server...
start "Win98 Skills Explorer server" %PY% server.py

rem Wait up to 15 seconds for the port to answer.
for /l %%i in (1,1,15) do (
  powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1', 1998); exit 0 } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 goto open
  timeout /t 1 /nobreak >nul
)
echo The server did not start. Check the server window for errors (is port 1998 in use?).
pause
exit /b 1

:open
echo Opening in default browser...
start "" http://localhost:1998
