@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
set "TARGET_SCRIPT=%SCRIPT_DIR%ai_commit.py"

REM Try to use venv Python first
if exist "%VENV_PYTHON%" (
    set "PYTHON_CMD=%VENV_PYTHON%"
) else (
    REM Fallback to system Python if venv is not available
    for /f "delims=" %%i in ('where python.exe 2^>nul') do set "PYTHON_CMD=%%i"
    if not defined PYTHON_CMD (
        echo [ERROR] Python is required but not found.
        echo Expected either:
        echo   1. Virtual environment at: "%VENV_PYTHON%"
        echo   2. Python in PATH (system installation)
        exit /b 1
    )
)

if not exist "%TARGET_SCRIPT%" (
    echo [ERROR] Script not found: "%TARGET_SCRIPT%"
    exit /b 1
)

"%PYTHON_CMD%" "%TARGET_SCRIPT%" %*
exit /b %ERRORLEVEL%
