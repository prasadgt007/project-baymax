# Project Baymax — Development Journal

A running record of how Baymax has evolved: what changed, when, and **why**. This is the
"story of the build" — meant to be referenced when preparing workshop material and to keep
context on the decisions behind the code.

> **How to use this file:** append a dated entry every time we make a meaningful change.
> Keep entries short: *what changed* + *why*. Newest entries at the top of the "Change Log"
> section. This is a narrative journal, not an auto-generated changelog.

---

## Project at a glance

- **Purpose:** an AI healthcare companion ("Baymax") that greets patients with context, triages
  symptoms, answers questions about their medical records (RAG), and schedules doctor
  appointments — with a separate view for hospital staff.
- **Workshop goal:** demonstrate **LangChain, LangGraph, LangSmith, and DeepAgents** working
  together, show how **Agent Skills** are used, and model clean, systematic development.
- **Stack:** FastAPI + LangGraph (DeepAgents) backend · MCP stdio server over Supabase
  (Postgres + pgvector) · NVIDIA AI Endpoints (Llama 3.1 70B chat, `nv-embedqa-e5-v5`
  embeddings) · React + Vite + Tailwind + Three.js frontend · Composio (Google Calendar) ·
  ngrok for sharing.
- **Design choice (intentional for the demo):** RAG runs on **every** chat query rather than
  relying on caching/short-cuts — simplicity and a clear teaching story were preferred over
  performance for the workshop.

---

## Milestone history (from git history)

| Date | Commit | Milestone |
|---|---|---|
| 2026-06-23 | `b15014b` | Initial commit — multi-agent healthcare assistant (supervisor + symptom/history/scheduling + compliance/scope agents). |
| 2026-06-25 | `fbbdeff` | Connected frontend↔backend, integrated Supabase DB, fixed Windows asyncio loop conflicts. |
| 2026-06-26 | `f927f39` | 3D "Guardnet" aesthetic, single-file UI, ngrok tunnel sharing. |
| 2026-06-29 | `3870342` | Cleanup of obsolete scripts; project restructure. |
| 2026-07-14 | `4d9c9e6` | **Architecture migration:** replaced the supervisor + sub-agents with a single **DeepAgent**; DB-driven scheduling and slot management. |

### Why the architecture changed (2026-07-14)
The original design was an explicit multi-agent graph: a **supervisor** routed each query to a
**Symptom** agent (triage), a **History** agent (RAG), and a **Scheduling** agent, plus a
**Compliance** agent (only appended a disclaimer) and a **Scope** classifier (in-scope vs
out-of-scope). In practice it **hallucinated and routed inaccurately**, and several "agents"
(compliance, scope) were doing trivial work that didn't justify a full LLM agent. To get better
routing, the supervisor was replaced with a single **DeepAgent** that handles routing, triage,
RAG, and scheduling in one ReAct loop. This fixed accuracy but **flattened the multi-agent
structure** — the result no longer resembles the intended multi-agent design, which is an open
design question (see "Open questions" below).

---

## Decisions made (2026-07-16)

- **Architecture:** **keep the single flat DeepAgent** for now. A principled multi-agent redesign
  (DeepAgents native sub-agents for History/RAG + Scheduling; compliance as a node, scope as a
  prompt rule) was discussed and **deferred** — explicitly *not* the failed supervisor design.
- **Doctor brief:** **keep it, adaptive + staff-only** (done — see change log).

<!-- superseded notes kept for context -->
### (superseded) Open questions

- **Architecture:** keep the single DeepAgent, or reintroduce a *principled* multi-agent design
  (DeepAgents native sub-agents for bounded, tool-heavy tasks like History/RAG and Scheduling;
  keep Compliance as a deterministic node and Scope as a prompt rule — i.e. don't make trivial
  steps into agents). **TBD with owner.**
- **Doctor brief:** originally generated on every booking. When a patient books without
  discussing symptoms, the brief is just history. Keep (make it adaptive: "Patient Summary" vs
  "Pre-Consultation Brief"), or remove? **TBD with owner.**

---

## Known issues (as of 2026-07-16)

