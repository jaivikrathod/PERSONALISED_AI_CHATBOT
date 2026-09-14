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

## Phase 2 — Structured data (the universality payoff) ✅ done

Goal: **a real estate bot and an unrelated vertical running the same code**,
differing only by registry rows. This is where B0 preset 2 becomes real.

**Where this phase stands:** shipped in the new `TEMPSERVER/datasources/` app,
pinned by `tests/test_datasources.py`. The acceptance test
(`SecondVerticalTests`) onboards an e-commerce catalogue purely through the
HTTP API and searches it through the orchestrator. Backend only — the screens
that call this API are Phase 4.

Module map: `models.py` (tables) · `types.py` (types, operators, coercion,
inference) · `ingest.py` (upload → records, cardinality) · `warnings.py` (E2
traps) · `declarations.py` (fields → JSON Schema) · `search.py` (compiler,
G4–G7 validator, `records` adapter, result shaping, executor) ·
`publishing.py` (checks, indexes, tool) · `views.py` (API).

### 2.1 Schema ✅ done — `datasources/0001_initial`
- [x] `data_sources`, `data_source_fields`, `data_records`, `data_source_syncs`
      per **B2.3**, plus: `data_sources.company` (tenancy scoping, as every
      other tenant table), `schema_confirmed_at` (the human confirmation),
      `data_source_syncs.filename` / `warnings`.
      `allowed_operators` is `text[]`; `payload` is JSONB (D2).
- [x] GIN `jsonb_path_ops` on `payload`. B-tree expression indexes on exposed
      numeric/date fields are created **at publish** (`ensure_indexes`),
      partial on `data_source_id`, on exactly the expression the adapter
      queries: `((payload ->> 'f')::double precision)` / `(payload ->> 'f')`.
- [x] *Also:* `tool_executions.compiled_query` (`chat/0005`) — the IR is
      "always logged" (B3), there rather than only in log lines.

### 2.2 Ingestion ✅ done
- [x] CSV **and** JSON (`[...]` or `{"records": [...]}`) → `data_records`,
      upsert on `(data_source_id, external_id)`; `mode=replace` soft-deletes
      rows absent from the file. Every run is a `data_source_syncs` row with
      rejected-row reasons. `id_field` auto-picked (`external_id`/`id`/`ref`/
      `sku`/…) and stored in `config`. Synchronous in the request; 20 MB cap.
- [x] Values are **coerced at import** to the field type (blank → key absent,
      uncastable → dropped + reported), so the adapter's casts are safe and
      index-compatible. Changing a field's type re-coerces stored payloads.
- [x] Type inference from a sample → suggested `data_source_fields`
      (headers normalised to identifiers; column names containing phone/
      email/cost/margin/owner/… start **hidden**). *Suggestion, not
      authoritative:* publish requires `confirm-schema`, and importing new
      columns clears the confirmation.
- [x] Cardinality per field; `enum_values` kept while ≤ 50. String fields get
      `equals` (enum) or `ilike` (free text) from it.
- [x] **Fixed filters** in `data_sources.config.fixed_filters`, applied to
      every query, never in the declaration, may target hidden fields.
      *Done when:* "show me sold properties" returns none — ✅
      (`test_the_fixed_filter_means_sold_properties_are_never_shown`).
- [x] **`description` required on every exposed field** at publish, and on
      PATCH of a published source. *Done when:* a source cannot be published
      with a blank description on an exposed field — ✅.
      *Not done:* "with a live example in the UI" — that is the Phase 4 screen.
- [x] Import warnings for the three E2 traps (never blocking): a constant
      category column or a sibling source with ~the same columns (trap 1); an
      exposed numeric column whose median differs ≥ 20× across groups of a
      low-cardinality column (trap 2); values that look like joined levels,
      `Clothing > Ethnic` (trap 3).

### 2.3 Declaration generator ✅ done
- [x] `data_source_fields` → flat JSON Schema per the **B3** table: enum ≤ 50,
      `min_`/`max_` for numbers, `_after`/`_before` for dates, arrays for
      `string_array`, `sort_by` enum, `limit` capped by
      `policy.max_rows_returned`. **One deliberate addition:** numeric fields
      with `equals` allowed also get an exact parameter (`bedrooms`), as the
      B0/E2 examples use. Parameter collisions fail publish.
- [x] Cache: the compiled schema is stored in `tools.input_schema` and read,
      never recompiled, per turn. Invalidation: `refresh_tool` on every
      write to a source or its fields (signals + explicit calls after bulk
      writes), bumping `schema_version` only when the output changed.
      *Not applicable yet:* `action_parameters` (Phase 3).
