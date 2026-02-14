@echo off
REM 荣耀AI审核发布系统 - Windows启动脚本

echo 🚀 启动荣耀AI审核发布系统...

REM 启动服务
echo 📦 启动Docker容器...
docker-compose up -d

REM 等待数据库启动
echo ⏳ 等待数据库启动...
timeout /t 5 /nobreak > nul

REM 运行数据库迁移
echo 🗄️  运行数据库迁移...
docker-compose exec backend alembic upgrade head

REM 创建初始管理员账号
echo 👤 创建初始管理员账号...
docker-compose exec backend python scripts/init_admin.py

echo ✅ 系统启动完成！
echo.
echo 📍 访问地址：
echo    - API文档: http://localhost:8000/docs
echo    - 前端界面: http://localhost:3000
echo    - 健康检查: http://localhost:8000/health
echo.
echo 👤 默认管理员账号：
echo    - 用户名: admin
echo    - 密码: admin123
echo.
echo 📝 查看日志: docker-compose logs -f
echo 🛑 停止服务: docker-compose down

pause