- [x] Triage skipped follow-up questions and jumped straight to remedies. **(fixed)**
- [x] Slot IDs (UUIDs) leaked into the patient-facing chat. **(fixed)**
- [x] Booking didn't create a Google Calendar event via Composio. **(fixed)**
- [x] Doctor brief leaked into the patient chat. **(fixed)**
- [ ] NSAID-for-hypertension caution not reliably honored by the 70B model (needs a rules layer / stronger model).
- [ ] Booking by *typing* a time (vs clicking a slot chip) can still confuse slot-ID handling.
- [ ] [deferred — demo] No authentication/login yet (Supabase Auth planned).
- [ ] [deferred — demo] Latency (per-call MCP subprocess; RAG every query is intentional for the demo).

---

## Change Log (newest first)

<!-- Add new dated entries here, newest at the top. Format:
### YYYY-MM-DD — short title
- **What:** ...
- **Why:** ...
- **Files:** ...
-->

### 2026-07-16 — Added `workshop/` prep materials
- **What:** created a `workshop/` folder with presenter-facing docs: `README.md` (index),
  `architecture-single-deepagent-vs-multi-agent.md` (why we moved off the multi-agent design —
  mis-routing, trivial agents, stacked latency — to a single DeepAgent, plus the nuance of when
  sub-agents are still worth it), and `rag-supabase-pgvector-and-auth.md` (how RAG works with
  Supabase + pgvector, the data model/query flow, and how Supabase Auth + RLS + Storage extend it).
- **Why:** owner is preparing to present this project as a workshop use case next week
  (LangChain/LangGraph/LangSmith/DeepAgents + skills); wanted the *why* behind the decisions
  documented as reference material.
- **Note:** docs describe the system as built and clearly label roadmap items (e.g. auth is not yet
  implemented; RLS enabled but unpoliced) so the talk stays honest.
- **Files:** `workshop/README.md`, `workshop/architecture-single-deepagent-vs-multi-agent.md`,
  `workshop/rag-supabase-pgvector-and-auth.md`.

### 2026-07-16 — Removed `ui-ux-pro-max` skill; queued frontend 3D work
- **What:** deleted the `ui-ux-pro-max` skill (`.agents/skills/ui-ux-pro-max/`, ~644K: SKILL.md +
  3 scripts + 11 CSVs). Added the frontend 3D enhancement tasks (Scene extraction, neural-network
  background, bloom glow, login-zoom, mobile perf, Playwright install) to `review/TODO.md` under a
  new "Frontend 3D / workshop enhancements" section, deferred per owner.
- **Why:** the skill was unused (not wired into the runtime) and low-quality (broken paths,
  `python3` on Windows, self-contradictory inventory) per the review; owner approved removal.
  Frontend build work is deferred to focus elsewhere for now.
- **Verified:** no code references it — only the `review/*` docs mentioned it as a finding.
- **Files:** removed `.agents/skills/ui-ux-pro-max/`; updated `review/TODO.md`.
- **Remaining skills:** `supabase`, `supabase-postgres-best-practices`, `r3f-3d-experience`,
  `web-animation-design`, `playwright-frontend-testing`.

### 2026-07-16 — Added frontend Agent Skills (R3F, animation, Playwright)
- **What:** authored three project skills under `.agents/skills/` to guide frontend work:
  - `r3f-3d-experience` — React Three Fiber patterns for the 3D background/camera (re-render &
    disposal footguns, instancing for many nodes, bloom for glow, prop-driven camera zoom, mobile
    DPR clamping). Also carries the "extract Scene into its own component, mounted once" guidance.
  - `web-animation-design` — Framer Motion patterns (gentle springs, `AnimatePresence`, reduced
    motion, staggering) for chat bubbles and phase transitions.
  - `playwright-frontend-testing` — e2e + mobile-viewport + frame-cadence testing (Playwright not
    yet installed; skill documents setup).
- **Why:** owner wants to enhance the frontend toward the spec (rotating hub-and-spoke neural
  network background with glowing nodes + login-triggered camera zoom, smooth on laptop & mobile).
- **Analysis note:** confirmed the frontend is **React Three Fiber**, not vanilla Three.js
  (`@react-three/fiber`/`drei`/`postprocessing` in use) — so the R3F skill applies. Deliberately
  did **not** add a separate "Web3D integration" skill: the real fix there is structural (extract
  the inline `<Scene>` from the 943-line `App.jsx`), folded into the R3F skill instead.
- **Current gap:** the background is still the placeholder `HeroBlob` (distorted spheres), not the
  intended neural network; `@react-three/postprocessing` is installed but unused; there's no
  login-zoom yet. These are the next build tasks the skills support.
