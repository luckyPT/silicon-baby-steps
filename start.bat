@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo 请先安装 Node.js 22.12+：https://nodejs.org/
  pause
  exit /b 1
)
node scripts\check-node.mjs
if errorlevel 1 (
  pause
  exit /b 1
)
call npm ci --no-fund --no-audit
if errorlevel 1 (
  echo 依赖安装失败，请检查网络。
  pause
  exit /b 1
)
echo 打开 http://localhost:4173/ 开始练级。
call npm run dev
pause
