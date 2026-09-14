# Implementation Tasks

Companion to [`WORKFLOW.md`](./WORKFLOW.md). That file is the *design*; this one
is the *queue*. Section references like **B0**, **B3**, **G4** point into it.

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` deferred

**Where to look things up:** Part A = what exists · Part B = the design ·
Part C = phases · Part D = rules · **Part E = plain-language worked examples**
(real estate + e-commerce), which is what the Phase 2 and Phase 4 tasks below
are written against.

**Rules for whoever works this list**
- Do not start a phase before the one above it is done. The order encodes real
  dependencies, not preference.
- Every task states its *done-when*. If you cannot demonstrate the done-when,
  the task is not done.
- Re-read Part D of WORKFLOW.md before writing code. Especially rule 1
  (tenancy), rule 3 (no industry branches) and rule 3a (a preset is data).
- **Update this file and WORKFLOW.md in the same commit as the code.** A task
  ticked here with nothing shipped, or a table in Part A that no longer matches
  the models, is worse than no document — the next agent trusts it.

**Conventions already set by shipped code** (follow them; do not re-litigate)
- Registry lives in `TEMPSERVER/registry/`. `Chatbot` is the anchor for
  everything Phase 2+ adds; new tables FK to it, not to `Company`.
- Per-bot budgets are read with `Chatbot.get_policy(key)`, never by indexing
  `policy`. Defaults live in `registry.models.default_policy()`.
- Presets are rows written by `registry/presets.py` at onboarding, never read at
  runtime. Adding a vertical means adding a `PRESETS` entry, not a branch.
- Data migrations **copy their specs in and freeze them**; they never import
  `presets.py`, which will keep changing.
- Tests for a new app go in `TEMPSERVER/tests/test_<app>.py`, not the app's own
  `tests.py`, matching `test_retrieval.py` and `test_auth_and_tenancy.py`.

---

## Phase 0 — Unblock ✅ done

Recorded for history; do not redo.

- [x] Bearer tokens (`users.AuthToken`) replacing `?user_type=` permission checks
- [x] Tenant scoping derived from the token (`config/tenancy.py`)
- [x] pgvector column + HNSW index on `questions.embedding`
- [x] `CHAT_CONFIDENCE_THRESHOLD` 0.90 → 0.40, pinned by `tests/test_retrieval.py`
- [x] Index/query text symmetry (`build_retrieval_text` = bare question)
- [x] Redis channel layer selectable via `REDIS_URL`

---

## Phase 1 — The loop ✅ done

Goal: **feature parity with today, plus multi-turn follow-ups**, with routing
moved from the consumer into the model. Two tools only.

> **Protect this phase from scope creep.** No structured data, no actions, no
> config UI. Two tools is enough to prove the loop.

**Where this phase stands:** shipped. The socket runs every customer message
through `orchestration.run_turn`; `chatbots.policy` is read at runtime; the old
threshold-then-LLM pipeline and `vector_question.generate_answer` are gone.
Pinned by `tests/test_orchestration.py` (27 tests). Read the *Carried forward*
list at the end of this phase before starting Phase 2.

### 1.1 Decide D1 before writing any migration ✅ done
- [x] **Confirm the `chatbots` table lands now, not later.** (WORKFLOW.md → Open
      decisions, D1.) **Answer: now.** Written into the D1 row (2026-09-09).
      Do not re-open.

### 1.2 Schema

**1.2a — the registry ✅ done.** Shipped in `TEMPSERVER/registry/`.

- [x] New Django app `registry`. Models: `Chatbot`, `Tool` (**B2.1 / B2.4**),
      `registry/presets.py`, `default_policy()` + `Chatbot.get_policy()`,
      `Tool.declaration()`, admin, `tests/test_registry.py`.
- [x] Data migration `registry/0002_backfill_chatbots.py` — one `Chatbot` per
      existing `Company` plus its two preset `Tool` rows, specs frozen.
- [x] *Added in 1.2b:* registration (`users/serializers.py`) now calls
      `provision_chatbot`, so companies created after the backfill get a bot.

**1.2b — the conversation schema ✅ done.** `chat/0003_conversation_schema`,
`chat/0004_backfill_roles_and_chatbots`.
- [x] `chat.ChatSession`: `chatbot` FK, `visitor_id`, `channel`,
      `working_set` JSONB, `summary`, `summary_upto_message_id`. (**B2.5**)
      Existing sessions backfilled to their company's first chatbot.
- [x] `chat.ChatMessage`: `role`, `tool_call_id`, `tool_name`, `tool_args`,
      `tool_result`, `tool_result_summary`, `tokens`, `latency_ms`. (**B2.5**)
      Backfilled `user` / `assistant` from `sent_by_us`.
      An assistant row with `tool_name` set is a *call*; a `tool` row is its
      result. `ChatMessage.objects.transcript()` hides both from the widget
      history, the agent console and inbox previews — same rows, filtered.
- [x] `chat.ToolExecution` → `tool_executions` (**B2.5**), one row per call
      including rejected ones, plus `company` FK for tenant scoping.

### 1.3 Provider adapter (D4) ✅ done
- [x] `orchestration/providers/` — `base.py` (`ChatProvider`, `ToolCall`,
      `HistoryItem`, `ModelResponse`), `gemini.py`, `get_provider()` keyed by
      `CHAT_PROVIDER`. Gemini thought signatures are persisted in the call row's
      `attachments.provider_meta` and replayed.
      *Done when:* nothing outside this package imports `google.genai` —
      ✅ pinned by `StructureTests`.
      *Not done here:* token streaming — see Cross-cutting.

### 1.4 The orchestrator ✅ done
- [x] `orchestration.orchestrator.run_turn(session, message, …)` implementing
      **B5**: store → **live-agent check first** → re-read chatbot/policy →
      safety net → context → model → gates → execute → loop.
- [x] Budgets read via `chatbot.get_policy()`. Round trips / tool-call cap →
      one final call with tools withheld; empty final answer → handoff;
      wall clock → apology + handoff; tool timeout → a `timeout` *result*
      (executor runs in a worker thread, `ORCHESTRATION_TOOL_THREADS`);
      identical repeat call → `cached`, not re-executed.
- [x] Context per **B7** (`orchestration/context.py`): platform prompt +
      persona, `summary`, last 8 turns, full tool JSON for the last 2 turns and
      `tool_result_summary` beyond, `working_set` if set. No filter merging.
      *Nothing writes `summary` or `working_set` yet* — columns and replay
      exist; the summariser is future work.
- [x] Gates **G1** (tenant keys dropped + WARNING log, executors only see
      `ctx.company_id`), **G2** (unknown tool → error listing available tools),
      **G3** (`orchestration/validation.py`, the schema subset the registry
      emits — swap in `jsonschema` if Phase 2 outgrows it), **G7** (tool-call
      cap, `top_k` max), **G9** (`rate_limit.per_conversation` /
      `per_company_per_minute`), **G10** (`tool_executions`).
      Tool results reach the model in a `{"data": …}` envelope and the system
      prompt states tool output is data.

### 1.5 The two tools ✅ done
- [x] `search_knowledge` (`orchestration/executors.py`) — today's pgvector
      retrieval behind `accept_threshold` / `retrieval_floor` from policy.
      Returns `{"chunks": [], "reason": "no_relevant_content"}` below the gate
      and parks the message in `UnansweredMessage`, as before.
      `margin_rule` is not applied — it needs the hybrid recall of Phase 2b.
- [x] `request_human_agent` — wraps `flag_agent_needed` and pings the agent
      console (`hand_off`, shared with the safety net).
- [x] Server-side handoff safety net (**B5**): explicit "talk to a human"
      pattern (model skipped), no active chatbot, budget exhaustion with no
      answer, and `handoff_after_barren_turns` consecutive turns whose tool
      calls all failed or came back empty — computed from `tool_executions`,
      so greetings (no tool call) never count.
      *Done when:* a deliberately looping model still reaches an agent — ✅.

### 1.6 Reduce the consumer to transport ✅ done
- [x] `questions/consumers.py` — parse → `resolve_session` → `run_turn` →
      send frames. *Done when:* no threshold comparison and no LLM call —
      ✅ pinned by `StructureTests`.
- [x] Outbound frame shape unchanged (`answer`, `delivered`, `error`,
      `session_id`, `session_token`, …). Added `type:"tool_started"`
      (`{tool, label}`, label from `tool.configuration.progress_label`).
      ⚠️ One-line frontend change was unavoidable: the widget's `switch`
      treated any unknown frame as an answer, so
      `useCustomerChatSocket.js` now ignores `tool_started`.

### 1.7 Prove it ✅ done — `tests/test_orchestration.py`
- [x] A greeting produces **no** knowledge search (`GreetingTests`).
- [x] A follow-up turn resolves against prior context (`FollowUpTests`).
- [x] Cross-tenant tool argument is ignored, not honoured (`TenancyTests`).
- [x] Budget exhaustion degrades to a final answer or handoff (`BudgetTests`).
- [x] `tests/test_retrieval.py` still passes unchanged.

### Carried forward from Phase 1 (not blockers for Phase 2)
- Turns still run inside the consumer process via `sync_to_async`; moving them
  to a worker and streaming tokens are the Cross-cutting tasks below.
- No live Gemini call is exercised by the test suite (the model is a scripted
  fake). Smoke-test the widget against a real `GEMINI_API_KEY` after deploy.
- `summary` / `working_set` are replayed but never written.

---

## Phase 2 — Structured data (the universality payoff)

Goal: **a real estate bot and an unrelated vertical running the same code**,
differing only by registry rows. This is where B0 preset 2 becomes real.

### 2.1 Schema
- [ ] `data_sources`, `data_source_fields`, `data_records`, `data_source_syncs`
      per **B2.3**. `data_records.payload` is JSONB (D2).
- [ ] Indexes: GIN `jsonb_path_ops` on `payload`; B-tree expression indexes on
      numeric/date fields created **once when a source is published**, not per query.

### 2.2 Ingestion
- [ ] CSV **and** JSON upload → `data_records`, upsert on
      `(data_source_id, external_id)`, run recorded in `data_source_syncs`.
- [ ] Type inference from a sample → suggested `data_source_fields` rows.
      *Inference is a suggestion, never silently authoritative* — a human
      confirms before the source can be published.
- [ ] Cardinality computation per string field (drives enum vs. free text in B3).
- [ ] **Fixed filters per data source** (**E4.2**). A filter the server always
      applies and never exposes to the model — `status = available`,
      `in_stock = true`, `is_active = true`. Store on `data_sources.config`.
      *Done when:* asking the bot "show me sold properties" returns none.
      *Every vertical needs one of these — do not ship Phase 2 without it.*
- [ ] **`description` required on every exposed field** (**E4.3**), with a live
      example in the UI. This is what maps "flat"→apartment and "2bhk"→bedrooms=2.
      *Done when:* a source cannot be published with a blank description on an
      exposed field.
- [ ] Import-time warnings for the three modelling traps (**E2**): a source that
      looks split by category, a column whose meaning depends on another
      (`price` where rows differ by `listing_type`), and a collapsed hierarchy.
      Warn, do not block — the company decides.

### 2.3 Declaration generator
- [ ] `data_source_fields` → flat JSON Schema, following the generation table in
      **B3** exactly (enum ≤50 cardinality, `min_`/`max_` pairs for numbers,
      `_after`/`_before` for dates, `sort_by` enum).
- [ ] Cache compiled declarations per `(chatbot_id, schema_version)`; invalidate
      on any write to `tools`, `data_source_fields` or `action_parameters`.
      *Why it matters:* declarations are re-sent every round trip (**B9**).
- [ ] Never emit `data_source_id`, operators, field paths or table names into the
      declaration.

### 2.4 Compiler, validator, adapter
- [ ] Flat parameters → the internal filter IR of **B3**. The model never emits
      IR (D3).
- [ ] Gates **G4** (`is_exposed`), **G5** (`allowed_operators`), **G6**
      (type coercion / exact enum match). A rejection returns a *machine-readable
      error naming the field and the allowed values* so the retry is informed.
- [ ] `records` adapter: IR → ORM `KeyTextTransform` with an explicit cast per
      declared type.
- [ ] Result shaping per **B3**: `matched`, `returned`, `truncated`, and
      `relaxable_filters` computed by re-running with each filter dropped in turn.
      *Done when:* a zero-result query yields a useful next sentence, not a dead end.
- [ ] `STRUCTURED_SEARCH` registered as a tool type in the registry.

### 2.5 Prove it
- [ ] The B0 worked example end to end: *"2BHK in New Ranip, not top floor"* →
      correct IR → correct rows.
- [ ] **The acceptance test for the whole product:** onboard a second, unrelated
      vertical (products, or clinic appointments) **touching no Python**.
      If it needs a code change, the abstraction leaked.
- [ ] A non-exposed field (`internal_margin`) is invisible in both directions —
      cannot be filtered on, never returned.
- [ ] One conversation crosses between `search_knowledge` and
      `search_<thing>` (**B0**) — proving the preset is not a branch.
- [ ] The full E2 set on one bot: "buy 2bhk in New Ranip" (structured),
      "how much brokerage" (knowledge), "rent 1bhk in Ahmedabad" (structured,
      city-level, returns `truncated` and narrows instead of dumping a list).
- [ ] Buy and rent live in **one** data source with a `listing_type` field, and
      `sale_price` / `monthly_rent` are separate columns (**E2** traps 1 and 2).
- [ ] `city` and `locality` are both filterable; a city-only query still works.

---

## Phase 2b — Documents as knowledge

Can run parallel with Phase 2; independent of it. This is the "let companies
upload their privacy policy / return policy" half of B0.

- [ ] `knowledge_sources`, `knowledge_documents`, `knowledge_chunks` per **B2.2**.
      `embed_text` separate from `content`; `embedding_model` stored per chunk.
- [ ] Migrate `questions` rows into `knowledge_chunks` as `kind='faq'` — with
      `embed_text` = question, `content` = answer. **Keep `questions` as the
      authoring surface** (Part D rule 6). Do not drop it.
- [ ] File upload + text extraction (PDF/DOCX/TXT/MD/HTML) with a `checksum` so
      re-uploading an unchanged file is a no-op.
- [ ] Chunker: ~300–500 tokens, ~15% overlap, split on headings and paragraph
      boundaries, never mid-sentence. Store `{document_title, section_heading,
      page}` in chunk metadata.
- [ ] Ingestion as a **background job with visible progress**, not a request.
- [ ] Hybrid retrieval per **B4**: pgvector top-30 + tsvector top-30 fused with
      RRF (`Σ 1/(60+rank)`). *This is what makes policy documents work* — clause
      numbers and plan names are exactly where full-text beats vectors.
- [ ] Three-signal gate (`retrieval_floor`, `accept_threshold`, `margin_rule`)
      stored in `chatbots.policy`.
- [ ] **Ship the measurement harness in this same phase** (**B4**): ~50 labelled
      questions per pilot tenant tagged `answerable`/`not`, tuned against
      precision on the `not` set. An unmeasured threshold is a guess — that is
      how 0.90 got there.
- [ ] Move embedding out of the request path (**B9**).

---

## Phase 3 — Actions

Goal: the bot can *do* things (capture a lead, book a slot), not just answer.

> **Security review against B6 before this faces the internet.** This is the
> only capability that writes to the world and the only one where a business
> user supplies a URL you will call.

- [ ] `actions`, `action_parameters`, `credentials` per **B2.4**.
- [ ] `API_ACTION` executor + declaration generation from `action_parameters`.
- [ ] **Gate G8 / egress guard** (**B6**): per-company URL allowlist; DNS
      resolved *before* connect and the resolved IP checked against RFC1918,
      loopback, link-local and `169.254.169.254`, then **pinned** for the request
      to close the TOCTOU gap; redirects disabled or re-validated per hop;
      HTTP(S) only; hard timeout; response size cap; no credentials cross-host.
- [ ] Two-phase confirmation enforced **server-side**, not by prompt instruction.
      Tokens single-use, conversation-scoped, bound to a hash of the *validated*
      arguments, 5-minute expiry.
      *Done when:* a model that "confirms itself", or drifts on the arguments
      between the two calls, fails closed.
- [ ] Secrets resolve from `credentials.secret_ciphertext` at execution time,
      injected into headers by the client, redacted from `tool_executions`.
      Never in a schema the model sees.
- [ ] Idempotency key from `(conversation_id, action_id, hash(args))`, checked
      locally *and* sent as `Idempotency-Key`.
      *Done when:* a retry after a timeout does not create two leads.
- [ ] Rate limits at three scopes; circuit breaker per action that withholds a
      failing tool from the declaration list.

---

## Phase 4 — Self-serve onboarding

Goal: **a new tenant onboards with no engineering involvement.** That is the
actual product goal.

- [ ] Preset picker — the B0 question. Creates the `Chatbot` row and its preset
      `Tool` rows. **Data, not a branch** (Part D rule 3a).
- [ ] Knowledge screen: existing FAQ editor + document/URL upload with progress.
- [ ] Connect data: CSV/JSON upload → schema review (confirm or correct inferred
      types) → publish.
- [ ] **Downloadable template spreadsheet per preset** (**E4.1**), columns
      pre-named with one example row filled in. Never hand out a blank sheet —
      most bad bots trace back to a messy first upload.
- [ ] Schema-review screen **shows cardinality and the actual distinct values**
      per field (**E4.4**): *"locality has 47 values: New Ranip, new ranip,
      Newranip…"*. This is where a company sees its own data is dirty. Dirty
      enums are the number-one cause of "the bot doesn't find anything".
- [ ] Fixed-filter toggle on the field-permissions screen (pairs with the
      Phase 2 backend task).
- [ ] **Field permissions screen — the one that matters.** One row per field,
      toggles for exposed / filterable / sortable / returned, operator chips.
      This is where `internal_margin` stays invisible.
- [ ] Actions screen with a "send test request" button showing the exact
      outbound call.
- [ ] Tool descriptions with a live **"what the AI sees"** panel rendering the
      compiled declaration.
- [ ] **Test console, shipped in this same phase** (**B8**): every tool call, its
      validated arguments, its result and its timing, inline next to the chat.
      *Why it is not optional:* tool descriptions are prompt engineering, and a
      business user cannot write a good one blind. Without this screen every
      misconfigured bot is a support ticket you debug from logs.
- [ ] Public URL moves to `/chat/<slug>` (**B2.1**) so link recipients cannot
      enumerate tenants by incrementing an integer.

---

## Cross-cutting, do not defer to a "hardening phase"

- [ ] Orchestration moves off the consumer onto a worker (**B9**). A turn is now
      seconds of model latency; this is also what makes multi-worker deployment
      possible at all.
- [ ] Stream the final answer; emit `tool_started` events keyed off each tool's
      own description. Perceived latency is most of the UX here.
- [ ] Tool results wrapped in an explicit data envelope, with the system prompt
      stating tool output is data and never instruction (**B6**). Enforce the
      part that holds: no tool result can change tool availability, tenancy
      binding, or confirmation state.
- [ ] Keep `WORKFLOW.md` Part C phase status and this file in sync as phases land.
- [ ] Keep **Part E** (onboarding playbook) true as the schema moves — it is what
      the Phase 4 screens are built against and what you show a new company.

---

## Deferred

- [-] `sql_readonly` adapter (**B3**) — highest value, highest risk. Past v1.
- [-] Cross-encoder reranker (D5) — ship RRF, measure with the B4 harness,
      revisit with data.
- [-] Per-source physical tables instead of JSONB (D2) — the adapter seam exists
      so one large tenant can migrate later without touching the compiler, the
      validator, or the model.
