# Universal AI Chatbot — Workflow & Architecture

**Audience: an AI agent making changes to this repo.** Read this file first.
It describes (A) what is actually built today, verified against the code, and
(B) the target design that makes the product *universal* — usable by a real
estate company, an e-commerce company, or a clinic without writing Python.

Companion document: [`universal-orchestration-architecture.html`](./universal-orchestration-architecture.html)
— the long-form architecture proposal with diagrams. **This file supersedes it
where they disagree**, because several findings in that document (F1, F2, F3,
F7, F8) have since been fixed in code.

---

## 0. TL;DR of the change being made

| | Today (built) | Target (universal) |
|---|---|---|
| Tenant knowledge | Q&A pairs only | Knowledge chunks **+ structured records (JSON) + actions** |
| Who decides what to do | The WebSocket consumer, before the LLM runs | **The LLM**, choosing from a per-tenant tool registry |
| Shape of a turn | embed → search → prompt → answer | **loop**: model → tool call → validated execution → model → … |
| Adding a new industry | Write new FAQ rows; anything non-FAQ is impossible | **Rows in a registry**. No Python. |
| Onboarding a company | — | Pick a **preset** (Q&A / catalogue), upload policy docs, done — see B0 |

The single acceptance test for the whole redesign:
**onboarding a vertical nobody anticipated must touch no Python.**

---

# PART A — The system as it exists today

## A1. Repo layout

```
PERSONALISED_AI_CHATBOT/
├── TEMPSERVER/          Django 5.2 + DRF + Channels (ASGI/daphne), PostgreSQL + pgvector
│   ├── config/          settings, urls, asgi, tenancy.py
│   ├── company/         Company model (the tenant)
│   ├── users/           User, AuthToken, bearer auth, permissions
│   ├── questions/       Question, UnansweredMessage, ChatConsumer (the bot socket)
│   ├── vector_question/ VectorJob + services.py (embeddings, Gemini, retrieval text)
│   ├── chat/            ChatSession, ChatMessage, AgentConsumer (human agent console)
│   └── tests/           test_auth_and_tenancy.py, test_retrieval.py
└── TEMPFRONTEND/        React 19 + Vite + Redux Toolkit + Tailwind
    └── src/{pages,components,hooks,services,redux,routes,utils}
```

Stack facts that constrain any change:
- Embeddings: `sentence-transformers` **all-MiniLM-L6-v2**, 384-dim, normalized,
  loaded in-process and cached on the class.
- Vector store: **pgvector column on `questions.embedding`** with an HNSW cosine
  index. There is no external vector DB. `vector_question.MockVectorStore` is a
  vestigial stub — the real search runs in Postgres.
- LLM: **Gemini** via `google-genai`, model from `GEMINI_MODEL`
  (default `gemini-2.5-flash`), forced to `response_mime_type: application/json`.
- Realtime: Django Channels. `REDIS_URL` selects the Redis channel layer;
  without it the in-memory layer is used and a `RuntimeWarning` is raised.
- Auth: **custom** `users.User` (not `django.contrib.auth`) + `AuthToken`
  (SHA-256 of the raw token stored, 14-day TTL) + `BearerTokenAuthentication`.
  DRF is **closed by default** (`IsAuthenticatedUser` is the default permission).

## A2. Data model (current)

| Table | Model | Notes |
|---|---|---|
| `company` | `company.Company` | The tenant. name, email, mobile, address. |
| `users` | `users.User` | FK company. `type` ∈ Admin/Agent/Manager. PBKDF2 password. |
| `auth_tokens` | `users.AuthToken` | `key_hash` is the lookup column; raw token never stored. |
| `questions` | `questions.Question` | FK company. `question`, `answer`, `embedding vector(384)`, `is_vectorized`, `is_archived`. HNSW index `questions_embedding_hnsw`. |
| `unanswered_messages` | `questions.UnansweredMessage` | FK company. Raw customer message the bot could not answer. |
| `vector_jobs` | `vector_question.VectorJob` | Per-company vectorization run: counters, status, timing. |
| `chat_session` | `chat.ChatSession` | FK company, optional FK agent, `status`, `agent_needed`, `public_token`. |
| `chat_message` | `chat.ChatMessage` | FK company+session, `message`, `sent_by_us`, `is_ai`, `message_type`, `attachments`. |

Two invariants worth knowing before editing:
- `Question.save()` **clears the embedding and unsets `is_vectorized`** whenever
  `question` or `answer` text changed. Editing unrelated fields does not.
- `ChatSession.public_token` (`secrets.token_urlsafe(24)`) is the *only* proof an
  anonymous browser owns a conversation. `/api/chat/history/` requires it.

## A3. Tenancy — the one rule

`config/tenancy.py`. **The company a request may touch is derived from the
authenticated token, never from the request.**

- `require_company(request)` → the caller's `company_id`.
- `assert_own_company(request, id)` → guard for company-id-in-path endpoints.
- `CompanyScopedQuerysetMixin` → filters reads to the caller's company **and**
  forces `company` on writes, so a client cannot create or move a row into
  another tenant via the request body.
- `?company_id=` is still accepted on list endpoints but can only *narrow*
  within the caller's own company; another tenant's id returns an empty page.

**Never introduce a code path that reads a tenant id from user input.**

## A4. The chat pipeline as built

`questions/consumers.py :: ChatConsumer` (`ws/chat/`). Per inbound frame:

1. Parse `{message, company_id, session_id?, customer_user_*}`. Reject empty
   message or missing `company_id`.
2. `_get_or_create_session` → reuse `session_id` **scoped to `company_id`**, else create.
3. Join the session channel group so agent replies reach this socket.
4. Store the customer message (`sent_by_us=False, is_ai=False`).
5. **If a human agent already owns the session** (`_live_agent_id`: agent set and
   status ∈ open/in_progress) → forward to the agent group, reply `type:"delivered"`,
   **the AI is skipped entirely**.
6. `_top_matches` → embed the query with `build_retrieval_text` (bare question
   text), then `CosineDistance` ordered against the HNSW index, `LIMIT 3`.
   Returns `(similarity = 1 - distance, question, answer)`.
7. Gate: no matches, or `best_score < CHAT_CONFIDENCE_THRESHOLD` (default **0.40**)
   → store `UnansweredMessage`, `_handoff_to_agent`, reply `AGENT_HANDOFF_MESSAGE`.
8. Otherwise `generate_answer(message, faq_pairs)` → Gemini returns
   `{"message": ..., "is_answer_found": bool}`.
9. If `is_answer_found` is false → park unanswered + hand off anyway. **The LLM's
   self-assessment is a second, independent gate** on top of the score.
10. Store the AI message, reply `type:"answer"` with `answer`, `score`,
    `is_answer_found`, `agent_needed`, `sources[]`, `session_id`, `session_token`.

