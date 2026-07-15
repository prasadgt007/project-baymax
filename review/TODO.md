# Project Baymax — Issue TODO

Every issue found in the review, tagged by **priority** (P0 = fix before exposure, P1 = correctness/
integrity, P2 = quality/DX) and **area** (backend / frontend / agents / db / skills / docs).
Each item cites the source finding. See `REPORT.md` for detail and `IMPLEMENTATION_PLAN.md` for
sequencing.

## P0 — Security / must-fix before any exposure

- [ ] `[backend]` No authentication on any endpoint; client-supplied `patient_id`/`user_role` are trusted → IDOR + privilege self-elevation. Introduce Supabase Auth + JWT; derive identity server-side. (`server.py:340,406,400`; `api.js:29-31,113`)
- [ ] `[backend]` `/api/brief/{id}` `user_role` query param **defaults to `"hospital_employee"`** → endpoint open to anyone. Verified live: `GET /api/brief/P001` (no param) → 200. (`server.py:400`)
- [ ] `[backend]` Role-spoof upload bypass: patient → 403 but same caller with `user_role=hospital_employee` → 200. Verified live. (`server.py:340`)
- [ ] `[backend/agents]` Staff-only brief **leaks into the patient-facing `response` text** after booking even though `doctor_brief` field is stripped. Verified live. (`server.py:314-316`; `tools.py:213-245`)
- [ ] `[db]` RLS is a no-op: enabled with **zero policies**, app connects as DB owner (RLS-exempt). Add policies + least-privilege role + `FORCE ROW LEVEL SECURITY`. (`db/supabase_schema.sql:40-41`; `db/migration_patient_documents.sql:37`; `db/migration_slots.sql:23`; `.env:16`)
- [ ] `[backend]` `book_slot` accepts a client-supplied `patient_id` → can book in another patient's name. (`database_mcp_server.py:449`)
- [ ] `[backend]` Owner DB URI forwarded into MCP subprocess on every call (`env=dict(os.environ)`); no least-privilege split. (`mcp_client.py:37`)
- [ ] `[backend]` Conversation memory keyed only by `patient_id:user_role` → callers sharing an id share state. (`server.py:185`)
- [ ] `[db/backend]` **Rotate all live secrets** in `.env` (NVIDIA, LangChain, Composio, Supabase pw `REDACTED`, ngrok). (`.env:2,7,11,16,20`)
- [ ] `[docs]` Remove tracked `transcript_matches.txt` (leaks local paths/env); gitignore it. (repo root)

## P1 — Correctness / integrity

- [ ] `[agents]` RAG prompt-injection: untrusted doc text is concatenated into the **system prompt** and returned via tools unsanitized. Channel demonstrated live. Isolate retrieved content as non-authoritative data. (`nodes.py:71-78`; `tools.py:56-71`)
- [ ] `[agents]` Triage follow-up cap **not enforced** — prose only; live test skipped the follow-up entirely. Add a state counter + code gate. (`skills.md:37`; `models.py:38-79`)
- [ ] `[agents]` Remedy safety ignores condition conflicts — recommended ibuprofen (NSAID) to a hypertensive patient. Guard conditions, not just allergies/meds. (`skills.md:41,85`)
- [ ] `[backend]` `risk_flag` hard-coded `False` everywhere; no real risk signal reaches the UI. Emit structured severity. (`server.py:320`; `tools.py:239`; `server.py:436`)
- [ ] `[db]` `hospital_slots.doctor_name` schema drift: code reads it but `db/migration_slots.sql` omits it (only `setup_hospital_slots.py` adds it). Migration-only setup breaks slot queries. (`database_mcp_server.py:406,418,501`; `db/migration_slots.sql:7-13`; `setup_hospital_slots.py:54`)
- [ ] `[backend/agents]` State is in-memory (`MemorySaver` + `_session_cache` dict) → lost on restart, no horizontal scaling; `/api/chat` degrades if `initialize_session` didn't run on the same process. Move to `PostgresSaver` + durable cache. (`graph.py:42`; `server.py:81`)

## P2 — Quality / DX / performance

