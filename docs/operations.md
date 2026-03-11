# Operations Runbook: Team Communication Analytics Bot

## Services

- `api`: FastAPI application (webhook, health, admin).
- `worker`: Celery worker for analytics, reporting, maintenance.
- `beat`: Celery beat scheduler (daily reports, retention).
- `db`: PostgreSQL.
- `redis`: Redis for broker and minimal caching.

## Health Checks

- `GET /health/live` – basic liveness.
- `GET /health/ready` – checks DB and Redis connectivity.

If `status="degraded"` on `/health/ready`, inspect DB/Redis availability before routing traffic.

## Common Failure Modes

- **DB unavailable**: `/health/ready` shows `"db": false`. The worker and API will fail DB operations; investigate PostgreSQL container/service first.
- **Redis unavailable**: `/health/ready` shows `"redis": false`. Celery tasks may not start; check Redis container, then restart worker/beat.
- **LLM provider issues**: reporting tasks may mark reports as failed or rejected and write audit logs for `llm_*_failed`. No reports are delivered when verification fails.

## Celery Tasks and Retries

- Analytics tasks (`analytics.update_threads_for_chat`, `analytics.run_for_chat`) and reporting/maintenance tasks use bounded retries with exponential backoff.
- Inspect task state via Celery monitoring tools or logs; repeated failures should be correlated with external outages (DB, Redis, LLM, Telegram).

## Safe Restarts

1. Scale down `beat` and `worker`.
2. Restart `db` and `redis` if needed.
3. Run migrations (if applicable).
4. Bring up `db` → `redis` → `worker` → `beat` → `api`.

Idempotent handlers ensure that rerunning analytics and reporting does not create duplicate signals or reports.

