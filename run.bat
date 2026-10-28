@echo off
cd /d "%~dp0"
py -3 md_time_calc.py 2>nul
if errorlevel 1 python md_time_calc.py
if errorlevel 1 (
  echo.
  echo Failed to start. Install Python 3 and retry: py -3 md_time_calc.py
  pause
)
