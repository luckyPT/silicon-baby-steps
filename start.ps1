$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw '请先安装 Node.js 22.12+（推荐24 LTS）：https://nodejs.org/' }
  node scripts/check-node.mjs
  if ($LASTEXITCODE -ne 0) { throw 'Node.js版本不满足要求。' }
  npm ci --no-fund --no-audit
  if ($LASTEXITCODE -ne 0) { throw '依赖安装失败，请检查网络后重试。' }
  Write-Host '打开 http://localhost:4173/ 开始练级。'
  npm run dev
  if ($LASTEXITCODE -ne 0) { throw '服务启动失败。' }
} finally { Pop-Location }
