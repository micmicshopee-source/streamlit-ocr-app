@echo off
REM Git 推送脚本
REM 用于推送更新到 GitHub

cd /d "d:\streamlit_ocr_app"

echo ========================================
echo 开始 Git 推送流程
echo ========================================
echo.

REM 删除可能存在的锁定文件
if exist ".git\index.lock" (
    echo 发现锁定文件，正在删除...
    del /f /q ".git\index.lock"
)

echo 步骤 1: 添加所有更改...
git add .
if %errorlevel% neq 0 (
    echo 错误: git add 失败
    pause
    exit /b 1
)

echo.
echo 步骤 2: 提交更改...
git commit -m "Update: 增加多用戶隔離、登錄註冊功能與 PDF 導出優化"
if %errorlevel% neq 0 (
    echo 错误: git commit 失败
    pause
    exit /b 1
)

echo.
echo 步骤 3: 推送到远程仓库...
git push origin main
if %errorlevel% neq 0 (
    echo 错误: git push 失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo Git 推送完成！
echo ========================================
pause