- **Files:** `.agents/skills/{r3f-3d-experience,web-animation-design,playwright-frontend-testing}/SKILL.md`.

### 2026-07-16 — Calendar sync on cancel/reschedule
- **What:** cancelling (and therefore rescheduling) now **deletes the Google Calendar event**, so
  the calendar stays in sync. Previously cancel only touched Supabase, so a reschedule left the old
  event AND added the new one → two events. Now each booking's calendar `event_id` is stored on the
  slot, and cancel deletes that event.
- **How:**
  - New `hospital_slots.calendar_event_id` column (added to live DB + `db/migration_slots.sql` +
    `setup_hospital_slots.py`; also backfilled `doctor_name` into the migration to fix earlier drift).
  - `calendar_client.create_appointment_event` now returns the `event_id`; new
    `calendar_client.delete_calendar_event()`.
  - New MCP tool `set_slot_calendar_event(slot_id, event_id)` + `set_slot_calendar_event_mcp`
    wrapper; `cancel_slot` now `RETURNING calendar_event_id`.
  - `book_appointment` persists the event_id after creating the event; `cancel_appointment`
    deletes the event after freeing the slot (best-effort — never blocks the DB op).
- **Why:** reported after a reschedule showed two events on the calendar.
- **Files:** `baymax/calendar_client.py`, `baymax/tools.py`, `baymax/mcp_client.py`,
  `database_mcp_server.py`, `db/migration_slots.sql`, `setup_hospital_slots.py`.
- **Verified:** book → event created + id stored; cancel → slot freed + event deleted (confirmed
  gone from calendar); full chat reschedule 9 AM→11 AM → DB shows 1 booking, calendar shows exactly
  1 event (11 AM), old event removed.

### 2026-07-16 — Cancellation fix (resilient slot resolution)
- **What:** cancelling an appointment failed with *"appointment not found or does not belong to
  this patient."* Root cause: tool outputs aren't persisted between turns and slot IDs are
  stripped from the visible chat, so on a later "cancel the 3pm one" turn the agent had no real
  UUID and passed a placeholder string (`"the slot_id of the 3pm appointment"`) → the DB `WHERE`
  matched nothing. Fixed by making `cancel_appointment` **resilient**: it now accepts an
  `appointment_time` hint (e.g. "3pm") and/or a `slot_id`, fetches the patient's real bookings,
  and resolves the target by exact UUID → time match → single-appointment fallback. A placeholder
  like "the slot_id of the 3pm appointment" still resolves because the time is extracted from it.
- **Why:** reported during live testing (see screenshot). Prompt-only guidance wasn't reliable —
  the LLM keeps fumbling UUIDs — so the robustness now lives in the tool.
- **Files:** `baymax/tools.py` (new `_time_hint_matches` helper + rewritten `cancel_appointment`),
  `baymax/skills.md` (cancellation/reschedule steps + tool description pass `appointment_time`).
- **Verified:** "cancel the 3pm one" → slot freed in Supabase, 11 AM booking untouched, no UUID
  errors.
- **Related gap (open):** cancelling frees the DB slot but does **not** delete the Google Calendar
  event created at booking (cancel touches only Supabase). To fix we'd store the calendar
  `event_id` on the slot at booking time and delete it on cancel — worth doing next if calendar
  parity matters for the demo. Same latent UUID-placeholder issue can still affect booking-by-typed-time
  (chips are reliable).

