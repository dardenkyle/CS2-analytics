@echo off
REM Quick start script for Windows to create GitHub issues
REM CS2 Analytics Production Deployment

echo ============================================================
echo CS2 Analytics - GitHub Issues Creator
echo ============================================================
echo.

REM Step 1: Setup
echo [1/3] Running setup...
python setup_github_issues.py
if errorlevel 1 (
    echo.
    echo ERROR: Setup failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo.

REM Step 2: Pre-flight check
echo [2/3] Running pre-flight checks...
python preflight_check.py
if errorlevel 1 (
    echo.
    echo ERROR: Pre-flight checks failed.
    echo Please configure your .env file with your GitHub token.
    echo.
    echo Instructions:
    echo 1. Go to: https://github.com/settings/tokens
    echo 2. Generate new token with 'repo' scope
    echo 3. Edit .env and add: GITHUB_TOKEN=your_token_here
    echo 4. Run this script again
    pause
    exit /b 1
)

echo.
echo ============================================================
echo.

REM Step 3: Create issues
echo [3/3] Creating GitHub issues...
echo.
set /p CONFIRM="Ready to create 33 issues with 44 labels and 10 milestones? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo Cancelled by user.
    pause
    exit /b 0
)

python create_github_issues.py
if errorlevel 1 (
    echo.
    echo ERROR: Issue creation failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! All issues created.
echo View them at: https://github.com/dardenkyle/CS2-analytics/issues
echo ============================================================
pause
