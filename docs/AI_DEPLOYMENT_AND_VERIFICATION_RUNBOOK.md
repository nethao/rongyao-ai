# AI Deployment and Verification Runbook

> Purpose: this document is written for an AI operator to deploy and verify this project in production-like environment.
> Language: Chinese.
> Policy: prioritize safety, repeatability, and rollback readiness.

---

## 1. Task Contract (for AI)

You are an execution agent for production deployment and verification.

Hard rules:
- Do **not** modify business code unless explicitly approved.
- Do **not** expose secrets in logs/output.
- Do **not** run destructive database commands (`DROP`, `TRUNCATE`, reset).
- Stop and request human confirmation before any risky step.
- Every step must produce a result (`PASS` / `FAIL` / `BLOCKED`) with evidence.

Output requirements:
- Keep a step-by-step execution log.
- Produce final report in the JSON format defined in section 10.

---

## 2. Required Inputs (fill before execution)

Provide this YAML to the AI before it starts:

```yaml
environment:
  name: production
  server_ip: ""
  ssh_user: ""
  ssh_port: 22
  domain_frontend: "e.com"
  domain_sites: ["a.com", "b.com", "c.com", "d.com"]

secrets:
  jwt_secret_key: ""
  database_url: ""
  redis_url: ""
  openai_api_key: ""
  imap_host: ""
  imap_port: 993
  imap_user: ""
  imap_password: ""
  oss_access_key_id: ""
  oss_access_key_secret: ""
  oss_endpoint: ""
  oss_bucket_name: ""

deployment:
  use_docker_compose: true
  compose_file: "docker-compose.yml"
  expected_backend_port: 8000
  expected_frontend_port: 3000
  expected_nginx_ports: [80, 443]

policy:
  allow_restart_services: true
  allow_migration: true
  allow_data_cleanup: false
```

If any required field is empty, mark as `BLOCKED` and stop.

---

## 3. Current Project Topology (must verify)

Expected services:
- `backend` (FastAPI)
- `celery_worker` (task worker)
- `db` (PostgreSQL)
- `redis`
- `frontend`
- `nginx`
- optional WordPress containers (`wp_a`, `wp_b`, `wp_c`, `wp_d`, `wp_db`)

Expected key routes:
- `GET /health`
- `GET /api/monitoring/health`
- analytics endpoints under `/api/analytics/*`

---

## 4. Preflight Checklist (Gate A)

AI must execute and record:

1) Infrastructure
- Docker/Compose available
- Disk > 20GB free
- Memory healthy
- Time sync normal

2) Security baseline
- DB/Redis not unintentionally exposed to public network
- Secrets loaded from environment, no default insecure values
- CORS policy reviewed for production

3) Config sanity
- `.env` present and complete
- `JWT_SECRET_KEY` is strong and non-default
- Database connection string points to target env

Gate rule:
- Any failed critical check => `BLOCKED`, stop and report.

---

## 5. Deployment Procedure (Gate B)

Execute in order:

1) Pull/update source
- checkout target release/tag/commit
- record exact git revision

2) Build and start services
- build images
- start required services
- wait until health checks pass

3) Database migration/init
- run migration/init scripts if required
- verify schema readiness

4) Worker readiness
- ensure `celery_worker` is running
- verify task queue connectivity (`redis`)

Required evidence:
- service list/status
- health endpoint responses
- migration result summary

---

## 6. Functional Verification (Gate C)

### C1. Core API
- `GET /health` -> healthy
- auth login flow works
- submissions list API works

### C2. Email ingestion pipeline
- trigger fetch emails
- verify status polling updates from start -> complete/fail
- ensure logs are scoped to current run

### C3. Word/Archive processing
- test one `.doc/.docx` case
- test one `.zip` with Word + images
- verify draft content and image placeholders are resolved in display path

### C4. Analytics page dependencies
- verify all endpoints:
  - `/api/analytics/overview`
  - `/api/analytics/trends`
  - `/api/analytics/editors`
  - `/api/analytics/media`
  - `/api/analytics/units`
  - `/api/analytics/sites`
  - `/api/analytics/sources`
