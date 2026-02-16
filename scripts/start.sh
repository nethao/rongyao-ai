#!/bin/bash

# 荣耀AI审核发布系统 - 启动脚本

echo "🚀 启动荣耀AI审核发布系统..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 启动服务（包含 backend、celery_worker、redis、db、frontend 等）
echo "📦 启动Docker容器（含 Celery Worker，AI 改写依赖此服务）..."
docker-compose up -d

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 5

# 运行数据库迁移
echo "🗄️  运行数据库迁移..."
docker-compose exec backend alembic upgrade head

# 创建初始管理员账号
echo "👤 创建初始管理员账号..."
docker-compose exec backend python scripts/init_admin.py

echo "✅ 系统启动完成！"
echo ""
echo "📍 访问地址："
echo "   - API文档: http://localhost:8000/docs"
echo "   - 前端界面: http://localhost:3000"
echo "   - 健康检查: http://localhost:8000/health"
echo ""
echo "👤 默认管理员账号："
echo "   - 用户名: admin"
echo "   - 密码: admin123"
echo ""
echo "📝 查看日志: docker-compose logs -f"
echo "📝 查看 AI 任务 Worker 日志: docker-compose logs -f celery_worker"
echo "🛑 停止服务: docker-compose down"
echo ""
echo "⚠️  若「AI 改写」无反应，请确认 celery_worker 已启动: docker-compose ps"
