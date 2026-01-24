@echo off
echo ========================================================
echo   Streamlit App Auto-Deploy Tool
echo ========================================================
echo.

:: Check Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed.
    pause
    exit /b
)

:: Configure Git User locally to avoid errors
git config user.name "Streamlit User"
git config user.email "user@example.com"

echo [1/5] Initializing Git...
if not exist .git (
    git init
)

echo.
echo [2/5] Adding files...
git add .

echo.
echo [3/5] Committing changes...
git commit -m "first commit" || echo No changes to commit

echo.
echo [4/5] Setting up remote repository...
git branch -M main
:: Remove existing origin to avoid conflicts
git remote remove origin 2>nul
:: Add the correct origin
git remote add origin https://github.com/micmicshopee-source/streamlit-ocr-app.git

echo.
echo [5/5] Pushing to GitHub...
echo Target: https://github.com/micmicshopee-source/streamlit-ocr-app.git
echo.
echo If a popup appears, please sign in to GitHub.
echo.
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   SUCCESS! Your code is now on GitHub.
    echo ========================================================
) else (
    echo.
    echo [ERROR] Push failed.
    echo Please check your internet connection or GitHub permissions.
)

pause
