# AI Customer Support Platform — Backend

Production-ready, multi-tenant SaaS backend for AI-powered customer-support
chatbots. Companies manage an FAQ/knowledge base, an AI bot answers visitors
using semantic (vector) retrieval, and low-confidence chats escalate to human
agents over realtime WebSockets.

Built with **Django 5 · DRF · PostgreSQL + pgvector · JWT · Channels · Celery +
Redis** and a pluggable **OpenAI / Gemini** abstraction layer.

---

## Architecture

Clean, layered architecture — views stay thin, business logic lives in services:

```
HTTP / WebSocket
      │
  Views / Consumers      ← serialization, auth, permissions
      │
  Service layer          ← business logic (ChatService, EmbeddingService, …)
      │
  Models / Managers      ← persistence, soft-delete, tenant scoping
      │
  PostgreSQL + pgvector  ·  Redis (Channels + Celery)  ·  OpenAI / Gemini
```

### Django apps

| App             | Responsibility |
|-----------------|----------------|
| `core`          | Shared base models, RBAC permissions, tenant mixins, exceptions, pagination, **AI provider abstraction**, WebSocket JWT auth |
| `accounts`      | Custom email `User`, roles (SUPER_ADMIN / COMPANY_ADMIN / MANAGER / AGENT), JWT auth, team management |
| `companies`     | `Company` (tenant), `UserCompany` membership, onboarding, isolation |
| `knowledge_base`| `KnowledgeBase`, `QuestionAnswer`, `QuestionEmbedding` (pgvector), bulk CSV/Excel upload, soft delete, semantic search |
| `chatbot`       | `Chatbot` (widget token), `Visitor` |
| `conversations` | `Conversation`, `Message`, **`ChatService.handle_user_message()`** (RAG flow), escalation, Channels consumers |
| `agents`        | `AgentAvailability`, `ConversationAssignment`, assign / transfer / close |
| `analytics`     | `ConversationMetrics`, `UnansweredQuestion`, convert-to-FAQ |
| `integrations`  | Widget configuration + **public token-based widget APIs** |

### Multi-tenancy & isolation

- Every tenant-owned row carries a `company` FK (directly or one relation away).
- `CompanyScopedQuerysetMixin` filters every list/detail query to the caller's
  company; `IsCompanyMember` enforces object-level isolation. SUPER_ADMIN bypasses.
- Service-layer guards (`_assert_same_company`, `TenantIsolationError`) prevent
  cross-tenant writes even outside the HTTP layer.

### The AI chat flow (`ChatService.handle_user_message`)

1. Save the visitor message.
2. Embed the question (provider abstraction).
3. pgvector cosine search → top-K similar FAQ entries (tenant-scoped).
4. Confidence = best similarity score.
5. Build a grounded prompt from retrieved Q/A pairs.
6. Call the LLM (OpenAI / Gemini).
7. Save the bot reply with provenance metadata.
8. Broadcast to the conversation's WebSocket room.
9. If confidence < `CHAT_CONFIDENCE_THRESHOLD`: record the unanswered question,
   set status `WAITING_AGENT`, and notify available agents.

---

## Requirements

- Python 3.12+ (works on 3.11)
- PostgreSQL 14+ **with the `pgvector` extension installed on the server**
- Redis 6+

> **Important:** `pip install pgvector` only installs the Python client. The
> PostgreSQL server itself must have the `vector` extension available. Easiest
> path (esp. on Windows) is the official Docker image:
>
> ```bash
> docker run -d --name pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ai_support \
>   -p 5432:5432 pgvector/pgvector:pg16
> ```
>
> Otherwise install pgvector for your local Postgres (see
> https://github.com/pgvector/pgvector#installation).

---

## Setup

```bash
cd SERVER
python -m venv venv && source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

cp .env.example .env            # then edit DB creds + API keys

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver      # ASGI via daphne (HTTP + WebSocket)
```

Background workers (separate terminals):

```bash
celery -A backend worker -l info
celery -A backend beat -l info        # optional: nightly analytics rollups
```

---

## API

All REST endpoints are under `/api/v1/`. Interactive docs:

- Swagger UI: `/api/docs/`
- ReDoc:      `/api/redoc/`
- OpenAPI:    `/api/schema/`

### Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/companies/companies/onboard/` | Public: create company + first admin |
| POST | `/api/v1/accounts/auth/login/` | JWT login → `{access, refresh, user}` |
| POST | `/api/v1/accounts/auth/token/refresh/` | Refresh access token |
| CRUD | `/api/v1/kb/knowledge-bases/`, `/api/v1/kb/qa/` | Manage FAQ data |
| POST | `/api/v1/kb/qa/bulk_upload/` | CSV/Excel import (`question`, `answer` cols) |
| POST | `/api/v1/kb/knowledge-bases/search/` | Semantic search |
| CRUD | `/api/v1/chatbot/chatbots/` | Manage bots; `…/rotate_token/` |
| GET  | `/api/v1/conversations/conversations/` | Agent inbox |
| POST | `/api/v1/conversations/conversations/escalate/` | Escalate to human |
| POST | `/api/v1/agents/assignments/assign/` · `…/transfer/` · `…/close/` | Chat routing |
| GET  | `/api/v1/analytics/metrics/dashboard/` | Live KPIs |
| POST | `/api/v1/analytics/unanswered/{uuid}/convert_to_faq/` | Curate FAQ |
| GET/POST | `/api/v1/integrations/widget/config/`, `/widget/start/`, `/widget/chat/` | **Public, widget-token auth** |

### Public widget auth

Send the chatbot's `widget_token`:

```
Authorization: Widget <widget_token>
```

### WebSockets

- Visitor: `ws://host/ws/visitor/<conversation_uuid>/?token=<widget_token>`
- Agent:   `ws://host/ws/agent/<conversation_uuid>/?token=<jwt_access>`

Supports messages, typing indicators (`{"action":"typing"}`) and read receipts
(`{"action":"read","message_id":…}`).

---

## Switching AI providers

Set in `.env`:

```
EMBEDDING_PROVIDER=gemini     # or openai
LLM_PROVIDER=gemini
EMBEDDING_DIM=768             # must match the model: openai=1536, gemini=768
```

Add a new provider by subclassing `BaseEmbeddingProvider` / `BaseLLMProvider`
in `core/ai/` and registering it in `core/ai/factory.py` — nothing else changes.

> Changing `EMBEDDING_DIM` changes the pgvector column width — regenerate the
> migration and re-embed existing questions.

---

## Tests

The suite mocks the AI providers (no API keys needed) but **requires Postgres
with pgvector** because models use real `VectorField` / HNSW indexes:

```bash
python manage.py test
```

---

## Production checklist

- Set `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, real `ALLOWED_HOSTS`.
- Serve over HTTPS behind a reverse proxy; run ASGI via `daphne`/`uvicorn`.
- Use managed Postgres (with pgvector) and Redis.
- Run Celery workers + beat as supervised services.
- Configure object storage for `MEDIA` (company logos).
