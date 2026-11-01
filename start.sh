#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo '请先安装 Node.js 22.12+（推荐24 LTS）：https://nodejs.org/' >&2
  exit 1
fi
node scripts/check-node.mjs
npm ci --no-fund --no-audit
printf '\n硅基学步已经准备好。打开 http://localhost:4173/ 开始练级。\n\n'
npm run dev
