@echo off
echo ========================================
echo 启动前端服务器 (Frontend Server)
echo ========================================
echo.

cd /d "%~dp0frontend"

echo 检查 Node.js 环境...
node --version
npm --version
echo.

echo 启动 Next.js 开发服务器...
echo 前端地址: http://localhost:3001
echo.

npm run dev

pause

