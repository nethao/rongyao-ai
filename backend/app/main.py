"""
FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import config, auth, submissions, drafts, wordpress_sites, monitoring

app = FastAPI(
    title="荣耀AI审核发布系统",
    description="Glory AI Audit System - 自动化内容处理与发布平台",
    version="0.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(wordpress_sites.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")


@app.get("/")
async def root():
    """健康检查端点"""
    return {
        "message": "荣耀AI审核发布系统",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
