# Buyunaihe Service Contracts

Shared contracts for all services. All services MUST follow these exactly.

## Service ports
| service | port | notes |
|---|---|---|
| frontend (nginx) | 80 | Vue 3 SPA |
| backend (FastAPI) | 8080 | main REST API, base path `/api` |
| agent-web (Flask) | 5001 | AI suggestion sync + result query |
| agent-worker | - | RabbitMQ consumer (ai_audit queue) |
| mysql | 3306 | dbs: `labelhub`, `labelhub_agent` |
| redis | 6379 | sessions/cache |
| rabbitmq | 5672 / 15672 | amqp + management |
| minio | 9000 / 9001 | s3 + console |

## Auth
- Backend issues a JWT token (HS256, secret from env `JWT_SECRET`, TTL 24h).
- Frontend sends `Authorization: Bearer <token>` on all `/api` requests except `/api/auth/login`.
- JWT payload: `{ "sub": user_id, "username", "role_code", "exp" }`.
- Roles: `owner`, `admin`, `labeler`, `reviewer`, `agent`.
- Default seeded users (password `123456`): `admin`/owner, `labeler1`/labeler, `reviewer1`/reviewer.
- Password hashing: bcrypt.

## Standard response envelope (backend)
```json
{ "code": 0, "message": "ok", "data": <any> }
```
Error: `code` != 0, `message` describes error, `data` null. HTTP status reflects error (401/403/404/400/500).

## Backend REST API (`/api`)

### Auth
- `POST /api/auth/login` `{username, password}` -> `{token, user:{id,username,nickname,role_code,avatar_url}}`
- `POST /api/auth/logout` -> `{}`
- `GET /api/auth/me` -> `user`
- `GET /api/users` (owner/admin) -> `[user]`
- `POST /api/users` (owner/admin) `{username,password,nickname,role_code,email,phone}` -> `user`
- `PUT /api/users/{id}` -> `user`
- `DELETE /api/users/{id}` -> `{}`

### Templates
- `GET /api/templates?status=&keyword=` -> `[template]`
- `POST /api/templates` `{name,description,schema}` -> `template`
- `GET /api/templates/{id}` -> `template` (schema included)
- `PUT /api/templates/{id}` `{name,description,schema}` -> `template`
- `DELETE /api/templates/{id}` -> `{}`
- `POST /api/templates/{id}/publish` -> `template`
- `POST /api/templates/{id}/archive` -> `template`

### Template `schema` shape (Schema-driven materials)
```json
{
  "materials": [
    {
      "id": "m1",
      "fieldKey": "label",
      "label": "分类标签",
      "type": "radio|checkbox|select|text|textarea|number|file|image|json|llm_prompt",
      "required": true,
      "options": ["A","B","C"],
      "props": {},
      "sortOrder": 0
    }
  ]
}
```
The same `schema` drives dynamic form rendering on annotation and review pages.

### Datasets
- `GET /api/datasets` -> `[dataset]`
- `POST /api/datasets` `{name,description}` -> `dataset`
- `GET /api/datasets/{id}` -> `dataset`
- `DELETE /api/datasets/{id}` -> `{}`
- `POST /api/datasets/{id}/upload` (multipart, field `file`) -> `dataset` (parses file, creates items)
- `GET /api/datasets/{id}/items?page=&size=` -> `{items,total,fields}`
- `POST /api/datasets/{id}/map-fields` `{mapping:{templateFieldKey: datasetField}}` -> `dataset`
Supported upload formats: `.json`, `.jsonl`, `.csv`, `.xlsx`. Parse into `dataset_items.raw_data`.

### Tasks
- `GET /api/tasks?status=&keyword=` -> `[task]`
- `POST /api/tasks` `{name,description,template_id,dataset_id,enable_ai_audit,enable_ai_suggestion}` -> `task`
- `GET /api/tasks/{id}` -> `task` (with template, dataset, progress summary)
- `PUT /api/tasks/{id}` -> `task`
- `DELETE /api/tasks/{id}` -> `{}`
- `POST /api/tasks/{id}/publish` -> `task` (generates task_items from dataset_items)
- `POST /api/tasks/{id}/pause` -> `task`
- `POST /api/tasks/{id}/complete` -> `task`
- `GET /api/tasks/{id}/progress` -> `{total,pending,annotating,submitted,ai_reviewing,reviewed,approved,rejected,completed}`
- `POST /api/tasks/{id}/assign` `{assignments:[{user_id,role}]}` -> `{}`
- `GET /api/tasks/{id}/assignees` -> `[assignment]`
- `GET /api/tasks/{id}/items?status=&page=&size=` -> `{items,total}`
- `GET /api/tasks/{id}/items/{itemId}` -> task item with dataset raw_data + template schema + current result