- [x] No `data_source_id`, operators, field paths or table names in the
      declaration — pinned by `test_the_declaration_is_flat_and_leaks_nothing`.

### 2.4 Compiler, validator, adapter ✅ done — `datasources/search.py`
- [x] Flat parameters → IR via the same `parameter_specs` the declaration is
      built from. The model never emits IR (D3). `advanced_filters` not built.
- [x] **G4** (exposed + filterable; hidden and nonexistent fields get the same
      error), **G5** (`allowed_operators`), **G6** (cast, exact enum match),
      **G7** (filter count, `limit`, offset, 300-char text cap — clamped).
      Rejections reach the model as `invalid_arguments` naming the field and
      the allowed values.
- [x] `records` adapter: `KeyTextTransform` + explicit cast per type; dates as
      ISO text.
- [x] Result shaping: `matched`, `returned`, `truncated`, `rows` (only exposed
      + returned fields, plus `ref`), and on zero results `relaxable_filters`
      by re-running with each filter dropped (≤ 6 re-runs).
      *Done when:* a zero-result query yields a next sentence — ✅.
- [x] `STRUCTURED_SEARCH` executor registered; the source is resolved through
      the turn's chatbot (G1), so a tool row pointing at another tenant's
      source returns `tool_unavailable`.

### 2.5 Prove it ✅ done — `tests/test_datasources.py`
- [x] B0 worked example: *"2BHK in New Ranip, not top floor"* → exact IR → P-101.
- [x] **Acceptance test:** an e-commerce catalogue onboarded via the API alone
      (`SecondVerticalTests`) — no Python, no code change.
- [x] `internal_margin` / `owner_phone` invisible in both directions.
- [x] One conversation crosses `search_properties` → `search_knowledge` →
      `search_properties`.
- [x] The E2 set on one bot, including the city-level rent query returning
      `truncated`.
- [x] Buy and rent in **one** source with `listing_type`; `sale_price` /
      `monthly_rent` separate (an "under 80 lakh" search skips rentals).
- [x] `city` and `locality` both filterable; a city-only query works.

### HTTP API (backend for the Phase 4 screens)
`/api/data-sources/` CRUD · `{id}/import/` · `{id}/fields/` ·
`{id}/confirm-schema/` · `{id}/publish/` · `{id}/unpublish/` ·
`{id}/declaration/` ("what the AI sees") · `{id}/syncs/` ·
`/api/data-source-fields/{id}/` (list/retrieve/PATCH). Admin/Manager only,
scoped to the token's company.

### Carried forward from Phase 2
- Import runs in the request; move it to the Phase 2b background job.
- `is_searchable` / `search_tsv` exist but are not compiled (full-text over
  records). `advanced_filters` (OR-groups) not built.
- The tool description is regenerated from `data_sources.description` on every
  refresh — edit the source, not the tool row, or the edit is overwritten.
- No live-Gemini run; tests use the scripted provider.

---

## Phase 2b — Documents as knowledge ✅ done

Can run parallel with Phase 2; independent of it. This is the "let companies
upload their privacy policy / return policy" half of B0.

**Where this phase stands:** shipped in the new `TEMPSERVER/knowledge/` app,
pinned by `tests/test_knowledge.py`. `search_knowledge` now runs hybrid
retrieval over `knowledge_chunks` (FAQ + documents). Backend only — the
upload/progress screen is Phase 4.

Module map: `models.py` · `extraction.py` (PDF/DOCX/TXT/MD/HTML → blocks) ·
`chunking.py` · `jobs.py` (DB-backed job queue) · `ingest.py` · `faq.py`
(questions → chunks) · `retrieval.py` (hybrid + gate) · `evaluation.py`
(harness) · `views.py` (API) · commands `run_ingestion_worker`,
`evaluate_knowledge`.

- [x] `knowledge_sources`, `knowledge_documents`, `knowledge_chunks` per
      **B2.2** (`knowledge/0001`), plus `ingestion_jobs`. `embed_text`
      separate from `content`; `embedding_model` per chunk; `content_tsv` is a
      Postgres **generated column** over `embed_text` + `content` (english
      config) with GIN; HNSW on `embedding`; one FAQ source per chatbot.