### Why the threshold is 0.40 (do not "fix" it back to 0.90)
Measured on MiniLM with bare-question index text, pinned by
`tests/test_retrieval.py`: exact restatement ≈ 1.00, true paraphrase 0.44–0.80,
unrelated 0.08–0.35. The usable separation is the narrow 0.35–0.44 band. The
threshold is a **cheap pre-filter**, not the decision — `is_answer_found` is.

### Index/query symmetry (do not "improve" `build_retrieval_text`)
Rows are embedded as the **bare question**, because queries are bare customer
questions. Embedding `"Question: …\nAnswer: …"` compares two different kinds of
object and drags every score down. The answer still reaches the model as
context; it is just not part of what the query is compared against.

## A5. Human agent handoff

`chat/services.py`:
- `pick_free_agent(company_id)` — an active, non-archived `type=Agent` user whose
  id is not in the `agent` column of any open/in_progress session.
- `flag_agent_needed(session)` — sets `agent_needed`, attaches a free agent
  (idempotent). Returns `None` when everyone is busy; the session stays flagged.
- Channel groups: `agent_{id}` (an agent's inbox) and `chat_session_{id}`.
- Events: `chat.assigned`, `chat.message`, `chat.closed`.

`chat/consumers.py :: AgentConsumer` (`ws/agent/?token=<bearer>`) — identity comes
from the token, never a query-string id. Actions: `refresh`, `history`, `close`,
`message`.

## A6. HTTP API surface

All under `/api/`.

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /auth/register/` | open | Creates company + first Admin atomically |
| `POST /auth/login/` | open | Issues a bearer token |
| `POST /auth/logout/`, `GET /auth/me/` | token | |
| `GET/PATCH /companies/` | token / Admin for write | Single row by construction |
| `/users/`, `/managed-users/` | Admin+Manager | |
| `/questions/` (CRUD, `?search=`) | Admin+Manager | DELETE is a **soft delete** that also clears the embedding |
| `/unanswered-messages/` (list, delete) | Admin+Manager | |
| `POST /unanswered-messages/{id}/resolve/` | Admin+Manager | Body `{answer}` → creates a Question, embeds it immediately, deletes the inbox row |
| `POST /vectorize/{company_id}/` | Admin+Manager | Runs `vectorize_company` synchronously |
| `GET /vector-jobs/` | token | Job history |
| `GET /chat/widget/`, `GET /chat/history/` | **open** | Widget config; history requires the session `token` |
| `POST /chat/sessions/assign/` | | Manual agent assignment |
| `/agent/chats/{,history,send,close}/` | Agent | REST twin of the agent socket |

WebSockets: `ws/chat/` (customer) and `ws/agent/` (agent console).

## A7. Frontend map

| Route | Page | Who |
|---|---|---|
| `/chat/:companyId` | `public-chat/PublicChatPage` + `PreChatForm` | anonymous visitor |
| `/register`, `/login` | `auth/*` | public |
| `/manage_questions` | `knowledge-base/KnowledgeBasePage` | Admin/Manager |
| `/unanswered` | `unanswered/UnansweredPage` + `AnswerQuestionModal` | Admin/Manager |
| `/users` | `users/UsersPage` | Admin/Manager |
| `/agent` | `agents/AgentConsolePage` | Agent |

Sockets: `hooks/useCustomerChatSocket.js`, `hooks/useAgentSocket.js`, both on
`hooks/useWebSocket.js`. Redux slices mirror the pages. `services/axiosInstance.js`
attaches the bearer token. `utils/constants.js` derives `WS_BASE_URL` from
`API_BASE_URL` by swapping the scheme and dropping `/api`.

## A8. Configuration

`TEMPSERVER/.env` (see `.env.example`): `DB_*`, `REDIS_URL`, `GEMINI_API_KEY`,
`GEMINI_MODEL`, `CHAT_CONFIDENCE_THRESHOLD`.
`TEMPFRONTEND/.env`: `VITE_API_BASE_URL`, optional `VITE_WS_BASE_URL`.

## A9. What is genuinely limiting about A4 (the reason for Part B)

| # | Limitation | Where |
|---|---|---|
| L1 | **Routing is hardcoded in the transport layer.** The consumer decides "search FAQs" before any model call. A greeting triggers a vector scan and can escalate. There is nowhere to add a second capability. | `questions/consumers.py` |
| L2 | **No conversation history reaches the model.** `generate_answer(message, faq_pairs)` sees one turn, so "and under 80 lakh?" is structurally unanswerable. | `vector_question/services.py` |
| L3 | **Q&A is the only knowledge shape.** Inventory, catalogues, price lists, order status — anything with *rows and fields* — cannot be represented as FAQ pairs. This is the core universality blocker. | `questions/models.py` |
| L4 | **No chatbot entity.** The tenant key is `company_id` and every knob (threshold, persona, model) is a global constant. Nowhere to hang per-bot config. | schema |
| L5 | **The bot can only answer, never act.** No way to create a lead, book a slot, or check an order. | — |
| L6 | Vectorization runs **synchronously in the request**, and embedding runs in the async consumer's thread. | `vector_question/views.py`, `consumers.py` |

L1–L5 are what Part B fixes. **Note that F1/F2/F3/F7/F8 from the HTML doc are
already fixed** — do not re-open them.

---

# PART B — Target architecture: registry-driven tool calling

## B0. Onboarding: presets, not bot types

This is the question the product asks a new company on day one:

> **"What kind of chatbot do you need?"**
> **(1)** Customers ask questions, you give answers. *(support, policies, general info)*
> **(2)** Customers search your catalogue by attributes. *(properties, products, services)*
> …plus, for both: **upload your policy documents.**

That question is exactly right as **onboarding UX**. But it must not become two
code paths.

> ### The correction that matters
> A "mode" is a **preset that provisions registry rows**, not a branch in the
> orchestrator. Both modes run the *same* loop, the *same* validator, the *same*
> executors. They differ only in which `tools` rows exist for that chatbot.
>
> If you build "simple mode" and "category mode" as two pipelines, you have
> rebuilt the exact problem in A9/L1 — routing hardcoded above the model — and
> the third company that wants *both* (an e-commerce store with a product
> catalogue **and** a return policy) breaks it. Which is most companies.

### What each preset actually provisions

| | **Preset 1 — Q&A** | **Preset 2 — Catalogue** |
|---|---|---|
| Company's mental model | "answer my customers' questions" | "help customers find the right item" |
| `tools` rows created | `search_knowledge`, `request_human_agent` | `search_knowledge`, `search_<thing>`, `request_human_agent` |
| Knowledge sources | FAQ pairs + uploaded documents | FAQ pairs + uploaded documents |
| Data sources | none | one `data_sources` row + its `data_source_fields` |
| Onboarding screens shown | Knowledge, Test | Knowledge, Connect data, Schema review, Field permissions, Test |
| Code that differs | **none** | **none** |

Preset 2 is a strict superset of preset 1. Upgrading a company from 1 to 2 is
inserting rows — no migration, no redeploy, no downtime. That is the whole test
of whether this design is real.

### Worked contrast

**Company A — a SaaS support bot (preset 1).** Customer: *"How do I reset my
password?"* The model has two tools. It calls `search_knowledge("reset
password")`, gets a chunk, answers. Behaviourally near-identical to today's
pipeline — but the *model* chose to search, so a greeting no longer triggers a
vector scan, and a follow-up ("and for a team account?") works because history
is in context.

**Company B — a real estate bot (preset 2).** Customer: *"I want a 2BHK in New
Ranip, not on the top floor."* The model sees a third tool,
`search_available_listings`, whose declaration was generated from that tenant's
`data_source_fields`:

```jsonc
{
  "name": "search_available_listings",
  "parameters": { "type": "object", "properties": {
    "locality":     { "type": "string",  "enum": ["New Ranip","Chandkheda","SG Highway", "…"] },
    "bedrooms":     { "type": "integer", "minimum": 1, "maximum": 10 },
    "is_top_floor": { "type": "boolean" },
    "max_price":    { "type": "number" },
    "limit":        { "type": "integer", "maximum": 20, "default": 10 }
  }}
}
```

It calls `search_available_listings({locality:"New Ranip", bedrooms:2, is_top_floor:false})`.
The compiler turns that into the IR of B3, the validator checks every field
against the registry, the `records` adapter queries `data_records.payload`, and
the result comes back shaped as in B3 (`matched`, `returned`, `truncated`,
`relaxable_filters`).

Then the same customer asks *"what's your brokerage fee?"* — and the **same
model in the same conversation** calls `search_knowledge` instead. That is the
thing the current architecture cannot do at all, and it is why the mode must not
be a branch: one customer crosses between modes inside one conversation.

### Where the uploaded policy files go

"Let the company upload their privacy policy, return policy, company info" is
already the design — it is a `knowledge_sources` row with `kind='document'`
(a file) or `kind='url'` / `kind='text'`. The ingestion job:

1. Extract text (PDF/DOCX/TXT/MD/HTML) → `knowledge_documents.raw_text`, with a
   `checksum` so re-uploading an unchanged file is a no-op.
2. Chunk it — target ~300–500 tokens with ~15% overlap, split on headings and
   paragraph boundaries first, never mid-sentence.
3. For a document chunk, `embed_text == content` (the prose is both what you
   search and what you return). For a **FAQ** row, `embed_text` is the question
   and `content` is the answer. Same table, two population rules — that is why
   the two columns exist (B2.2).
4. Store `metadata` per chunk: `{document_title, section_heading, page}`. The
   model cites it, and the dashboard shows the company *which* document answered.

**Why documents are strictly better than forcing policies into Q&A pairs:** a
return policy is one document a company already has. Today they must hand-write
"What is your return policy?" / "Can I return after 30 days?" / "Do I pay return
shipping?" as separate rows and will always miss cases. One upload, chunked,
covers all of them — and the hybrid retrieval in B4 is what makes it work, since
policy text is full of exact terms (plan names, day counts, clause numbers)
where full-text recall beats vectors.

### The onboarding flow, end to end

```
1. Register company + admin                          (exists today)
2. "What kind of chatbot?"  → creates the `chatbots` row + preset `tools` rows
3. Upload documents          → knowledge_sources(kind='document') → chunk + embed
4. Add FAQ pairs             → knowledge_sources(kind='faq')      → existing editor
5. [preset 2 only] Upload catalogue CSV/JSON → data_sources + inferred fields
6. [preset 2 only] Review inferred field types, set exposed/filterable/sortable
7. Test console — watch every tool call and fix the descriptions
8. Share the link  /chat/<slug>
```

Steps 5 and 6 are the *only* difference between the two companies, and neither
touches Python.

## B1. The core idea

Stop deciding *for* the model. Give it a **per-tenant tool registry** and let it
choose, in a loop, constrained by a registry the backend owns and validates.

```
customer msg ─▶ orchestrator ─▶ model ──(tool call)──▶ validator ─▶ executor ─┐
                     ▲                                                        │
                     └──────────────── tool result (role='tool') ◀────────────┘
                                       ↓ no tool call
                                   stream reply
```

Everything else — the schema, the compiled declarations, the ten gates — exists
to make the **return arrow** safe. What does *not* change: same Postgres, same
embedding model, same WebSocket transport, same agent-handoff machinery.

### The four tool types

| `tool_type` | `configuration` holds | Schema derived from | Executor |
|---|---|---|---|
| `KNOWLEDGE_SEARCH` | `{source_ids: [...]}` or empty for all | fixed: `query`, optional `top_k` | hybrid retriever (pgvector + tsvector) |
| `STRUCTURED_SEARCH` | `{data_source_id: 123}` | generated from `data_source_fields` | query compiler → validator → adapter |
| `API_ACTION` | `{action_id: 45}` | generated from `action_parameters` | schema validator → egress-guarded HTTP |
| `HANDOFF` | `{queue, reason_required}` | fixed: `reason`, optional `summary` | existing `flag_agent_needed` |

**This is the answer to the user's "JSON kind of thing" question.** A real
estate tenant uploads a CSV/JSON of listings; an e-commerce tenant uploads
products. Both become `data_records.payload` JSONB rows under a `data_sources`
row with a `data_source_fields` registry. The *only* difference between the two
tenants is rows in those tables.

## B2. Target data model

Additive. `questions` **survives** as the authoring surface for `kind='faq'`
knowledge sources.

### B2.1 Config
| Table | Key columns | |
|---|---|---|
| `company` | id, name, email, … | exists |
| `users` | id, company_id, type, … | exists |
| `chatbots` | id, company_id, **slug**, name, persona_prompt, model, temperature, locale, is_active, **policy jsonb** | new |

`chatbots.policy` holds what are global constants today: retrieval floor, accept
threshold, max tool calls per turn, handoff rules, row caps. `slug` replaces the
raw company id in the public URL (`/chat/acme-support`, not `/chat/7`) so link
recipients cannot enumerate tenants by incrementing an integer.

### B2.2 Knowledge
| Table | Key columns |
|---|---|
| `knowledge_sources` | id, chatbot_id, name, kind (`faq`\|`document`\|`url`\|`text`), config jsonb, status, last_indexed_at |
| `knowledge_documents` | id, source_id, external_ref, title, raw_text, checksum, updated_at |
| `knowledge_chunks` | id, chatbot_id, source_id, document_id, ordinal, **content**, **embed_text**, **embedding vector(384)**, content_tsv, **embedding_model**, token_count, metadata jsonb |

Two columns carry design weight. `embed_text` is separate from `content`: for a
FAQ row the embedding covers the *question* (plus optional author paraphrases)
while `content` returned to the model is the *answer* — this is A4's
index/query symmetry, generalized. `embedding_model` is stored **per chunk** so
a model upgrade can be indexed alongside the old one and cut over per chatbot
instead of being a platform-wide re-index outage.

```sql
CREATE INDEX kc_embedding_hnsw ON knowledge_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX kc_tsv    ON knowledge_chunks USING gin (content_tsv);
CREATE INDEX kc_tenant ON knowledge_chunks (chatbot_id, source_id);
```

### B2.3 Structured data — the universality layer
| Table | Key columns |
|---|---|
| `data_sources` | id, chatbot_id, name (slug), display_name, description, adapter (`records`\|`rest_api`\|`sql_readonly`), config jsonb, row_count, sync_status, last_synced_at, is_published |
| `data_source_fields` | id, data_source_id, name, label, data_type, path, description, unit, **is_exposed**, is_filterable, is_sortable, is_searchable, is_returned, **allowed_operators text[]**, enum_values jsonb, cardinality, display_order |
| `data_records` | id, data_source_id, external_id, **payload jsonb**, search_tsv, updated_at, deleted_at · unique (data_source_id, external_id) |
| `data_source_syncs` | id, data_source_id, mode, rows_in, rows_upserted, rows_rejected, errors jsonb, started_at, finished_at |

**`data_source_fields` is the security boundary, not documentation.** It is the
only list of names the validator accepts. A field with `is_exposed = false` is
invisible in both directions — cannot be filtered on, never returned. That is
where `internal_margin` or `supplier_cost` stays hidden.

#### Structure is rows, data is JSON

The single most-misunderstood part of this schema. Two tables that look similar
do completely different jobs:

```
        ┌──────────┬──────────┬───────┬─────────────┐
HEADER  │ locality │ bedrooms │ price │ owner_phone │  ← data_source_fields
        ├──────────┼──────────┼───────┼─────────────┤
ROW 1   │ New Ranip│    2     │6500000│  98250...   │  ← data_records
ROW 2   │Chandkheda│    3     │9200000│  98251...   │  ← data_records
        └──────────┴──────────┴───────┴─────────────┘
```

- **`data_source_fields` is the header row.** Written once at setup, ~10–30 rows
  per source, edited in the field-permissions screen.
- **`data_records` is the data.** Thousands of rows, one JSONB `payload` each,
  written by the importer and never hand-edited.

**Why the field definitions must not also be JSON.** The payload already
contains the key names, so the temptation is to skip `data_source_fields`
entirely. It does not work, because the payload carries names but no *rules*:

| Question at query time | From `payload` | From `data_source_fields` |
|---|---|---|
| Is `bedrooms` a number or a string? | `2` could be either | declared type |
| May the model filter on `owner_phone`? | unknowable | `is_exposed = false` |
| May `owner_phone` be returned? | unknowable | `is_returned = false` |
| What localities may be offered as an enum? | scan every row | `enum_values` |
| What does "bedrooms" mean to a customer? | unknowable | `description` |

And the performance argument is decisive: G4/G5/G6 run on **every tool call**.
Against `data_source_fields` that is one indexed lookup over a handful of rows.
Against a JSON blob of field definitions it is a parse; against the payloads
themselves it is a table scan of the whole dataset to answer "is this field
allowed" — before you have even run the query.

Note that `payload` stores **every** column including hidden ones. Hiding is
enforced at the registry, not by dropping data at import, so a company can
expose a field later without re-uploading.

### B2.4 Tools, actions, credentials
| Table | Key columns |
|---|---|
| `tools` | id, chatbot_id, name, description, tool_type, configuration jsonb, **input_schema jsonb (compiled)**, schema_version, is_active, requires_confirmation, rate_limit jsonb · unique (chatbot_id, name) |
| `actions` | id, chatbot_id, name, description, execution (`http`\|`internal`), http jsonb {method,url,headers,body_template,timeout_ms}, credential_id, confirmation_required, idempotency_template |
| `action_parameters` | id, action_id, name, data_type, required, description, enum_values, default_value, validation jsonb |
| `credentials` | id, company_id, name, auth_type, **secret_ciphertext**, key_version, rotated_at |

**Parameters as rows *and* as schema.** `action_parameters` exists because a
no-code UI edits parameters field by field. But `tools.input_schema` is the
*compiled artifact* — the JSON Schema actually sent to the model, regenerated
whenever source rows change. `STRUCTURED_SEARCH` and `KNOWLEDGE_SEARCH` have no
parameter rows at all; their schema is derived from `data_source_fields`.
One source of truth per tool type, one cached compilation.

### B2.5 Conversation and audit
| Table | Change |
|---|---|
| `chat_session` | add chatbot_id, visitor_id, channel, **working_set jsonb**, summary, summary_upto_message_id |
| `chat_message` | add **role** (`user`\|`assistant`\|`tool`\|`system`), tool_call_id, tool_name, tool_args jsonb, tool_result jsonb, tool_result_summary, tokens, latency_ms |
| `tool_executions` | id, conversation_id, message_id, tool_id, raw_arguments, validated_arguments, status, error_code, rows_returned, duration_ms, created_at (new) |

Extend `chat_message` rather than adding a parallel table: the transcript an
agent reads in the console and the transcript replayed to the model **must be
the same rows**, or the agent will not see what the bot promised the customer.

## B3. What the model actually sees

```jsonc
{
  "name": "search_available_listings",
  "description": "Search available property listings by location, budget, size and type. Use when the customer describes what they are looking for. Do not use for policies or company info.",
  "parameters": {
    "type": "object",
    "properties": {
      "city":          { "type": "string",  "enum": ["Ahmedabad","Surat","Vadodara"] },
      "bedrooms":      { "type": "integer", "minimum": 1, "maximum": 10 },
      "max_price":     { "type": "number",  "description": "Upper budget in INR" },
      "min_price":     { "type": "number" },
      "property_type": { "type": "string",  "enum": ["apartment","villa","plot"] },
      "sort_by":       { "type": "string",  "enum": ["price_asc","price_desc","newest"] },
      "limit":         { "type": "integer", "minimum": 1, "maximum": 20, "default": 10 }
    }
  }
}
```

No `data_source_id`, no operators, no field paths, no table names. The model sees
a *business capability*; the backend keeps the mapping.

**Flat parameters out, filter IR in.** Do **not** expose a generic
`filters: [{field, operator, value}]` array to the model — JSON Schema cannot
constrain any of the three, so `{"field":"cost","operator":"under","value":"80 lakh"}`
is schema-valid and wrong three ways. A flat surface makes enums, ranges and
types enforceable *in the declaration*. Sources that genuinely need OR-groups
opt into an `advanced_filters` parameter carrying raw IR, validated by the same
code path.

### Field → parameter generation rules
| Field type | Condition | Generated parameter(s) | Compiles to |
|---|---|---|---|
| string | cardinality ≤ 50 | `name` (enum) | `equals` |
| string | cardinality > 50 | `name` (free text) | `equals` or `ilike`, per field config |
| number/integer | filterable | `min_name`, `max_name` | `gte`, `lte` |
| date/datetime | filterable | `name_after`, `name_before` | `gte`, `lte` |
| boolean | filterable | `name` | `equals` |
| string_array | filterable | `name` (array of enum) | `contains_any` |
| any | sortable | `sort_by` (enum of `name_asc`/`name_desc`) | sort clause |

### The internal IR — never generated by the model, always logged
```json
{
  "data_source": "properties",
  "filters": [
    { "field": "city",     "operator": "equals", "value": "Ahmedabad" },
    { "field": "bedrooms", "operator": "equals", "value": 3 },
    { "field": "price",    "operator": "lte",    "value": 8000000 }
  ],
  "sort":  [{ "field": "price", "direction": "asc" }],
  "limit": 10,
  "offset": 0
}
```

### Result shaping — this is context budget being spent
```json
{
  "matched": 47,
  "returned": 10,
  "rows": [{ "title": "…", "city": "Ahmedabad", "price": 7500000, "bedrooms": 3, "ref": "PROP-1182" }],
  "truncated": true,
  "relaxable_filters": ["max_price"]
}
```
`matched` lets the model say "47 match, here are 10" instead of implying it saw
everything. `truncated` prompts narrowing instead of inventing a total. On a
zero-result query, `relaxable_filters` — computed by re-running with each filter
dropped in turn — turns a dead end into *"nothing at 80 lakh; the cheapest 3 BHK
on SG Highway is 92."* Generic logic, no industry knowledge in it.

### Adapters
- **`records`** (default). Rows in `data_records.payload` JSONB. Filters compile
  to ORM `KeyTextTransform` lookups with an explicit cast per declared type. GIN
  `jsonb_path_ops` for equality; B-tree expression indexes on numeric/date fields
  created once when a source is **published**, not per query.
- **`rest_api`**. IR maps to query params via a per-source template. Same
  validation, different sink. Subject to the egress rules in B6.
- **`sql_readonly`**. Read-only connection to a tenant DB with allowlisted tables
  and columns. Highest value, highest risk — **defer past v1**.

> **JSONB vs. real columns.** JSONB means zero DDL per tenant and one code path,
> at the cost of casts on every filter. Physical per-source tables are faster but
> need runtime DDL — an operational and security liability at tenant scale.
> **Start with JSONB.** It covers the tens-of-thousands-of-rows range that fits
> most tenants, and the adapter seam lets one large tenant move to a materialized
> table later without touching the compiler, the validator, or the model.

## B4. Knowledge search (target)

1. **Embed the query** with the chunk's own `embedding_model`, normalized. Cache
   identical queries per chatbot for the session.
2. **Two recalls in parallel**: pgvector HNSW cosine (top 30) and Postgres
   full-text over `content_tsv` (top 30). Vector alone is weak exactly where
   business content is strong — SKUs, policy names, plan tiers, error codes.
3. **Fuse with Reciprocal Rank Fusion**, `score = Σ 1/(60 + rank)`. No score
   normalization needed between two incomparable scales.
4. **Apply the relevance gate**, then cap to `top_k` and a hard token ceiling (~1200).

### The gate — three per-chatbot signals replacing one global constant
| Signal | Purpose | Starting value |
|---|---|---|
| `retrieval_floor` | Discard obvious noise before fusion | cosine ≥ 0.32 |
| `accept_threshold` | Below this, return **zero** chunks rather than weak ones | fused rank-1 in top decile |
| `margin_rule` | If rank 1 and rank 5 are indistinguishable, the query is off-domain | Δ ≥ 15% |

**These are starting points, not answers.** Any threshold not measured against
labelled data is a guess — which is how `0.90` got there originally. Build a
fixture of ~50 questions per pilot tenant tagged `answerable` / `not`, tune per
chatbot against precision on the `not` set, store the result in `chatbots.policy`.
**Ship the measurement harness in the same phase as the retriever.**

When nothing clears the gate, return `{"chunks": [], "reason": "no_relevant_content"}`.
This is the single most important behavioural difference from today: an *empty*
result is a useful signal the model can act on, whereas three irrelevant FAQs are
actively harmful because a capable model will try to answer from them.

Keep `is_answer_found` as a **separate axis**: retrieval score answers *did we
find something*; the model answers *was it enough*. Log both.

## B5. The orchestration loop

### Turn lifecycle
1. Resolve conversation → chatbot → policy. **Bind `chatbot_id` and `company_id`
   to the turn now**; nothing downstream reads them from anywhere else, ever.
2. If a human agent owns the session, **skip the model entirely** — the existing
   `_live_agent_id` check, unchanged and still first.
3. Assemble context (B7). Load cached tool declarations.
4. Call the model with history + declarations.
5. No tool call → stream the reply, persist, done.
6. Tool call(s) → validate (B6) → execute, in parallel when independent → append
   `role='tool'` messages → back to step 4.
7. On budget exhaustion, **degrade deliberately**: one final model call with
   tools withheld and an instruction to answer from what it has, or hand off.

### Budgets
| Budget | Default | On breach |
|---|---|---|
| `tool_calls_per_turn` | 4 | Withhold tools, force a final answer |
| `model_round_trips` | 3 | Same |
| `wall_clock_ms` | 20 000 | Apologise + offer handoff |
| `single_tool_timeout_ms` | 6 000 | Return a timeout **result** to the model, continue |
| `repeat_identical_call` | 1 | Return a cached result, do not re-execute |

A tool that times out returns a *result*, not an exception. The model handles
"that lookup did not respond" far better than the orchestrator handles an unwind
mid-turn, and the customer gets a sentence instead of a spinner.

### Handoff becomes a tool
Today escalation is a side effect of a low similarity score. Make it
`request_human_agent`, a tool the model calls when it judges it cannot help —
**and keep a server-side safety net independent of the model**: N consecutive
turns with no successful tool result, an explicit "talk to a human" pattern
match, or budget exhaustion all force handoff regardless of what the model wants.
Model judgement is better at the decision; the server rule is what stops a loop.

### Worked example — the multi-turn case
```
Turn 1
customer  "I want to buy a property in Ahmedabad"
model  → search_available_listings({ city: "Ahmedabad", limit: 10 })
tool   ← { matched: 312, returned: 10, truncated: true, rows: [...] }
model  → "We have 312 listings in Ahmedabad. What's your budget, and how many bedrooms?"

Turn 2 — the follow-up
customer  "Under 80 lakh and 3 BHK, near SG Highway"
model  → search_available_listings({ city:"Ahmedabad", bedrooms:3, max_price:8000000, locality:"SG Highway" })
tool   ← { matched: 0, returned: 0, relaxable_filters: ["max_price"] }
model  → search_available_listings({ city:"Ahmedabad", bedrooms:3, locality:"SG Highway", sort_by:"price_asc", limit:5 })
tool   ← { matched: 18, returned: 5, rows: [{ price: 9200000, ... }] }
model  → "Nothing on SG Highway at 3 BHK under 80 lakh. Closest is 92 lakh — show those, or widen the area?"
```
`city: "Ahmedabad"` reappears in turn 2 because the turn-1 tool call is in the
replayed history — **no filter state store, no slot machine, no merge logic**.
And the second call within turn 2 is the model reacting to `relaxable_filters`
inside a single turn, which the current pipeline cannot express at all.

## B6. Validation and security — ten gates

Every tool execution passes all of them. None is skippable by tool type.

| Gate | Enforces | On failure |
|---|---|---|
| G1 | **Tenancy binding.** `chatbot_id`/`company_id` come from the server-side session. Model-supplied tenant identifiers are *ignored*, not merely validated. | Drop + alert |
| G2 | Tool exists, is active, belongs to this chatbot | Error to model |
| G3 | JSON Schema 2020-12 against `input_schema` | Error to model |
| G4 | Every referenced field is `is_exposed` on that data source | Error to model |
| G5 | Operator is in that field's `allowed_operators` | Error to model |
| G6 | Value casts to the declared type; enums matched exactly | Error to model |
| G7 | Row cap, offset cap, filter-count cap, token cap | Clamp silently |
| G8 | Egress: allowlist + resolved-IP check + pinned connect | Drop + alert |
| G9 | Per-conversation and per-company rate limits | Error to model |
| G10 | Audit: write `tool_executions` — raw args, validated args, outcome, timing | — |

**Rejection is a feature.** A failed validation returns a machine-readable error
naming the offending field and the allowed values, so the model's next attempt is
informed rather than a blind retry.

**G1 must never be relaxed.** Every cross-tenant leak in a system shaped like
this traces back to a tenant identifier that arrived as a tool argument. Treat
model output as untrusted user input — in a prompt-injection scenario that is
precisely what it is.

### Prompt injection through tool results
Retrieved chunks and fetched rows are content a tenant uploaded, or (in the
`rest_api` case) content a third party returned. Wrap every tool result in an
explicit data envelope, state in the system prompt that tool output is data and
never instruction, and enforce the part that actually holds: **no tool result can
change tool availability, tenancy binding, or confirmation state.** Those live in
server state, so a successful injection can mislead a reply but cannot escalate a
capability.

### Actions specifically
- **Two-phase confirmation, enforced server-side** (not by prompt instruction).
  When `requires_confirmation` is set, the first invocation returns
  `{"status":"confirmation_required","summary":"…","confirmation_token":"cnf_…"}`
  without executing. Tokens are single-use, conversation-scoped, **bound to a
  hash of the validated arguments**, and expire in five minutes — so a model that
  "confirms itself" or drifts on the arguments fails closed.
- **SSRF is the headline risk.** "Business users configure an API URL" hands an
  SSRF primitive to your least-trusted input. Non-negotiable: per-company URL
  allowlist; DNS resolution *before* connect with the resolved IP checked against
  RFC1918 / loopback / link-local / `169.254.169.254`, then **pinned** for the
  request to close the TOCTOU gap; redirects disabled or re-validated per hop;
  HTTP(S) only; hard timeout; response size cap; no credentials forwarded cross-host.
- **Secrets never enter the schema.** Credentials resolve from
  `credentials.secret_ciphertext` at execution time and are injected into headers
  by the client. Redacted from `tool_executions`.
- **Idempotency.** Key derived from `(conversation_id, action_id, hash(args))`
  goes out as `Idempotency-Key` and is checked locally, so a retry after a
  timeout does not create two leads.
- **Circuit breaker** per action — after N consecutive failures the tool is
  withheld from the declaration list so the model routes around it.

## B7. Conversation context

> **The message log is the state.** Persist tool calls and tool results as
> `chat_message` rows and replay them. **Do not auto-merge filters server-side.**
> Sticky server-side filters are invisible to the model and to the customer and
> become impossible to clear — "actually, anywhere in Gujarat" has to defeat a
> merge rule the model does not know exists. Re-emission from history is
> self-correcting: what the model can see, it can change.

Assembly order per turn:
1. System prompt — platform rules + `chatbots.persona_prompt`.
2. Rolling summary of everything before the recent window.
3. Last 8 turns verbatim, including tool calls with their arguments.
4. Tool results: full JSON for the last 2 turns; older ones replaced by
   `tool_result_summary` ("returned 10 of 312 Ahmedabad listings"). Row payloads
   dominate the budget and age badly — the **call** carries forward, not the rows.
5. `working_set`, if non-empty.

`working_set` is deliberately small: last successful query per data source,
confirmed identity fields, pending confirmation token. It is a **cache, not a
source of truth** — cleared on session close, never read by a validator,
reconstructible from the message log. Anything richer is a dialogue state
machine, which is exactly the industry-specific hardcoding this design avoids.

## B8. Configuration UX (the actual product)

Adding an industry must be configuration, not a deploy. Seven screens in the
existing React dashboard:
0. **Preset** — "what kind of chatbot?" (B0). Creates the `chatbots` row and
   its starting `tools` rows. Changeable later by inserting rows, never a migration.
1. **Knowledge** — the current FAQ editor, plus document and URL upload.
   Chunking/embedding are background jobs with visible progress. This is where
   privacy policy / return policy / company-info files land.
2. **Connect data** — CSV/JSON upload first (covers most pilots), then REST, then
   read-only SQL.
3. **Schema review** — types inferred from a sample; the user confirms or
   corrects. Inference is a suggestion, never silently authoritative.
4. **Field permissions** — the screen that matters. One row per field with
   toggles for exposed / filterable / sortable / returned, plus operator chips.
5. **Actions** — endpoint, method, parameters, credential, confirmation flag,
   and a "send test request" button showing the exact outbound call.
6. **Tool descriptions** — name and description per tool with a live
   **"what the AI sees"** panel rendering the compiled declaration.

> **Build the test console in the same phase.** A test chat showing every tool
> call, its validated arguments, its result and its timing, inline. Tool
> descriptions are prompt engineering whether or not you call them that, and a
> business user cannot write a good one blind. Without this screen, every
> misconfigured bot is a support ticket you debug from logs.

## B9. Scaling and operations

- **Redis channel layer** — prerequisite, not an optimization. Groups in the
  in-memory layer exist only inside one process, so handoff silently breaks with
  a second worker.
- **Move orchestration off the consumer.** A turn is now seconds of model
  latency. The consumer enqueues; a worker runs the loop and publishes tokens
  back through the session group. This is also what makes multi-worker
  deployment possible at all.
- **Stream the final answer**, and emit a lightweight "checking our listings…"
  event when a tool starts, keyed off the tool's own description.
- **Move embedding out of the request path.** MiniLM is ~10 ms but it is
  CPU-bound work inside an async consumer.
- **Watch the dimension lock-in.** `vector(384)` is a column type;
  `embedding_model` per chunk is what keeps a model upgrade from being an outage.
- **Cost.** Declarations are re-sent every round trip — a 6-tool bot pays
  ~400–900 tokens per call just to describe itself. Cache the compiled JSON, keep
  descriptions tight, prune unused tools.

Latency budget, typical two-tool turn: context assembly + declaration cache hit
< 30 ms · model round trip 1 (decide) 600–1200 ms · tool execution (indexed)
20–120 ms · model round trip 2 (compose, streamed) 800–2000 ms ·
**first token ~1.5–3.5 s**.

---

# PART C — Migration plan

| Phase | Ships | Proves | Status |
|---|---|---|---|
| **0 — Unblock** | Bearer session tokens replacing `?user_type=`; Redis channel layer; pgvector + HNSW on `questions.embedding`; threshold 0.90 → 0.40; index/query text symmetry | Existing bot gets faster and stops over-escalating | ✅ **done** |
| **1 — Loop** | `chatbots` + `tools`; orchestrator with exactly **two** tools (`search_knowledge`, `request_human_agent`); consumer reduced to transport; conversation history in context | The loop, the budgets, and multi-turn — at feature parity plus follow-ups | ▶ **next** |
| **2 — Structured** | `data_sources` / `data_source_fields` / `data_records`; CSV+JSON import; declaration generator; IR compiler; validator; `records` adapter | Real estate **and** one unrelated vertical on the same code, differing only by registry rows | |
| **3 — Actions** | `actions` / `credentials`; egress guard; confirmation flow; rate limits; circuit breaker | Lead capture end to end, with a security review against B6 before it faces the internet | |
| **4 — Self-serve** | The B8 config UI, the test console, per-tenant threshold tuning | A new tenant onboards with no engineering involvement | |

**Protect Phase 1 from scope creep.** Two tools is enough to prove the loop, and
every later capability is a registry row plus an executor — which is precisely
the claim this architecture makes.

## Open decisions
| | Question | Recommendation |
|---|---|---|
| D1 | Introduce `chatbots` now, or keep `company` as the tenant key? | **Now.** One table and one FK while the data is small; later means backfilling every tool, source and conversation row. |
| D2 | JSONB record store, or per-source physical tables? | **JSONB**, with the adapter seam for a later migration. |
| D3 | Flat parameters, or raw filter IR as the model-facing schema? | **Flat**, with opt-in `advanced_filters`. |
| D4 | Bind to Gemini, or abstract the provider now? | **Thin adapter now** — declarations in, calls out. A day's work, not a framework. |
| D5 | Cross-encoder reranker for knowledge search? | **Not in v1.** Ship RRF, measure with the B4 harness, revisit with data. |
| D6 | Is handoff the model's decision or the server's? | **Both.** Tool for intent, independent server rule as the safety net. |

---

# PART D — Rules for an AI agent editing this repo

1. **Tenancy first.** Any new endpoint, consumer, or executor derives the tenant
   from the authenticated token or the server-side session. Never from the body,
   query string, or a model-supplied argument. Use `config/tenancy.py`.
2. **Do not revert the tuned retrieval constants.** `CHAT_CONFIDENCE_THRESHOLD =
   0.40` and bare-question `build_retrieval_text` are measured, and pinned by
   `tests/test_retrieval.py`. Changing either means re-running that harness.
3. **Do not add industry-specific branches.** No `if vertical == "real_estate"`.
   If a new vertical needs a code change, the abstraction leaked — the fix
   belongs in the registry, not the orchestrator.
3a. **A preset is data, not a branch.** The "what kind of chatbot?" answer (B0)
   provisions `tools` rows at onboarding and is never read again at runtime.
   There must be no `if bot_type == "qna"` anywhere in the orchestrator — one
   company will want both modes in one conversation, and most eventually do.
4. **Keep the agent-handoff check first.** If a human owns the session, the model
   is skipped entirely. Preserve this when the orchestrator lands.
5. **The message log is the state.** No parallel transcript table; no
   server-side filter merging.
6. **Additive migrations.** `questions` stays as the FAQ authoring surface. Do
   not drop it when `knowledge_chunks` arrives.
7. **New capability = new executor behind the same interface + registry rows.**
   Never a new branch in the consumer.
8. When touching embeddings, remember `Question.save()` invalidates the embedding
   on text change, and that `vector(384)` is a column type — a model swap is a
   migration, not a config flip.
9. **One dataset per kind of thing, never per category** (E2, Trap 1). Buy/rent,
   men's/women's, new/used are *columns*, not separate data sources. And split
   any column whose meaning depends on another column (E2, Trap 2).
10. **Update this file** when the architecture changes, and flip the Phase status
   table in Part C. Worked examples belong in Part E, not inline in Part B.

---

# PART E — Onboarding playbook (worked examples)

Part B is the architecture. This part is the **plain-language version** — what a
company actually does, and what your portal must ask them for. Use it when
explaining the product, when designing the onboarding screens, and as the
acceptance criteria for Phase 4.

## E1. The two boxes

Every company, in every industry, supplies exactly two kinds of thing:

| | What it is | How they give it | Lands in |
|---|---|---|---|
| **Box 1 — Text** | Policies, rules, general info. Answers that are *paragraphs*. | Upload files + type FAQ pairs | `knowledge_sources` → `knowledge_chunks` |
| **Box 2 — Items** | Things with **fields** you filter on. Answers that are *a list*. | Upload a spreadsheet | `data_sources` + `data_source_fields` + `data_records` |

**The test for which box something belongs in:**
*"Does the customer pick from many similar things?"*
Yes → Box 2. One fixed answer everyone gets → Box 1.

Preset 1 (B0) fills Box 1 only. Preset 2 fills both. Most companies end up
needing both, which is why the preset must never be a code branch.

## E2. Worked example — a real estate company

Take three real customer questions and notice they are **not the same kind**:

| Question | Needs | Box |
|---|---|---|
| "i want to buy 2bhk property into new ranip" | filter a list | **2** |
| "how much brokerage you take" | one fixed answer | **1** |
| "i want to rent a 1bhk flat in ahmedabad" | filter a list | **2** |

### Box 1 — files they already have
`brokerage-and-fees.pdf`, `rental-agreement-process.pdf`,
`documents-required-for-purchase.pdf`, `about-us.txt`, plus a handful of typed
FAQ pairs for one-line facts (office hours, service areas).

### Box 2 — the spreadsheet template

| ref | title | **listing_type** | property_type | city | locality | bedrooms | **sale_price** | **monthly_rent** | deposit | area_sqft | floor | total_floors | furnishing | amenities | status | description | owner_phone |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-101 | Shivalik Residency | buy | apartment | Ahmedabad | New Ranip | 2 | 6500000 | | | 1050 | 3 | 11 | unfurnished | lift;parking | available | Spacious 2BHK… | 98250… |
| P-102 | Green Heights | rent | apartment | Ahmedabad | Chandkheda | 1 | | 14000 | 50000 | 620 | 5 | 9 | semi | lift;gym | available | Cosy 1BHK… | 98251… |

**One row = one item. One fact = one column.** That is the whole rule.

### The three modelling traps

These are generic — they recur in every vertical under different names, so the
onboarding UI should actively warn about them.

**Trap 1 — splitting one dataset by category.**
Buy and rent go in **one** source with a `listing_type` column, never two
sources. A customer says *"actually, anything to rent instead?"* mid-chat; with
one source that is a different filter value, with two it is the model juggling
two tools. Generalizes to: **one dataset per *kind of thing*, never per
category.** Products = one source, not one per department.

**Trap 2 — one column meaning two things.**
Never a single `price`. A sale is `6500000`; a rent is `14000/month`. In one
column, *"under 20,000"* matches every rental and nothing sensible for sales.
Use `sale_price` **and** `monthly_rent`, leaving the irrelevant one blank — a
rental row has no sale price, so a "under 80 lakh" search skips it for free.
Generalizes to: **if a column's meaning depends on another column, split it.**

**Trap 3 — collapsing a hierarchy into one field.**
"New Ranip" is a *locality*; "Ahmedabad" is a *city*. Question 1 gives the
locality, question 3 gives the city. With only `locality`, question 3 finds
nothing; with only `city`, question 1 cannot narrow. **Keep every level of the
hierarchy as its own filterable column.** Same for category/sub-category in
e-commerce, department/specialty in a clinic.

### Field settings the company then confirms

| Column | Type | Searchable | Shown | Note |
|---|---|---|---|---|
| listing_type, property_type, city, locality, furnishing | pick-list | ✅ | ✅ | |
| bedrooms, sale_price, monthly_rent, floor, total_floors, area_sqft | number | ✅ | ✅ | |
| amenities | multi-pick | ✅ | ✅ | |
| status | pick-list | **fixed filter → `available`** | ❌ | see E4 |
| description, title | text | ❌ | ✅ | |
| **owner_phone** | text | ❌ | ❌ | never leaves the database |

### The three questions, end to end
```
1) "i want to buy 2bhk property into new ranip"
   → search_properties({ listing_type:"buy", bedrooms:2, locality:"New Ranip" })
   → 8 matches, shown as a list

2) "how much brokerage you take"
   → search_knowledge("brokerage")
   → chunk from brokerage-and-fees.pdf

3) "i want to rent a 1bhk flat in ahmedabad"
   → search_properties({ listing_type:"rent", bedrooms:1, city:"Ahmedabad" })
   → { matched: 312, truncated: true }
   → "312 1BHK rentals in Ahmedabad. Which area, and your monthly budget?"
```
Question 3 is the payoff: because the result carries `matched` and `truncated`
(B3), the bot narrows instead of dumping a list — and when the customer replies
*"New Ranip, under 15000"*, the earlier filters carry forward from the message
log (B7) with no state machine.

## E3. Worked example — an e-commerce company

**Identical steps, different content.** This is the proof the design is universal.

Box 1: `return-and-refund-policy.pdf`, `shipping-and-delivery.pdf`, `privacy-policy.pdf`.

Box 2:

| sku | name | category | sub_category | brand | price | size | color | in_stock | cost_price |
|---|---|---|---|---|---|---|---|---|---|
| SKU-77 | Running Shoes | Footwear | Sports | Nike | 4999 | 9 | Black | true | 2100 |
| SKU-78 | Cotton Kurta | Clothing | Ethnic | Fabindia | 1899 | M | Blue | true | 700 |

Hidden field: `cost_price` — the exact same mechanism that hides `owner_phone`.
Trap 3 shows up again as `category` / `sub_category`.

```
"show me blue kurtas under 2000"  → search_products({ color:"Blue", sub_category:"Ethnic", max_price:2000 })
"can i return after 20 days?"     → search_knowledge("return period")
```

### Side by side

| | Real estate | E-commerce |
|---|---|---|
| Files | brokerage, documents needed | returns, shipping |
| Spreadsheet | properties | products |
| Columns | locality, bedrooms, sale_price… | category, brand, price, size… |
| Hidden column | `owner_phone` | `cost_price` |
| Hierarchy trap | city / locality | category / sub_category |
| **Screens used** | **the same** | **the same** |
| **Python written** | **none** | **none** |

## E4. What the portal must provide (Phase 4 requirements)

These come out of the walkthroughs above and are easy to leave out:

1. **A downloadable template spreadsheet** per preset, columns pre-named with one
   example row filled in. Do not hand a company a blank sheet and hope — most bad
   chatbots trace back to a messy first upload, and the template is the cheapest
   possible fix.
2. **Fixed filters per data source.** `status = available` must be applied
   server-side always, and *not* offered to the model. Otherwise a customer asks
   *"show me sold properties"* and the bot obliges. Every vertical has one of
   these (`in_stock`, `is_active`, `accepting_patients`).
3. **Required field descriptions, with examples.** The customer types "flat",
   "2bhk", "top floor"; the column is `property_type`, `bedrooms`,
   `total_floors`. The model bridges that vocabulary gap **only if the
   description is written**:
   - `bedrooms` → *"Number of bedrooms. Customers call this BHK — '2BHK' means 2."*
   - `property_type` → *"Customers may say 'flat' for apartment, 'bungalow' for villa."*

   This is the most-skipped and most-load-bearing field in the whole portal.
   Make it required with a live example, not an optional box.
4. **Show cardinality and values on the schema-review screen** — *"locality has
   47 distinct values: New Ranip, new ranip, Newranip, …"*. That is when a
   company notices its own data is messy, instead of you discovering it from a
   customer complaint. Dirty enums are the number-one cause of a bot that
   "doesn't find anything".
