# 荣耀AI审核发布系统 (Glory AI Audit System)

[![GitHub](https://img.shields.io/badge/GitHub-rongyao--ai-blue?logo=github)](https://github.com/nethao/rongyao-ai)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3-4FC08D?logo=vue.js)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

自动化内容处理与发布平台，用于多站点WordPress投稿管理。

## 功能特性

- 📧 自动邮件抓取与内容提取
- 🤖 AI智能语义转换（第一人称→第三人称）
- 📝 双栏对比审核界面
- 🖼️ 图片自动上传阿里云OSS
- 📤 一键发布到多个WordPress站点
- 📚 版本管理与历史回溯
- ⚡ 异步任务处理

## 技术栈

- **后端**: FastAPI + Python 3.11
- **数据库**: PostgreSQL 15
- **缓存/队列**: Redis
- **任务队列**: Celery
- **文档处理**: LibreOffice
- **AI**: OpenAI API
- **存储**: 阿里云OSS
- **容器化**: Docker + Docker Compose

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/nethao/rongyao-ai.git
cd rongyao-ai
```

2. 配置环境变量
```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入实际配置
```

3. 启动服务

**Linux/Mac:**
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

**Windows:**
```bash
scripts\start.bat
```

**或手动启动:**
```bash
# 启动所有服务
docker-compose up -d

# 等待数据库启动后，运行迁移
docker-compose exec backend alembic upgrade head

# 创建初始管理员账号
docker-compose exec backend python scripts/init_admin.py
```

4. 访问应用
- API文档: http://localhost:8000/docs
- 前端界面: http://localhost:3000
- 健康检查: http://localhost:8000/health

### 默认账号

- 用户名: `admin`
- 密码: `admin123`
- ⚠️ 请在生产环境中立即修改默认密码！

### 开发模式

```bash
# 查看日志
docker-compose logs -f backend

# 进入容器
docker-compose exec backend bash

# 停止服务
docker-compose down

# 重启服务
docker-compose restart backend
```

## 项目结构

```
.
├── backend/                 # 后端应用
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic模型
│   │   ├── services/       # 业务逻辑
│   │   ├── tasks/          # Celery任务
│   │   └── utils/          # 工具函数
│   └── requirements.txt
├── docker/                  # Docker配置
└── docker-compose.yml      # 服务编排
```

## 开发指南

详见 `.kiro/specs/glory-ai-audit-system/` 目录下的规格文档：
- `requirements.md` - 需求文档
- `design.md` - 设计文档
- `tasks.md` - 任务列表

## 许可证

MIT License
