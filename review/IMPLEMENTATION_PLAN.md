# Project Baymax — Implementation Plan

Prioritized, phased remediation for the findings in `REPORT.md`. Effort is rough
(S ≈ <½ day, M ≈ 1–2 days, L ≈ 3–5 days) for one engineer familiar with the stack.

Guiding principle: **the app's happy path works — do not rewrite it.** The single flat DeepAgent
is fine. The work is almost entirely security, state durability, and cleanup. Fix the trust
boundary first; everything else is secondary.

---

## Phase 0 — Immediate (do before anything is exposed) · ~½ day

| # | Item | Why | Effort |
|---|---|---|---|
| 0.1 | **Rotate all secrets in `.env`** (NVIDIA, LangChain, Composio, Supabase DB password, ngrok). | They are live and have been read out of the working tree. Weak DB password (`REDACTED`). | S |
| 0.2 | **Stop exposing via ngrok** until Phase 1 lands. | No auth today → public tunnel = full PHI exposure. | S |
| 0.3 | **Remove `transcript_matches.txt` from the repo** (and `write_nodes.txt` if not needed); add to `.gitignore`. | Tracked file leaks local paths/env. | S |

---

## Phase 1 — Security / access control (P0) · ~1 week

The core problem: **the client declares its own identity and role.** Fix the trust boundary and
most vulnerabilities close at once.

| # | Item | Rationale | Effort |
|---|---|---|---|
| 1.1 | **Introduce real authentication.** Use Supabase Auth; frontend sends a JWT (`Authorization: Bearer`) instead of `patient_id`/`user_role` in the body. | Removes IDOR + role self-elevation. Foundation for everything below. | L |
| 1.2 | **Derive `patient_id` and `role` server-side from the verified JWT**, never from the request. Add FastAPI middleware/dependency that rejects unauthenticated calls. Delete `user_role`/`patient_id` from `ChatRequest`/`SessionRequest` and the `/api/brief` query param default (`server.py:95,116,400`). | Kills the spoof/IDOR class entirely. Especially fixes the open-by-default brief. | M |
| 1.3 | **Write and test RLS policies** on `patients`, `patient_interactions`, `patient_documents`, `hospital_slots` (`patient_id = auth.uid()` for patients; role claim for staff), and switch the app to a **least-privilege** DB role. Add `FORCE ROW LEVEL SECURITY`. | Defense in depth so the DB enforces scoping even if app code has a bug. Today RLS is a no-op (owner connection + no policies). | M |
| 1.4 | **Stop leaking the brief into patient responses.** The brief must never be narrated in the patient-facing `response` — either don't call `generate_brief_for_doctor` in patient sessions, or post-filter the brief block out of `final_response` for patients (mirror the field-strip at `server.py:314-316`). | The "patient-hidden" guarantee is currently broken (verified live). | S |
| 1.5 | **Do not put the owner DB URI on the request path.** Give the MCP subprocess a scoped credential; stop forwarding the full env (`mcp_client.py:37`). | Limits blast radius of any injection/RCE foothold. | S |

**Exit criteria:** an unauthenticated request gets 401; a patient JWT cannot read another
patient's data even by tampering; `/api/brief` requires a staff JWT; RLS blocks a cross-patient
query at the DB even with a forged app-layer id.

---

## Phase 2 — Correctness & integrity (P1) · ~1 week