- [x] `questions` → `knowledge_chunks` as `kind='faq'`, `embed_text` =
      question, `content` = answer (`knowledge/0002`, frozen). **`questions`
      stays the authoring surface:** `faq.py` mirrors every save/archive/delete
      by signal and reuses the question's own embedding, so no model runs in
      the request. A bot created later is backfilled.
- [x] Upload + extraction (PDF via `pypdf`, DOCX via `python-docx`, TXT/MD,
      HTML via stdlib) with a SHA-256 `checksum` — re-uploading an unchanged
      file returns `unchanged: true` and queues nothing. Scanned (image-only)
      PDFs fail with a clear message; no OCR. New deps in `requirements.txt`.
- [x] Chunker: heading- and paragraph-aware, never mid-sentence, ~15% overlap,
      metadata `{document_title, section_heading, page}`.
      ⚠️ **Size deviates from this task on purpose:** all-MiniLM-L6-v2 reads
      only 256 wordpiece tokens, so 300–500-token chunks would be embedded from
      their first half. Chunks target ~200 and cap at 240 tokens *including* the
      section heading, which is prefixed to every document chunk so clause
      numbers ("Clause 4.2") are searchable. A single sentence over the cap is
      the only mid-sentence split. Change the constants with the model.
- [x] Ingestion as a **background job with visible progress**: `ingestion_jobs`
      rows (`status`, `done_steps`/`total_steps`, `progress` %, `message`,
      `error`), polled at `/api/ingestion-jobs/`. `INGESTION_MODE`: `thread`
      (default, after commit), `worker` (`manage.py run_ingestion_worker`,
      `SKIP LOCKED`, safe with several workers), `inline` (tests). A failed
      extraction is a failed job, never a crashed worker.
- [x] Hybrid retrieval per **B4**: pgvector top-30 + full-text top-30 (terms
      OR-ed, `to_tsquery('english')`), fused with RRF `Σ 1/(60+rank)`, token
      ceiling `policy.max_context_tokens` (1200).
- [x] Three-signal gate in `chatbots.policy`: `retrieval_floor` (0.32),
      `accept_threshold` (0.40), `margin_rule` (0.15, applied below
      `margin_bypass_score` 0.55). **Plus lexical acceptance:** a query carrying
      a specific token (has a digit, or is all-caps — clause numbers, plan and
      SKU codes) is accepted when a full-text hit contains it, even at low
      cosine. That is what makes "what does clause 4.2 say" work.
      *Interpretation note:* B4's "fused rank-1 in top decile" was not
      implementable without a score distribution to take a decile of; the gate
      keeps the measured cosine threshold instead.
- [x] **Measurement harness** (`knowledge/evaluation.py`,
      `manage.py evaluate_knowledge --chatbot <slug> --fixture <json> [--tune]
      [--target 0.95] [--write]`): precision on the `not` set first, then
      recall; `--tune` grid-searches `accept_threshold` × `margin_rule`.
      Shipped with `tests/fixtures/knowledge_eval.json` (15 FAQs, one policy
      document, 25 answerable + 25 not), and the default gate is pinned against
      it: **precision on `not` = 1.0, recall ≥ 0.8**.
      ⚠️ *Not done:* ~50 labelled questions **per pilot tenant**. The fixture is
      synthetic; run the command on real questions before trusting any value.
- [~] Move embedding out of the request path (**B9**). Document embedding
      runs in the job; FAQ mirroring reuses stored embeddings. Still in a
      request: `POST /api/vectorize/{company_id}/` and the unanswered-inbox
      `resolve` (one question), kept synchronous because the current frontend
      reads their counts from the response. The per-turn *query* embedding is
      inherent to a turn and is cached per process.

### HTTP API (backend for the Phase 4 Knowledge screen)
`/api/knowledge-sources/` (list/create `document`|`text`; `faq` is managed,
`url` rejected until the Phase 3 egress guard) · `{id}/upload/` (multipart,
202 + job) · `{id}/text/` · `{id}/documents/` ·
`/api/knowledge-documents/{id}/` (retrieve/delete) · `/api/ingestion-jobs/`.
Admin/Manager only, scoped to the token's company.

### Carried forward from Phase 2b
- `url` knowledge sources need the B6 egress guard (Phase 3).
- The `search_knowledge` result shape changed from `{question, answer, score}`
  to `{title, content, score, section?, page?}` — the model reads it; the
  socket's `sources[]` frame is unchanged.
- Cross-encoder reranker stays deferred (D5); revisit with harness data.

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
- [ ] Fixed-filter toggle on the field-permissions screen (backend shipped in
      Phase 2: `data_sources.config.fixed_filters`).
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
