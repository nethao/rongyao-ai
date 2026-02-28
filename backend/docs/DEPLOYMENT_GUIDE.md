# 荣耀AI审核发布系统 - 部署指南

## 系统要求

### 硬件要求
- CPU: 4核心或以上
- 内存: 8GB或以上
- 磁盘: 50GB可用空间（包含数据库和临时文件）

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Linux操作系统（推荐Ubuntu 20.04+）
- 处理RAR/7Z附件需系统依赖：`p7zip-full`、`unrar`（Docker部署已内置，重建镜像生效）

## 环境变量配置

创建 `.env` 文件在项目根目录：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://glory_user:your_password@postgres:5432/glory_db

# Redis配置
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# JWT密钥（请使用强密码）
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 加密密钥（用于配置加密）
ENCRYPTION_KEY=your-32-character-encryption-key

# OpenAI API配置
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1

# 阿里云OSS配置
OSS_ACCESS_KEY_ID=your-oss-access-key-id
OSS_ACCESS_KEY_SECRET=your-oss-access-key-secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=your-bucket-name

# IMAP邮箱配置
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USER=your-email@example.com
IMAP_PASSWORD=your-email-password
IMAP_USE_SSL=true

# 应用配置
APP_ENV=production
LOG_LEVEL=INFO

# 数据清理配置
IMAGE_COMPRESS_DAYS=365
DATA_DELETE_DAYS=730
ATTACHMENT_RETENTION_DAYS=15
```

## 部署步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd glory-ai-audit-system
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
nano .env
```

### 3. 构建和启动服务

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 创建初始管理员账号（可选）
docker-compose exec backend python -m app.scripts.create_admin
```

### 5. 验证部署

访问以下端点验证服务：

- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 前端界面: http://localhost:3000

## 服务管理

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart celery-worker
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v
```

## 数据库管理

### 备份数据库

```bash
# 创建备份
docker-compose exec postgres pg_dump -U glory_user glory_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 恢复数据库

```bash
# 恢复备份
docker-compose exec -T postgres psql -U glory_user glory_db < backup_20240101_120000.sql
```

### 运行迁移

```bash
# 创建新迁移
docker-compose exec backend alembic revision --autogenerate -m "description"

# 应用迁移
docker-compose exec backend alembic upgrade head

# 回滚迁移
docker-compose exec backend alembic downgrade -1
```

## Celery任务管理

### 启动Worker

```bash
# Worker已通过docker-compose自动启动
# 手动启动（如需要）
docker-compose exec backend celery -A app.tasks worker --loglevel=info
```

### 启动Beat调度器

```bash
# Beat已通过docker-compose自动启动
# 手动启动（如需要）
docker-compose exec backend celery -A app.tasks beat --loglevel=info
```

### 监控任务

```bash
# 查看活动任务
docker-compose exec backend celery -A app.tasks inspect active

# 查看已注册任务
docker-compose exec backend celery -A app.tasks inspect registered

# 查看统计信息
docker-compose exec backend celery -A app.tasks inspect stats
```

## 生产环境优化

### 1. 使用HTTPS

配置Nginx反向代理：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 配置防火墙

```bash
# 只开放必要端口
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### 3. 设置自动重启

编辑 `docker-compose.yml`，添加重启策略：

```yaml
services:
  backend:
    restart: always
  celery-worker:
    restart: always
  celery-beat:
    restart: always
```

### 4. 配置日志轮转

创建 `/etc/logrotate.d/glory-ai`：

```
/var/log/glory-ai/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
```

### 5. 监控和告警

使用Prometheus + Grafana监控系统指标：

```bash
# 添加监控服务到docker-compose.yml
# 配置告警规则
# 设置通知渠道（邮件、Slack等）
```

## 故障排查

### 服务无法启动

1. 检查端口占用：`netstat -tulpn | grep :8000`
2. 查看服务日志：`docker-compose logs backend`
3. 验证环境变量：`docker-compose config`

### 数据库连接失败

1. 检查数据库服务：`docker-compose ps postgres`
2. 验证连接字符串：检查 `.env` 中的 `DATABASE_URL`
3. 测试连接：`docker-compose exec postgres psql -U glory_user -d glory_db`

### Celery任务不执行

1. 检查Worker状态：`docker-compose ps celery-worker`
2. 查看Worker日志：`docker-compose logs celery-worker`
3. 验证Redis连接：`docker-compose exec redis redis-cli ping`

### OSS上传失败

1. 验证OSS配置：检查 `.env` 中的OSS配置
2. 测试网络连接：`curl https://oss-cn-hangzhou.aliyuncs.com`
3. 检查权限：确认OSS账号有上传权限

## 性能优化

### 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_submissions_status ON submissions(status);
CREATE INDEX idx_submissions_created_at ON submissions(created_at);
CREATE INDEX idx_drafts_status ON drafts(status);
CREATE INDEX idx_task_logs_created_at ON task_logs(created_at);

-- 定期清理
VACUUM ANALYZE;
```

### Redis优化

```bash
# 配置最大内存
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Celery优化

```python
# 增加Worker数量
celery_app.conf.update(
    worker_concurrency=4,  # 根据CPU核心数调整
    worker_prefetch_multiplier=4,
)
```

## 安全建议

1. **定期更新密钥**：定期更换JWT密钥和加密密钥
2. **限制API访问**：配置IP白名单或使用VPN
3. **启用审计日志**：记录所有管理员操作
4. **定期备份**：每日自动备份数据库
5. **监控异常**：设置告警规则，及时发现异常行为

## 扩展部署

### 水平扩展

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
  celery-worker:
    deploy:
      replicas: 5
```

### 负载均衡

使用Nginx配置负载均衡：

```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

## 联系支持

如遇到部署问题，请联系技术支持团队。
