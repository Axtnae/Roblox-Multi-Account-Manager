@echo off
REM Release 0.2
REM User update script - updates code without full reinstallation
echo Updating Roblox Multi-Account Manager...
echo.

REM Check if we're in a git repository
if not exist ".git" (
    echo ERROR: This doesn't appear to be a git repository.
    echo Please download the latest version manually from GitHub.
    echo.
    pause
    exit /b 1
)

REM Pull latest changes
echo Pulling latest updates from GitHub...
git pull
if %errorLevel% neq 0 (
    echo.
    echo Update failed. You may need to download manually.
    echo Check https://github.com/Axtnae/Roblox-Multi-Account-Manager
    pause
    exit /b 1
)

REM Check if requirements changed
echo.
echo Checking for dependency updates...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --upgrade
    echo.
    echo ✓ Dependencies updated successfully!
) else (
    echo.
    echo Virtual environment not found. Running full setup...
    call setup.bat
)

echo.
echo ✅ Update completed successfully!
echo You can now run start.bat to launch the application.
echo.
pause