| # | Item | Rationale | Effort |
|---|---|---|---|
| 2.1 | **Mitigate RAG prompt injection.** Stop concatenating raw doc text into the *system* prompt (`nodes.py:71-78`); pass retrieved content only as clearly-delimited "reference data, not instructions" in the user/tool channel, and add an instruction that document text is never authoritative. | Untrusted uploaded text currently enters the system prompt; injection channel demonstrated. | M |
| 2.2 | **Enforce the triage follow-up cap in state.** Add a `triage_followups` counter to `BaymaxState` and gate follow-up questions in code, not just prose (`skills.md:37`). | The described 1-follow-up cap is not enforced; behavior is arbitrary. | M |
| 2.3 | **Reconcile the `hospital_slots` schema.** Make `db/migration_slots.sql` and `setup_hospital_slots.py` agree (add `doctor_name` to the migration), and backfill/require `doctor_name` so slot labels aren't `" - "`. | Running the `db/` migration alone breaks slot queries; empty doctor names surface in the UI. | S |
| 2.4 | **Produce a real `risk_flag`.** Have the agent emit a structured severity signal (e.g. via a tool or structured output) and surface it instead of the hard-coded `False` (`server.py:320`). | The safety-critical signal is currently dead. | M |
| 2.5 | **Add condition-aware remedy safety.** Extend the prompt/guardrails so remedies also avoid condition conflicts (e.g. NSAIDs for hypertensive patients), not just allergies/meds. | Live test recommended ibuprofen to a hypertensive patient. | S |
| 2.6 | **Durable state: replace `MemorySaver` with `PostgresSaver`** and move `_session_cache` into the DB/checkpointer. | In-memory state is lost on restart and blocks horizontal scaling. | M |

---

## Phase 3 — Quality, DX, performance (P2) · ~3–4 days

| # | Item | Rationale | Effort |
|---|---|---|---|
| 3.1 | **Write a real `README.md`** (setup, env vars, run backend/frontend, seed DB). | It's empty; onboarding is code-archaeology today. | S |
| 3.2 | **Delete stale docs & dead code:** `docs/workflow.md`/`.mmd` (supervisor fiction), `baymax/utils.py`, fix `tools.py:11-17` docstring (5→7 tools). | Docs actively mislead; dead code confuses. | S |
| 3.3 | **Consolidate/repair skills:** merge the two Supabase skills, tighten triggers to this project's stack, fix `ui-ux-pro-max` paths (`skills/`→`.agents/skills/`), `python3`→`python`, and the contradictory inventory counts. | Redundant/over-broad/broken skill defs. | S |
| 3.4 | **Fix model-name drift:** align docstrings (`nodes.py:8,26,98`) with the actual `meta/llama-3.1-70b-instruct`, or upgrade to the intended model. | Docs claim Llama 3.3; code runs 3.1. | S |
| 3.5 | **Decide Composio: wire it in or remove it.** If scheduling should hit Google Calendar, integrate it; otherwise drop `composio-*` deps and the `COMPOSIO_*` env vars. | Dead dependency + misleading setup surface. | S–M |
| 3.6 | **Reuse the MCP connection** instead of spawning a subprocess per call (`mcp_client.py:31-38`) — long-lived client or in-process pool. | Large per-request latency win. | M |
| 3.7 | **Response hygiene:** widen the `slot_id` strip regex (`nodes.py:164-170`) and don't render `" - "` when `doctor_name` is empty. | Internal wording leaks to users. | S |
| 3.8 | **Fix greeting to mention all chronic conditions**, not just `conditions[0]` (`server.py:266`). | Asthma was silently dropped for P001. | S |
| 3.9 | **Reconcile seed data** (`db/supabase_schema.sql:44-48`) with the live DB, or document that seeds are illustrative. | Seed says John Doe/Jane Smith; live DB has Chester V/John Doe. | S |

---

## Sequencing rationale
- **Phase 0** is minutes of work and removes the most acute exposure (live keys, public tunnel).
- **Phase 1** is the spine: once identity/role come from a verified JWT and RLS is real, the
  IDOR, role-spoof, open-brief, and cross-patient issues collapse together. Do it before anything
  else functional.
- **Phase 2** hardens what remains attackable through legitimate access (injection) and fixes the
  safety/correctness signals (risk flag, triage cap, schema).
- **Phase 3** is cleanup that makes the project maintainable and faster but changes no security
  posture.
