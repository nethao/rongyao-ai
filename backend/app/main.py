"""
FastAPI应用主入口
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api import config, auth, users, submissions, drafts, wordpress_sites, monitoring, analytics

logger = logging.getLogger(__name__)

app = FastAPI(
    title="荣耀AI审核发布系统",
    description="Glory AI Audit System - 自动化内容处理与发布平台",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS 白名单：通过 ALLOWED_ORIGINS 环境变量配置
_origins = [
    o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()
]
if not _origins:
    _origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(wordpress_sites.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """生产环境不暴露内部异常堆栈"""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


@app.get("/")
async def root():
    return {
        "message": "荣耀AI审核发布系统",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