- [ ] `[docs]` `README.md` is empty (0 bytes) though `pyproject.toml:5` points to it. Write real setup/run docs. (`README.md`)
- [ ] `[docs]` `docs/workflow.md` + `docs/workflow.mmd` describe a supervisor/multi-agent graph that no longer exists. Delete or rewrite to match the single-DeepAgent reality. (`docs/workflow.md`)
- [ ] `[backend]` Model-name drift: docstrings say "Llama 3.3 70B", code runs `meta/llama-3.1-70b-instruct`. Align or upgrade. (`nodes.py:8,26,98` vs `:27`)
- [ ] `[agents]` Dead code: `baymax/utils.py` (`load_skills`/`get_skill`) unused; `tools.py:11-17` docstring says 5 tools but 7 are returned. (`baymax/utils.py`; `tools.py:11-17`)
- [ ] `[backend]` Composio deps + env vars unused (only `test_composio.py`). Wire in or remove `composio-*` and `COMPOSIO_*`. (`pyproject.toml:8-9`; `.env:11-14`; `test_composio.py`)
- [ ] `[backend]` MCP subprocess spawned per call (fresh process + stdio + `asyncio.run` each time). Reuse a connection/pool. (`mcp_client.py:31-38`)
- [ ] `[backend/agents]` Response hygiene: agent leaks the word "slot_id" to users (strip regex only catches `slot_id:` with colon); slot labels render trailing `" - "` when `doctor_name` empty. (`nodes.py:164-170`)
- [ ] `[backend]` Greeting mentions only `conditions[0]`; P001's Asthma was dropped. List all chronic conditions. (`server.py:266`)
- [ ] `[db]` Seed drift: `db/supabase_schema.sql:44-48` seeds John Doe/Jane Smith; live DB has Chester V/John Doe. Reconcile or mark seeds illustrative. (`db/supabase_schema.sql:44-48`)
- [ ] `[skills]` `supabase` skill trigger over-broad ("ANY Supabase task", JS/SSR frameworks unused here) + remote-changelog fetch mandate. Tighten. (`.agents/skills/supabase/SKILL.md:3,17`)
- [ ] `[skills]` `supabase` and `supabase-postgres-best-practices` overlap on DB/pgvector triggers; the latter recommends `ENABLE ROW LEVEL SECURITY` with no policy. Consolidate; fix RLS guidance. (`.agents/skills/supabase-postgres-best-practices/SKILL.md:91-96`)
- [x] `[skills]` `ui-ux-pro-max`: broken paths / `python3` on Windows / contradictory counts. **Removed 2026-07-16** (unused, not wired into runtime).
- [ ] `[frontend]` Entire app in one 943-line `App.jsx`; consider splitting components for maintainability. (`frontend/src/App.jsx`)

## Frontend 3D / workshop enhancements (deferred — planned)

Goal: replace the placeholder blob with the intended visual — a rotating **hub-and-spoke neural
network** background with **glowing nodes** and a **camera zoom on login**, smooth on laptop &
mobile. Skills to guide this are in place: `r3f-3d-experience`, `web-animation-design`,
`playwright-frontend-testing`.

- [ ] `[frontend]` **Extract `<Scene>` into its own component** (`frontend/src/components/Scene.jsx`), mounted once at the app root, driven by props (`phase`, `mouse`). De-risks everything below. (P1 — do first) (`frontend/src/App.jsx:101-112,425`)
- [ ] `[frontend]` **Build the hub-and-spoke neural-network background**: instanced glowing nodes (`<Instances>`) + line spokes (`<Line>`/`LineSegments`) + slow rotation, replacing `HeroBlob`. (P2) (`frontend/src/App.jsx:44-99`)
- [ ] `[frontend]` **Add node glow via bloom**: wire the already-installed `@react-three/postprocessing` `<EffectComposer><Bloom/>`, gated down/off on low-end mobile. (P2)
- [ ] `[frontend]` **Login-triggered camera zoom**: prop-driven camera lerp in `useFrame` keyed off `phase` (login → chat/dashboard); no Canvas remount. (P2)
- [ ] `[frontend]` **Mobile performance pass**: `dpr={[1,2]}`, reduce sphere/segment counts (currently 128×128) and node counts on small screens, respect `prefers-reduced-motion`. (P2)
- [ ] `[frontend]` **Install Playwright + first mobile frame-rate test** (`npm i -D @playwright/test`; config + frame-cadence probe per the `playwright-frontend-testing` skill). (P2)
