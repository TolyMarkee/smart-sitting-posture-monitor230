# 一键启动智能坐姿监测系统（Windows PowerShell）

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  智能坐姿监测系统 - 一键启动" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$ProjectDir = Split-Path -Parent $PSScriptRoot

# 1. 安装后端依赖并启动
Write-Host "`n[1/2] 启动 FastAPI 后端..." -ForegroundColor Yellow
Set-Location "$ProjectDir\backend"
pip install -r requirements.txt -q 2>$null
$BackendJob = Start-Process -NoNewWindow -PassThru `
    python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"
Write-Host "  后端 PID: $($BackendJob.Id) → http://localhost:8000"

Start-Sleep -Seconds 2

# 2. 安装前端依赖并启动
Write-Host "`n[2/2] 启动 Vue3 前端..." -ForegroundColor Yellow
Set-Location "$ProjectDir\frontend"
npm install --silent 2>$null
$FrontendJob = Start-Process -NoNewWindow -PassThru `
    npm -ArgumentList "run", "dev"
Write-Host "  前端 PID: $($FrontendJob.Id) → http://localhost:5173"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  启动完成" -ForegroundColor Green
Write-Host "  后端: http://localhost:8000" -ForegroundColor Green
Write-Host "  前端: http://localhost:5173" -ForegroundColor Green
Write-Host "  测试用户: test / 123456" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "按 Ctrl+C 停止所有服务"
