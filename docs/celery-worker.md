# Celery Worker 与 AI 转换任务

## 接口返回「AI转换任务已启动」代表什么？

接口 `POST /submissions/{id}/transform` 返回：

```json
{
  "message": "AI转换任务已启动",
  "task_id": "d5d85bf9-3a60-49d0-b994-b274f8dd6257",
  "submission_id": 30
}
```

表示**任务已成功投递到 Redis 队列**，**并不表示任务已经开始执行**。  
任务要真正执行，必须有一个 **Celery Worker** 在运行并消费该队列。

## 如何确认 Worker 是否在跑？

### 使用 Docker Compose 时

1. **看服务是否启动**
   ```bash
   docker-compose ps
   ```
   确认列表里有 **celery_worker** 且状态为 Up。

2. **若没有 celery_worker，单独启动**
   ```bash
   docker-compose up -d celery_worker
   ```

3. **看 Worker 日志（是否有收到任务、是否报错）**
   ```bash
   docker-compose logs -f celery_worker
   ```
   点击「AI改写」后，应能看到类似：
   - `Received task: transform_content[xxx]`
   - `开始AI转换任务: submission_id=30`
   - 若报错会在这里显示。

### 本地不用 Docker 时

在项目根目录（或 backend 目录）下启动 Worker：

```bash
cd backend
# 确保已激活虚拟环境，且 .env 中 CELERY_BROKER_URL 指向可用的 Redis（如 redis://localhost:6379/0）
celery -A app.tasks worker --loglevel=info
```

Redis 需单独安装并启动，且配置与 backend 使用的 `CELERY_BROKER_URL` 一致。

## 如何确认任务是否真的在执行？

1. **看任务日志表（后端）**  
   若已实现「AI 改写任务状态」接口，可调用：
   - `GET /submissions/{submission_id}/transform-status`  
   若返回 `status: "started"` 或 `"success"` / `"failed"`，说明 Worker 已执行过该投稿的任务。

2. **看 Worker 日志**  
   如上 `docker-compose logs -f celery_worker`，能看到任务接收与执行日志。

3. **看投稿状态**  
   执行成功后，投稿状态会变为 `completed`，草稿版本或内容会更新。

## 小结

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 接口返回成功但一直没结果 | Worker 未启动或未连上 Redis | 启动 `celery_worker` 并查看日志 |
| 前端一直轮询无变化 | 同上，或任务执行失败 | 查 Worker 日志与 `transform-status` |
| Worker 启动报错 | broker/backend 配置错误或 Redis 不可用 | 检查 `CELERY_BROKER_URL`、Redis 是否可访问 |

**建议**：使用 Docker 时务必执行 `docker-compose up -d` 或至少 `docker-compose up -d backend redis celery_worker`，保证 API、Redis 和 Worker 都在运行。
