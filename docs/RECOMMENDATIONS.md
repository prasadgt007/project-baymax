# Recommendations — Skills, Subagents, Scripts & Workshop Notes

*Compiled 2026-07-17 after cleaning the repo and running a full feature test pass.*

---

## 1. Feature test results (as of this pass)

All core features were exercised against the live app and **work**:

| # | Feature | Result |
|---|---|---|
| 1 | Proactive greeting (name + chronic conditions) | ✅ P001 → "Chester V", Hypertension/Asthma |
| 2 | Triage follow-up (asks before remedies) | ✅ asks a question, withholds remedies |
| 3 | Slot list (no UUID leak) | ✅ clean numbered times; UI still gets slot objects |
| 4 | Booking → Supabase + Google Calendar | ✅ slot booked, event created, `event_id` stored, brief hidden from patient |
| 5 | Cancel → DB + calendar sync | ✅ slot freed, calendar event deleted |
| 6 | RBAC: patient upload blocked / staff allowed | ✅ patient 403, staff 200 |
| 7 | Staff brief (adaptive) | ✅ "Patient Summary" when no symptoms, staff footer present |

**No new functional bugs found.** Two known items remain (both previously documented):
- **No authentication** — `patient_id`/`role` trusted from client; `/api/brief` open by default.
  Deferred (demo). See `review/REPORT.md`.
- **Latency** — see the workshop risk below.

---

## 2. Workshop notes & the one real risk: latency ⚠️

The biggest thing to plan around for a **live** demo is response time. A single turn makes several
sequential model calls, and RAG runs on **every** message; a **booking** turn is the heaviest
(book → generate brief → create calendar event) and can take **2–3 minutes**. During testing, curl
calls to the booking turn timed out purely on latency (the operation still completed server-side).

**Mitigations, cheapest first (pick based on time before the workshop):**
1. **Pre-warm & rehearse.** Do one throwaway booking before presenting (first call is slowest);
   keep the exact demo script tested end-to-end.
2. **Narrate the wait as a feature.** Open **LangSmith** live and show the ReAct loop / tool calls
   happening — turns "it's slow" into "look, it's reasoning and calling tools."
3. **Trim tool calls per turn.** Don't auto-generate the brief on *every* booking during the demo;
   or skip `search_patient_records` on turns that don't need records.
4. **(Later) Reuse the MCP connection** instead of spawning a subprocess per call, and gate RAG to
   only when needed. Biggest structural win; tracked in `review/TODO.md`.

**Demo script that shows the most in the least time (suggested):**
greeting → a symptom ("headache 2 days") → answer the follow-up → "book an appointment" → click a
slot → show the Google Calendar event → "cancel it" → show it disappear. Then switch to **Staff**,
upload a PDF, view the brief.

---

## 3. Agent Skills

**Current:** `supabase`, `supabase-postgres-best-practices`, `r3f-3d-experience`,
`web-animation-design`, `playwright-frontend-testing`.

**Recommendations:**
- ✅ **Keep** the three frontend skills — they're scoped to this project and support the planned 3D
  work.
- 🔧 **Consolidate the two Supabase skills.** They overlap on DB/pgvector triggers and one advises
  enabling RLS without a policy (the footgun behind this project's no-op RLS). Merge into one
  Baymax-tailored skill (Python + psycopg + pgvector + the auth/RLS roadmap).
- ➕ **Consider a `baymax-agent-conventions` skill** — most behavior lives in `baymax/skills.md`
  (the prompt). A short skill documenting "how we edit the prompt / add a tool / keep IDs out of
  patient text" would keep future changes consistent. (Optional.)

> Note: `.agents/` is now tracked in git, so skills are versioned and shareable — good for the
> "using skills" part of the workshop.

---

## 4. Subagents

Two different meanings — both worth a sentence in the talk:

**a) Product sub-agents (DeepAgents).** We deliberately run **one** DeepAgent (see
`workshop/architecture-single-deepagent-vs-multi-agent.md`). If you later want *principled*
sub-agents, the two good candidates are:
- **History/RAG researcher** — runs several searches and returns one clean summary, keeping the
  main context small (context isolation is the real reason to use a sub-agent).
- **Scheduling specialist** — owns the multi-step book/cancel/reschedule dance.

Keep **compliance as a node** and **scope as a prompt rule** — don't promote trivial steps to
agents (that was the original design's mistake).

**b) Dev-time subagents (Claude Code).** For building the project, task-scoped agents help:
- a **code-reviewer** subagent before each commit,
- an **Explore** subagent to map code before changes.
These are workflow tools, not part of the app.

---

## 5. Scripts

**Present in `scripts/`:**
- `setup_hospital_slots.py` — seed 14 days of appointment slots (relative to today).
- `check_composio.py` — verify the Composio/Google Calendar connection (read-only). *(new)*

**Recommended additions:**
- ✅ **`reset_demo.py`** *(added — see below)* — clear all test bookings/documents and reseed
  slots, so you start each demo run clean. **Very useful for a live workshop.**
- ➕ **`smoke_test.py`** — hit `/api/health`, `initialize_session`, and a canned chat to confirm
  the stack is up before presenting. (Playwright skill covers the richer version.)
- ➕ **`seed_demo_patients.py`** — (re)insert the demo patients/records idempotently, so a fresh
  Supabase project is demo-ready in one command.

---

## 6. File organization (done this pass)
- Removed: `transcript_matches.txt`, `write_nodes.txt`, `test_composio.py` (old testing/junk),
  `baymax/utils.py` (dead code), `docs/workflow.md` + `docs/workflow.mmd` (stale multi-agent
  diagrams that contradicted the current design).
- Added `scripts/` and moved `setup_hospital_slots.py` there; added `check_composio.py` and
  `reset_demo.py`.
- Filled in the empty `README.md`; added `docs/CODEBASE_GUIDE.md` (beginner walkthrough).
