@echo off
setlocal enabledelayedexpansion
:: Release 0.2

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_CMD=python"

:: Try to detect Python in PATH
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found in PATH. Attempting to locate Python in common install locations...
    set "PYTHON_EXE="
    for /f "delims=" %%P in ('dir /b /s "%LocalAppData%\Programs\Python\python3*.exe" 2^>nul') do (
        set "PYTHON_EXE=%%P"
        goto :FOUND_PYTHON
    )
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.7+ from https://python.org
    echo The download page will open now.
    start https://www.python.org/downloads/
    pause
    exit /b 1
:FOUND_PYTHON
    set "PYTHON_CMD=!PYTHON_EXE!"
    set "PATH=%PATH%;!PYTHON_EXE:~0,-10!"
)

:: Check Python version
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"
if %errorlevel% neq 0 (
    echo ERROR: Python 3.7 or higher is required.
    echo Please upgrade your Python installation.
    pause
    exit /b 1
)

echo ✓ Python version check passed.
echo.

:: Virtual environment logic
if exist "venv" (
    echo Virtual environment already exists.
    set /p DELVENV="Do you want to delete and recreate the venv? (y/n): "
    if /i "!DELVENV!"=="y" (
        echo Removing old venv...
        rmdir /s /q venv
        set CREATEVENV=y
    ) else (
        set CREATEVENV=n
    )
) else (
    set CREATEVENV=y
)

if /i "!CREATEVENV!"=="y" (
    echo Creating Python virtual environment...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure you have the 'venv' module installed.
        pause
        exit /b 1
    )
    echo ✓ Virtual environment created successfully.
) else (
    echo Using existing virtual environment.
)
echo.

:: Create .data directory and set hidden attribute (Windows)
if not exist ".data" (
    mkdir .data
    attrib +h .data
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo ✓ Virtual environment activated.
echo.

:: Upgrade pip
echo Upgrading pip to latest version...
python -m pip install --upgrade pip
echo.

:INSTALL_PACKAGES
set /p INSTALLPKG="Do you want to install/upgrade required packages? (y/n): "
if /i "%INSTALLPKG%"=="n" goto SKIP_INSTALL

echo Installing required packages...
echo This may take a few minutes...
echo.

pip install "selenium==4.17.2"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install selenium
    set /p RETRY="Retry package installation? (y/n): "
    if /i "%RETRY%"=="y" goto INSTALL_PACKAGES
    pause
    exit /b 1
)

pip install "cryptography>=41.0.0,<46.0.0"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install cryptography
    set /p RETRY="Retry package installation? (y/n): "
    if /i "%RETRY%"=="y" goto INSTALL_PACKAGES
    pause
    exit /b 1
)

pip install webdriver-manager==4.0.1
if %errorlevel% neq 0 (
    echo ERROR: Failed to install webdriver-manager
    set /p RETRY="Retry package installation? (y/n): "
    if /i "%RETRY%"=="y" goto INSTALL_PACKAGES
    pause
    exit /b 1
)

pip install "psutil>=5.9.0"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install psutil
    set /p RETRY="Retry package installation? (y/n): "
    if /i "%RETRY%"=="y" goto INSTALL_PACKAGES
    pause
    exit /b 1
)

echo.
echo ✓ All packages installed successfully!
echo.

:: Verify installation
echo Verifying installation...
python -c "import selenium; import cryptography; import webdriver_manager; import psutil; print('✓ All modules imported successfully!')"
if %errorlevel% neq 0 (
    echo ERROR: Package verification failed.
    set /p RETRY="Retry package installation? (y/n): "
    if /i "%RETRY%"=="y" goto INSTALL_PACKAGES
    pause
    exit /b 1
)

:SKIP_INSTALL
echo.
echo ================================================================
echo Setup completed successfully!
echo ================================================================
echo.
echo Virtual environment location: %CD%\venv
echo.
echo Setup complete! The application is ready to use.
echo.
echo To launch the application:
echo   Run: Start.bat
echo.
echo Press any key to exit setup...
pause >nul
endlocal