### 2026-07-16 — Live-test fixes: greeting, slot-chip display; calendar/DB confirmed working
- **What:**
  - **Greetings no longer trigger tools.** Added CRITICAL RULE #3 in `skills.md`: on "hi"/small
    talk, reply with a short greeting and call no tools. (Bug: typing "Hi" made the agent dump the
    patient's appointment list.)
  - **Slot chips no longer show the raw `slot_id`.** Frontend `handleSend` now takes a separate
    display string; the hidden `<!-- slot_id: ... -->` marker is still sent to the backend but
    stripped from the patient's chat bubble (`frontend/src/App.jsx`).
  - **Verified Composio + Supabase are actually working.** A booking persists to `hospital_slots`
    (`is_booked=true`, correct patient) *and* creates a Google Calendar event. The reason events
    "don't show up" for the owner: they are created on the **Composio-connected Google account
    (a separate demo Google account)**, not the owner's own work calendar.
- **Why:** issues reported during the owner's first live run-through.
- **Files:** `baymax/skills.md`, `frontend/src/App.jsx`.
- **Notes / still open:** (1) the compliance disclaimer still appends to plain greetings when the
  text mentions "symptom" — cosmetic; (2) NVIDIA rate limits: none observed in the session logs,
  but the DeepAgent makes several NVIDIA calls per turn (booking is the heaviest), so the free-tier
  RPM limit *could* be hit under rapid use — worth a retry/backoff or tier bump later.

### 2026-07-16 — Doctor brief: adaptive + staff-only (leak fixed)
- **What:** the pre-consultation brief is now **adaptive** — a full "Pre-Consultation Brief"
  when symptoms were discussed (agent passes a `symptoms_summary`), or a lighter
  "Patient Summary" (history/meds/allergies) when the patient only booked. The brief is now
  **staff-only**: it is captured into the `doctor_brief` field (shown to hospital employees)
  and stripped from the patient-facing chat text, so it no longer leaks to patients.
- **Why:** owner decided to keep the brief but make it adaptive and confidential; previously the
  full brief was narrated back to the patient after every booking.
- **Files:** `baymax/briefs.py` (adaptive title + reason/summary section + conditional risk),
  `baymax/tools.py` (`generate_brief_for_doctor` takes `symptoms_summary`), `baymax/nodes.py`
  (capture "Patient Summary" too; strip the brief block from patient text), `baymax/skills.md`
  (instruct: pass a summary; never show the brief to the patient).
- **Verified:** patient booking → clean confirmation, no brief, `doctor_brief=None`; staff
  `/api/brief` → adaptive "Patient Summary"; Google Calendar event still created.
- **Design note:** owner chose to **keep the single flat DeepAgent** for now (no sub-agent
  refactor) — so this was done within the current architecture.

### 2026-07-16 — Bug-fix pass: triage follow-ups, slot-ID leak, Google Calendar
- **What:**
  - **Triage now enforces a follow-up.** On a first symptom mention, Baymax asks 1–2 follow-up
    questions and withholds remedies until the patient answers (two-stage flow). Added a
    top-of-prompt "CRITICAL RULES" block and a few-shot example — a mid-prompt prose rule alone
    was not reliably followed by Llama 3.1 70B.
  - **Slot IDs no longer leak to patients.** Prompt rule + cleaned tool return strings
    (`book_appointment`/`cancel_appointment` no longer echo the UUID) + a stronger UUID/`slot_id`
    scrub in the node's final-text cleanup. Slots now render as a plain numbered list; the UI
    still receives slot objects (with IDs) for the chips.
  - **Google Calendar integration wired up.** Booking a slot now also creates a Google Calendar
    event via Composio (`GOOGLECALENDAR_CREATE_EVENT`). New `baymax/calendar_client.py`;
    `book_slot` now returns `slot_datetime`/`duration_minutes`/`doctor_name` (via SQL `RETURNING`)
    so the event has real time/doctor details. Best-effort: a calendar failure never blocks the
    DB booking. Verified live (event created + confirmed on the connected calendar).
- **Why:** these were the three demo-blocking bugs — Baymax jumped straight to remedies, exposed
  raw UUIDs in chat, and booked only in the DB (not on Google Calendar).
- **Files:** `baymax/skills.md`, `baymax/tools.py`, `baymax/nodes.py`, `baymax/calendar_client.py`
  (new), `database_mcp_server.py`.
- **Known follow-ups:** (1) the NSAID-for-hypertension safety caution is in the prompt but the
  70B model doesn't always honor it — needs a rules layer or stronger model for reliability;
  (2) booking by *typing* a time (vs clicking a chip) can still confuse ID handling — prompt was
  hardened to require the exact UUID, chip flow is the reliable path; (3) the doctor-brief still
  renders inside the patient chat after booking — pending the keep/remove decision.

### 2026-07-16 — Added this development journal + `/review` audit
- **What:** created `docs/PROJECT_JOURNAL.md` (this file) and a `/review` folder with a full
  code+security review (REPORT, architecture diagrams, implementation plan, TODO).
- **Why:** owner wants a living record of the project's evolution for workshop prep, and a
  baseline assessment before making changes.
- **Files:** `docs/PROJECT_JOURNAL.md`, `review/*`.
