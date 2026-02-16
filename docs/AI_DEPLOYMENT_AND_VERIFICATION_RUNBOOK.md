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

