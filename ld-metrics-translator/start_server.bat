@echo off
title L&D Metrics Translator Server
echo Starting LD Metrics Translator server...

:: Get the short path name (8.3 format) to handle spaces and special characters
for /f "tokens=*" %%a in ('dir /b /s /a:d "%~dp0" ^| findstr /i "ld-metrics-translator"') do set "SHORTPATH=%%~sa"

:: Change to the directory using short path
cd /d "%SHORTPATH%"

echo Current directory: %CD%

:: First try using the Python in the virtual environment
if exist "%CD%\venv\Scripts\python.exe" (
    echo Using virtual environment...
    "%CD%\venv\Scripts\python.exe" "%CD%\run.py"
) else (
    echo Virtual environment not found, using system Python...
    python "%CD%\run.py"
)

:: Keep the window open if there's an error
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start. Press any key to exit...
    pause
)
