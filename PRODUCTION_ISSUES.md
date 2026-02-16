# 生产环境部署问题日志

## 问题记录

### 1. Playwright浏览器缺失问题（已解决）

**日期**: 2026-02-17

**问题描述**:
- 美篇邮件抓取失败：`Executable doesn't exist at /root/.cache/ms-playwright/chromium-1097/chrome`
- 手动发布美篇链接时报错
- 美篇内容需要JavaScript渲染，使用Playwright抓取，但Docker容器中未安装浏览器
- **关键问题**：Playwright浏览器安装在容器的 `/root/.cache/ms-playwright/` 目录，未挂载到宿主机，容器重启后丢失

**影响范围**:
- 美篇文章抓取功能完全不可用（邮件和手动发布）
- 投稿只保存邮件原文HTML，不包含实际内容和图片

**临时解决方案**（每次容器重启后需要执行）:
```bash
docker-compose exec backend playwright install chromium
docker-compose exec celery_worker playwright install chromium
```

**永久解决方案**:
已修改 `docker/backend/Dockerfile`，添加：
1. 修复包名：`libgdk-pixbuf2.0-0` → `libgdk-pixbuf-2.0-0`
2. Playwright所需的系统依赖（libgbm1, libxshmfence1等）
3. 在镜像构建时执行 `playwright install chromium`

**修改文件**:
- `docker/backend/Dockerfile` (commit: d72843b)

**生产部署步骤**:
```bash
# 1. 重新构建镜像（必须）
docker-compose build backend celery_worker

# 2. 启动容器
docker-compose up -d

# 3. 验证浏览器已安装
docker-compose exec backend ls -la /root/.cache/ms-playwright/chromium-1097/
docker-compose exec celery_worker ls -la /root/.cache/ms-playwright/chromium-1097/

# 4. 测试美篇抓取
# - 发送美篇邮件，检查celery日志
# - 手动发布页面输入美篇链接
```

**预防措施**:
- ⚠️ **生产部署前必须完整重建镜像**，不能依赖临时安装
- 所有需要浏览器的功能都应在Dockerfile中预装
- 新增第三方工具依赖时，必须同步更新Dockerfile
- 容器重启后验证关键依赖是否存在

---

## 部署检查清单

### 镜像构建前检查
- [ ] requirements.txt包含所有Python依赖
- [ ] Dockerfile包含所有系统依赖
- [ ] Playwright浏览器已安装（backend和celery_worker）
- [ ] LibreOffice已安装（Word文档处理）

### 部署后验证
- [ ] Playwright浏览器存在：`ls /root/.cache/ms-playwright/chromium-1097/`
- [ ] 公众号链接抓取正常
- [ ] 美篇链接抓取正常（邮件和手动发布）
- [ ] Word文档上传处理正常
- [ ] 图片上传OSS正常
- [ ] AI改写功能正常
- [ ] WordPress发布正常

---

## 相关命令

### 查看容器中已安装的浏览器
```bash
docker-compose exec backend playwright --version
docker-compose exec backend ls -la /root/.cache/ms-playwright/
docker-compose exec celery_worker ls -la /root/.cache/ms-playwright/
```

### 手动安装浏览器（临时，仅用于开发调试）
```bash
docker-compose exec backend playwright install chromium
docker-compose exec celery_worker playwright install chromium
```

### 重新构建镜像（生产部署必须）
```bash
# 完整重建
docker-compose build --no-cache backend celery_worker
docker-compose up -d

# 或快速重建
docker-compose build backend celery_worker
docker-compose up -d
```

---

## 更新记录

| 日期 | 问题 | 解决方案 | 状态 |
|------|------|----------|------|
| 2026-02-17 | Playwright浏览器缺失，容器重启后丢失 | 更新Dockerfile添加浏览器安装，生产部署需重建镜像 | ✅ 已解决 |
