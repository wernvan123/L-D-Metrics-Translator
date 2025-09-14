@echo off
title L&D Metrics Translator Server
echo Starting server...

:: Use pushd to handle paths with spaces and special characters
pushd "%~dp0"

:: Always use system Python
echo Using system Python...
python "run.py"

:: Keep window open
if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start. Press any key to exit...
) else (
    echo.
    echo Press any key to close...
)
pause

popd
