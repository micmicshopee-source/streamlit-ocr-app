# Git 推送脚本 (PowerShell)
# 用于推送更新到 GitHub

Set-Location "d:\streamlit_ocr_app"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "开始 Git 推送流程" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 删除可能存在的锁定文件
if (Test-Path ".git\index.lock") {
    Write-Host "发现锁定文件，正在删除..." -ForegroundColor Yellow
    Remove-Item ".git\index.lock" -Force -ErrorAction SilentlyContinue
}

Write-Host "步骤 1: 添加所有更改..." -ForegroundColor Green
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: git add 失败" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host ""
Write-Host "步骤 2: 提交更改..." -ForegroundColor Green
git commit -m "Fix: 修復刪除功能、篩選條件說明和導出按鈕標籤"
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: git commit 失败" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host ""
Write-Host "步骤 3: 推送到远程仓库..." -ForegroundColor Green
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: git push 失败" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git 推送完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Read-Host "按 Enter 键退出"
