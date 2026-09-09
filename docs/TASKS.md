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

## Phase 1 — The loop  ▶ next

Goal: **feature parity with today, plus multi-turn follow-ups**, with routing
moved from the consumer into the model. Two tools only.

> **Protect this phase from scope creep.** No structured data, no actions, no
> config UI. Two tools is enough to prove the loop.

### 1.1 Decide D1 before writing any migration
- [ ] **Confirm the `chatbots` table lands now, not later.** (WORKFLOW.md → Open
      decisions, D1.) Everything below assumes yes. If the answer is no, stop —
      half this phase changes shape.
      *Done when:* the decision is written into the D1 row of WORKFLOW.md.

### 1.2 Schema
- [ ] New Django app `registry`. Models: `Chatbot`, `Tool`.
      `Chatbot`: company FK, `slug` (unique, public URL key), name,
      persona_prompt, model, temperature, locale, is_active, `policy` JSONB.
      `Tool`: chatbot FK, name, description, `tool_type`, `configuration` JSONB,
      `input_schema` JSONB, schema_version, is_active, requires_confirmation,
      rate_limit JSONB, unique (chatbot, name). Schema per **B2.1 / B2.4**.
- [ ] Data migration: one `Chatbot` per existing `Company`, slug from the
      company name, plus its two preset `Tool` rows.
      *Done when:* every existing company keeps working with no client change.
- [ ] Extend `chat.ChatSession`: `chatbot` FK, `visitor_id`, `channel`,
      `working_set` JSONB, `summary`, `summary_upto_message_id`. (**B2.5**)
- [ ] Extend `chat.ChatMessage`: `role` (`user`/`assistant`/`tool`/`system`),
      `tool_call_id`, `tool_name`, `tool_args`, `tool_result`,
      `tool_result_summary`, `tokens`, `latency_ms`. (**B2.5**)
      *Backfill:* existing rows → `role='user'` where `sent_by_us=False`, else
      `role='assistant'`.
- [ ] New `tool_executions` table (**B2.5**). Written by G10 from day one, even
      though only two tools exist.

### 1.3 Provider adapter (D4)
- [ ] `orchestration/providers/` — a thin seam: declarations in, tool calls out,
      streamed text out. Gemini implementation only.
      *Done when:* nothing outside this package imports `google.genai`.
      *Explicitly not:* a framework. Target a day's work.

### 1.4 The orchestrator
- [ ] New app `orchestration`. `run_turn(session, message) -> events`
      implementing the lifecycle in **B5**: resolve → **live-agent check first**
      → assemble context → model → tool calls → validate → execute → loop.
- [ ] Budgets from **B5** read out of `chatbots.policy`, with the defaults in
      that table. A tool timeout returns a *result*, never raises.
- [ ] Context assembly per **B7**: system prompt + persona, rolling summary,
      last 8 turns verbatim, full tool JSON for the last 2 turns and
      `tool_result_summary` beyond that.
      *Do not* implement server-side filter merging. The log is the state.
- [ ] Gates **G1, G2, G3, G7, G9, G10** wired now (G4/G5/G6 arrive with
      structured data in Phase 2, G8 with actions in Phase 3). G1 is
      non-negotiable: tenant identity comes from the session, and a
      model-supplied tenant id is *ignored*, not validated.

### 1.5 The two tools
- [ ] `search_knowledge` — wraps today's retrieval. Fixed schema `{query, top_k?}`.
      Returns `{"chunks": [], "reason": "no_relevant_content"}` when nothing
      clears the gate (**B4**) — an empty result is a signal, not a failure.
- [ ] `request_human_agent` — wraps the existing `flag_agent_needed`.
      Schema `{reason, summary?}`.
- [ ] **Server-side handoff safety net, independent of the model** (**B5**):
      N consecutive turns with no successful tool result, an explicit
      "talk to a human" match, or budget exhaustion forces handoff.
      *Done when:* a deliberately looping model still reaches an agent.

### 1.6 Reduce the consumer to transport
- [ ] `questions/consumers.py :: ChatConsumer.receive()` becomes: parse frame →
      resolve session → hand to the orchestrator → stream events back. All
      branching in it today disappears.
      *Done when:* the file contains no threshold comparison and no LLM call.
- [ ] Keep the existing outbound frame shape (`type:"answer"`, `session_id`,
      `session_token`, …) so `TEMPFRONTEND` needs no change in this phase.
      Add `type:"tool_started"` for the "checking…" indicator (**B9**).

### 1.7 Prove it
- [ ] Test: a greeting produces **no** knowledge search.
      *(Today it triggers a vector scan and can escalate — this is L1 dying.)*
- [ ] Test: a follow-up turn resolves against prior context.
      *(Today structurally impossible — this is L2 dying.)*
- [ ] Test: cross-tenant tool argument is ignored, not honoured (**G1**).
- [ ] Test: budget exhaustion degrades to a final answer or handoff, never hangs.
- [ ] `tests/test_retrieval.py` still passes unchanged.

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