- no 500 responses

Gate rule:
- Any P0/P1 failure => do not proceed to release confirmation.

---

## 7. Production Readiness Audit (Gate D)

The AI must flag risks by severity:

- `P0` must-fix before go-live
- `P1` high risk, needs mitigation plan
- `P2` acceptable with follow-up

Minimum audit topics:
- startup mode (dev vs prod)
- CORS strictness
- secret defaults and leakage risk
- TLS/HTTPS completeness
- rollback availability
- observability and alerting

---

## 8. Rollback Plan (must be tested)

Rollback trigger examples:
- sustained 5xx
- core flow unavailable (login, fetch, publish)
- data corruption risk

Rollback actions:
1) stop new writes if needed
2) restore previous app version
3) restart services
4) verify health + smoke tests
5) announce rollback status

AI must confirm rollback command readiness **before** release confirmation.

---

## 9. Go/No-Go Decision Rules

`GO` only if all conditions are true:
- Gate A/B/C passed
- no unresolved P0
- rollback tested/documented
- final smoke test passed

Otherwise return `NO_GO` with exact blockers.

---

## 10. Final Report Format (AI must output JSON)

```json
{
  "decision": "GO | NO_GO",
  "timestamp": "ISO-8601",
  "release": {
    "git_revision": "",
    "environment": "production"
  },
  "gates": {
    "A_preflight": "PASS | FAIL | BLOCKED",
    "B_deploy": "PASS | FAIL | BLOCKED",
    "C_functional": "PASS | FAIL | BLOCKED",
    "D_audit": "PASS | FAIL | BLOCKED"
  },
  "checks": [
    {
      "id": "C4_analytics_sites",
      "status": "PASS | FAIL | BLOCKED",
      "evidence": "short evidence"
    }
  ],
  "risks": [
    {
      "severity": "P0 | P1 | P2",
      "title": "",
      "impact": "",
      "mitigation": ""
    }
  ],
  "rollback": {
    "ready": true,
    "tested": true,
    "notes": ""
  },
  "next_actions": [
    "action 1",
    "action 2"
  ]
}
```

---

## 11. Human Approval Checkpoint

Before final `GO`, AI must ask human:
- Confirm release window
- Confirm backup exists
- Confirm rollback owner on duty

If any item is unconfirmed, return `NO_GO`.



---

## 12. 待配置项目（上线后添加）

### Celery Beat定时任务（邮件自动抓取）

**当前状态**：
- ✅ 定时任务代码已配置（每5分钟抓取邮件）
- ❌ Celery Beat服务未启动
- ✅ 手动点击"获取投稿"按钮可以抓取

**配置方法**：

1. 在`docker-compose.yml`中添加celery_beat服务：

```yaml
  celery_beat:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    command: celery -A app.tasks:celery_app beat --loglevel=info
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - db
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/glory_audit
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    networks:
      - app-network
```

2. 启动服务：
```bash
docker-compose up -d celery_beat
```

3. 验证定时任务：
```bash
docker-compose logs -f celery_beat
```

应该看到类似日志：
```
[INFO] beat: Starting...
[INFO] Scheduler: Sending due task fetch-emails-every-5-minutes
```

**定时任务配置**：
- 邮件抓取：每5分钟执行一次
- 清理任务：每天凌晨2点执行

**配置文件位置**：`backend/app/tasks/__init__.py`

**验证步骤**：
1. 确认celery_beat容器运行：`docker-compose ps | grep beat`
2. 查看日志确认任务调度：`docker-compose logs celery_beat`
3. 等待5分钟后检查是否有新投稿
4. 查看celery_worker日志确认任务执行：`docker-compose logs celery_worker | grep fetch_emails`

**注意事项**：
- Celery Beat只需要一个实例运行
- 确保Redis服务正常运行
- 定时任务时间可在`backend/app/tasks/__init__.py`中调整
