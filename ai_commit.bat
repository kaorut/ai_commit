@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
set "TARGET_SCRIPT=%SCRIPT_DIR%ai_commit.py"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Python venv is required but not found.
    echo Expected: "%VENV_PYTHON%"
    exit /b 1
)

if not exist "%TARGET_SCRIPT%" (
    echo [ERROR] Script not found: "%TARGET_SCRIPT%"
    exit /b 1
)

"%VENV_PYTHON%" "%TARGET_SCRIPT%" %*
exit /b %ERRORLEVEL%
