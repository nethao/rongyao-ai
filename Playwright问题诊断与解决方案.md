# Playwright 问题诊断与解决方案（美篇抓取）

**最后更新**：2026-02-26

---

## 当前状态（已修复）

美篇抓取已改为 **Crawl4AI 优先、Playwright 兜底**，在现有 Docker 环境下**无需安装/修复 Playwright** 即可正常抓取美篇。

- **代码**：`backend/app/services/web_fetcher.py` 中 `fetch_meipian_article_async()` 先调 Crawl4AI，失败再尝试 Playwright。
- **生效**：重启 `backend` 与 `celery_worker` 后，邮件中的美篇链接或手动发稿选择「美篇」并填链接即可使用。

**若仍失败可快速排查**：
1. 看后端或 Celery 日志：`docker-compose logs backend celery_worker`，搜 `美篇`、`Crawl4AI`、`抓取.*失败`。
2. 确认链接是 `https://www.meipian.cn/...` 或 `https://meipian.cn/...`（白名单已包含）。
3. 确认 `crawl4ai` 已安装：`docker-compose exec backend pip show crawl4ai`。
4. 重启服务使代码生效：`docker-compose restart backend celery_worker`（若代码挂载了 `./backend`，改完即生效）。
5. **若日志显示 Crawl4AI 也报错（例如浏览器未找到）**：Crawl4AI 底层可能使用 Playwright，需在容器内正确安装 Chromium，见下方 **方案 A**（在 appuser 下执行 `playwright install chromium`）。

---

## 问题现状（历史原因）

### 核心问题
**Playwright Chromium 在 Docker 容器中无法启动**，导致原先仅依赖 Playwright 的美篇抓取失败。

### 错误表现
1. **浏览器文件丢失**
   - 手动复制到 `/app/.cache/ms-playwright/` 的 Chromium 在容器重启后消失
   - 错误：`Executable doesn't exist at .../chrome-headless-shell`

2. **启动超时/崩溃**
   - `browser.launch()` 超时（30 秒）
   - 错误：`chrome_crashpad_handler: --database is required`、SIGTRAP

3. **依赖/路径**
   - Dockerfile 中 `playwright install chromium` 在 root 下执行，运行时为 `appuser`，浏览器路径不一致

### 根本原因
- 安装时机与运行用户不一致：root 安装的 Chromium，appuser 运行时找不到
- 可选：依赖冲突（若单独升级 playwright 可能与 crawl4ai 等冲突）

---

## 解决方案

### 方案 A：修复 Playwright（推荐，适合长期维护）

#### 优点
- 美篇抓取精度高（使用精确的 CSS 选择器）
- 符合原有架构设计
- 可复用于其他需要 JS 渲染的网站

#### 缺点
- 需要重建容器（约 5-10 分钟）
- 增加镜像体积（~200MB）

#### 实施步骤

**1. 修改 Dockerfile**
```dockerfile
# 在 USER appuser 之后安装 Playwright
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app /tmp/glory_audit

USER appuser

# 在 appuser 身份下安装浏览器
RUN playwright install chromium

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

**2. 重建容器**
```bash
cd ~/rongyao-ai
docker-compose build backend
docker-compose up -d backend celery_worker
```

**3. 验证**
```bash
docker-compose exec backend python -c "
from app.services.web_fetcher import WebFetcher
fetcher = WebFetcher()
title, content, images, html = fetcher.fetch_meipian_article('https://www.meipian.cn/5jwb658d')
print(f'标题: {title}')
print(f'图片数: {len(images)}')
"
```

---

### 方案 B：美篇改用 Crawl4AI（已采用）

- **已实现**：`web_fetcher.py` 中美篇抓取为 **Crawl4AI 优先，Playwright 兜底**，无需改 Docker 即可在容器内抓美篇。
- **优点**：无需重建镜像；与通用 URL 抓取统一用 Crawl4AI。
- **缺点**：提取精度可能略逊于原 Playwright + 美篇专用选择器；若需可再启用方案 A 优化兜底。
- **重启生效**：`docker-compose restart backend celery_worker`

---

## 已完成的工作

✅ **Crawl4AI 安装**（v0.4.247）  
✅ **通用网站抓取**（`fetch_generic_url_async()`）  
✅ **邮件解析支持**（`OTHER_URL` 类型）  
✅ **美篇抓取**（`fetch_meipian_article_async()`：**Crawl4AI 优先，Playwright 兜底**）  
✅ **Docker 下美篇可用**（无需修复 Playwright 即可抓取美篇）  

⚠️ **Playwright 兜底**（仅在 Crawl4AI 失败时使用；Docker 内仍可能因无 Chromium 而失败，不影响主流程）

---

## 技术细节

### 当前架构（已实现）
```
邮件 → EmailParser.extract_url() → ContentType 判断
  ├─ WECHAT_ARTICLE → fetch_wechat_article()
  ├─ MEIPIAN_ARTICLE → fetch_meipian_article() [Crawl4AI 优先 → Playwright 兜底]
  └─ OTHER_URL       → fetch_generic_url()     [Crawl4AI]
```

---

## 关键文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `backend/requirements.txt` | ✅ 已修复 | 移除冲突依赖 |
| `docker/backend/Dockerfile` | ⚠️ 需修改 | Playwright 安装顺序错误 |
| `backend/app/services/web_fetcher.py` | ✅ 已实现 | 美篇/通用抓取逻辑 |
| `backend/app/tasks/email_tasks.py` | ✅ 已实现 | OTHER_URL 处理 |
| `backend/app/services/email_parser.py` | ✅ 已实现 | OTHER_URL 提取 |

---

## 推荐决策与下一步

- **当前已采用**：混合方案（美篇优先 Crawl4AI，失败再 Playwright）。Docker 下无需改镜像即可抓美篇。
- **若 Crawl4AI 提取质量不理想**：可再实施 **方案 A**（在 Dockerfile 中按 appuser 安装 Playwright Chromium），使兜底路径在容器内也可用。
- **验证美篇抓取**：重启服务后，用「手动发稿」选美篇并填入链接，或发送含美篇链接的邮件，看投稿列表是否出现抓取内容；失败时查 `backend` / `celery_worker` 日志中的 `抓取美篇文章失败` 或 `Crawl4AI` 相关报错。