Task statuses: `draft`, `published`, `paused`, `completed`, `archived`.
Task item statuses: `pending`, `annotating`, `submitted`, `ai_reviewing`, `reviewed`, `approved`, `rejected`, `completed`.

### Annotation (labeler)
- `GET /api/annotation/square?status=&keyword=` -> `[task]` (published tasks available to labeler)
- `POST /api/annotation/tasks/{id}/claim` -> `{task_item_id}` (claims next unassigned item)
- `GET /api/annotation/items/{itemId}` -> `{item, template_schema, raw_data, result, suggestion}`
- `PUT /api/annotation/items/{itemId}/draft` `{result}` -> `{result}` (status -> annotating)
- `POST /api/annotation/items/{itemId}/submit` `{result}` -> `{result}` (status -> submitted; if task enable_ai_audit, dispatches audit to RabbitMQ and status -> ai_reviewing)
- `POST /api/annotation/items/{itemId}/ai-suggestion` -> `{suggestion_id}` (calls agent-web, async)
- `GET /api/annotation/suggestions/{suggestionId}` -> `{status, suggestion}` (polls agent-web)

### Review (reviewer)
- `GET /api/review/tasks?keyword=` -> `[task]` (tasks where current user is reviewer & have items to review)
- `GET /api/review/tasks/{id}/items?status=&page=&size=` -> `{items,total}`
- `GET /api/review/items/{itemId}` -> `{item, template_schema, raw_data, result, ai_report}`
- `GET /api/review/items/{itemId}/ai-report` -> `{status, score, issues, reasoning, suggestion}`
- `POST /api/review/items/{itemId}/decision` `{decision, comment}` -> `{task_item}` (decision: `approved`|`rejected`|`modify_approve`; status -> approved/rejected/completed; transition logged)

### Export
- `POST /api/export` `{task_id, format}` (format: json|jsonl|csv|xlsx) -> `export_record`
- `GET /api/export?task_id=` -> `[export_record]`
- `GET /api/export/{id}` -> `export_record` (with files)
- `GET /api/export/{id}/download` -> redirect/signed url to MinIO object

### Stats
- `GET /api/stats/overview` -> `{task_count, dataset_count, template_count, user_count, pending_review, completed_items}`
- `GET /api/stats/task/{id}` -> `{progress, labeler_stats:[...], timeline:[...]}` (for ECharts)

## agent-web HTTP API (Flask, port 5001)
Base: none. JSON in/out.
- `GET /health` -> `{"status":"ok"}`
- `POST /suggestion` `{suggestion_id, task_id, task_item_id, template_schema, raw_data, context}` -> `{"suggestion_id","status":"generating"}` (async: store row pending, generate in background thread, write result)
- `GET /suggestion/{suggestion_id}` -> `{"suggestion_id","status","suggestion","model","error","created_at","completed_at"}`
- `GET /audit/{audit_id}` -> `{"audit_id","status","score","issues","reasoning","suggestion","evidence","model","error"}`
- agent-web reads/writes DB `labelhub_agent` tables `ai_suggestions`, `ai_audit_reports`.

## RabbitMQ audit message (backend publishes, agent-worker consumes)
Exchange: `labelhub` (direct), routing key: `ai_audit`, queue: `ai_audit` bound to it.
Message body (JSON):
```json
{
  "audit_id": "<uuid>",
  "task_id": 1,
  "task_item_id": 10,
  "template_schema": { ... materials ... },
  "annotation_result": { ... labeler result ... },
  "raw_data": { ... original sample ... },
  "context": { "task_name": "...", "dataset_name": "..." }
}
```
agent-worker on consume:
1. insert `ai_audit_reports` row status=processing.
2. run field rule validation against `template_schema` + `annotation_result` (required, type, options).
3. if configured LLM available, call OpenAI-compatible API to produce score/issues/reasoning/suggestion.
4. if no LLM key configured, fall back to rule-based scoring (full marks if all rules pass; partial deductions per violated rule) so the loop works without keys.
5. update row status=done, score, issues, reasoning, suggestion, evidence, model, completed_at.

## MinIO buckets
`annotation`, `dataset`, `export`, `template` — all with anonymous read (`public` download policy) so frontend can fetch files directly via `LABELHUB_MINIO_PUBLIC_URL`.

## AI degradation policy
- Both agent-web and agent-worker MUST function without an LLM API key.
- Without a key: produce rule-based / heuristic suggestions and audit reports (deterministic, still useful for the closed loop).
- With a key (`AI_AUDIT_API_KEY` + `AI_AUDIT_BASE_URL` + `AI_AUDIT_MODEL`): call OpenAI-compatible LLM via langchain `ChatOpenAI`.
