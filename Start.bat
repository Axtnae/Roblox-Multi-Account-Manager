@echo off
setlocal enabledelayedexpansion

echo Requesting administrator privileges...
echo.

REM Check if already running as admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Already running as administrator.
    goto :run_app
)

REM If not admin, restart as admin
echo Elevating to administrator...
powershell -Command "Start-Process '%~f0' -Verb RunAs"
exit /b

:run_app
echo Running as administrator...
echo.

REM Get the directory where this batch file is located
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to create the environment.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)

REM Check if Python is available
python --version
if %errorLevel% neq 0 (
    echo ERROR: Python not found in virtual environment!
    pause
    exit /b 1
)

REM Check if required modules are installed
echo Checking required modules...
python -c "import tkinter, selenium, psutil, cryptography; print('All modules available')"
if %errorLevel% neq 0 (
    echo ERROR: Required modules not installed!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Change to src directory and launch the application
echo Launching Roblox Multi-Account Manager...
echo.
cd src
REM Use pythonw.exe to hide the command prompt window
pythonw main.py

REM Keep window open if there's an error
if %errorLevel% neq 0 (
    echo.
    echo Application exited with error code: %errorLevel%
    pause
)

REM Return to original directory
cd ..
