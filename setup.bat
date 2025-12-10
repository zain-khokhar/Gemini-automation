@echo off
echo ========================================
echo PDF MCQ Extraction Tool - Quick Start
echo ========================================
echo.

echo Step 1: Installing Node.js dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install Node.js dependencies
    pause
    exit /b 1
)
echo.

echo Step 2: Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Open a terminal and run: npm start
echo 2. Complete Gemini login if needed
echo 3. Open another terminal and run: python ui_main.py
echo.
echo See README.md for detailed instructions.
echo.
pause
