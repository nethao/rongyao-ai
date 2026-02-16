# 生产环境部署问题日志

## 问题记录

### 1. Playwright浏览器缺失问题

**日期**: 2026-02-17

**问题描述**:
- 手动发布功能测试美篇链接时报错：`Executable doesn't exist at /root/.cache/ms-playwright/chromium-1097/chrome-linux/chrome`
- 美篇内容需要JavaScript渲染，使用Playwright抓取，但Docker容器中未安装浏览器

**影响范围**:
- 美篇文章抓取功能完全不可用
- 手动发布美篇类型失败

**临时解决方案**:
```bash
docker-compose exec backend playwright install chromium
```

**永久解决方案**:
已修改 `docker/backend/Dockerfile`，添加：
1. Playwright所需的系统依赖（libgbm1, libxshmfence1等）
2. 在镜像构建时执行 `playwright install chromium`

**修改文件**:
- `docker/backend/Dockerfile`

**验证方法**:
```bash
# 重新构建镜像
docker-compose build backend

# 启动容器
docker-compose up -d backend

# 测试美篇链接
# 在前端手动发布页面输入美篇链接，应该能正常获取内容
```

**预防措施**:
- 所有需要浏览器的功能（如网页抓取）都应在Dockerfile中预装浏览器
- 新增第三方工具依赖时，必须同步更新Dockerfile
- 生产部署前必须完整重建镜像，不依赖临时安装

---

## 部署检查清单

### 镜像构建前检查
- [ ] requirements.txt包含所有Python依赖
- [ ] Dockerfile包含所有系统依赖
- [ ] Playwright浏览器已安装
- [ ] LibreOffice已安装（Word文档处理）

### 部署后验证
- [ ] 公众号链接抓取正常
- [ ] 美篇链接抓取正常
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
```

### 手动安装浏览器（临时）
```bash
docker-compose exec backend playwright install chromium
```

### 重新构建镜像（永久）
```bash
docker-compose build backend
docker-compose up -d backend
```

---

## 更新记录

| 日期 | 问题 | 解决方案 | 负责人 |
|------|------|----------|--------|
| 2026-02-17 | Playwright浏览器缺失 | 更新Dockerfile添加浏览器安装 | Kiro AI |
