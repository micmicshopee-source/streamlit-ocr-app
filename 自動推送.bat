@echo off
chcp 65001 >nul
echo ========================================
echo 自動推送修復更新到 GitHub
echo ========================================
echo.

cd /d "d:\streamlit_ocr_app"

echo [1/4] 檢查並刪除鎖定文件...
if exist ".git\index.lock" (
    echo 發現鎖定文件，正在刪除...
    del /f /q ".git\index.lock" 2>nul
    timeout /t 1 /nobreak >nul
)

echo [2/4] 添加修改的文件...
git add app.py
git add "問題修復報告_20260126.md"
git add "推送修復更新.md"
if %errorlevel% neq 0 (
    echo.
    echo ❌ 錯誤: git add 失敗
    echo.
    echo 可能的原因:
    echo 1. 其他程序正在使用 Git (如 VS Code)
    echo 2. 文件權限問題
    echo.
    echo 解決方法:
    echo 1. 關閉 VS Code 和其他可能使用 Git 的程序
    echo 2. 以管理員身份運行此腳本
    echo 3. 手動執行命令: git add app.py "問題修復報告_20260126.md"
    pause
    exit /b 1
)

echo [3/4] 提交更改...
git commit -m "Fix: 修復刪除功能、篩選條件說明和導出按鈕標籤"
if %errorlevel% neq 0 (
    echo.
    echo ❌ 錯誤: git commit 失敗
    echo.
    echo 可能沒有需要提交的更改，或提交失敗
    pause
    exit /b 1
)

echo [4/4] 推送到遠程倉庫...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo ❌ 錯誤: git push 失敗
    echo.
    echo 可能的原因:
    echo 1. 網絡連接問題
    echo 2. 認證問題
    echo 3. 遠程倉庫權限問題
    echo.
    echo 請檢查網絡連接和 Git 認證設置
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Git 推送完成！
echo ========================================
echo.
echo Streamlit Cloud 將自動檢測到更改並重新部署
echo 通常需要 1-2 分鐘完成部署
echo.
pause
