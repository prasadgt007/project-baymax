# 🏥 Project Baymax — AI Healthcare Companion

Ask a patient what it's like to see a doctor and you'll hear some version of the same story: weeks
of waiting for an appointment, a rushed few minutes once they're finally in the room, and having to
re-explain their whole history because no one's had time to read the chart. Ask the doctor, and
you'll hear the mirror image — too little time with each patient, and too many hours afterward
typing notes into an EHR that never seems to give any of that time back.

None of that is anecdotal — it's measured, and it's large:

## The problem, in numbers
- **More than 12 million** Americans (1 in 20 adults) experience a diagnostic error every year in
  outpatient care alone — [Singh, Meyer & Thomas, *BMJ Quality & Safety*, 2014](https://pubmed.ncbi.nlm.nih.gov/24742777/) —
  and a 2023 Johns Hopkins–led study estimates **795,000 people a year** are permanently disabled or
  die as a result of misdiagnosis — [Newman-Toker et al., *BMJ Quality & Safety*, 2023](https://pubmed.ncbi.nlm.nih.gov/37460118/).
- **31 days** — the average wait for a new physician appointment across major U.S. cities in 2025,
  up **48% since 2004** — [AMN Healthcare, 2025 Survey of Physician Appointment Wait Times](https://www.amnhealthcare.com/amn-insights/physician/whitepapers/2025-survey-of-physician-appointment-wait-times/).
- For every **1 hour** a physician spends face-to-face with patients, nearly **2 more hours** go to
  EHR work and paperwork — [Annals of Internal Medicine, via the American Medical Association](https://pnhp.org/news/physicians-spend-two-hours-on-ehrs-and-desk-work-for-every-hour-of-direct-patient-care/).
- And the face time itself keeps shrinking: primary care visits last **under 5 minutes** for half
  the world's population — [*BMJ Open*, a 67-country study of 28.5M consultations](https://www.sciencedaily.com/releases/2017/11/171108215721.htm).
- **$150 billion** is lost every year in the U.S. alone to missed appointments, with no-show rates
  running **5–30%** depending on specialty — [HCI Innovation Group](https://www.hcinnovationgroup.com/clinical-it/article/13008175/missed-appointments-cost-the-us-healthcare-system-150b-each-year).
- **46%** of patients have filled out the *same* medical history form more than once, and **97%**
  say it matters that their provider actually has their full history on hand — [Harmony Healthcare IT](https://www.harmonyhit.com/electronic-medical-records-statistics/).

The encouraging part: this is already provably tractable with exactly this kind of technology —
where AI-assisted documentation has been adopted, it's cut physician admin time by roughly **20%**,
and **75%** of physician AI users say it's already reduced their burden — [Doximity, 2026 State of
AI in Medicine Report](https://www.doximity.com/reports/state-of-ai-medicine-report/2026).

## How Baymax helps
Baymax is a small, workshop-scale demonstration of an agentic AI assistant aimed squarely at that
gap — **personalized enough to feel like it actually knows the patient**, and **useful enough to
give hospital staff a head start before the patient ever walks in**.

**For patients**, that means: not re-explaining a chronic condition on every visit, because Baymax
already knows it and opens by referencing it directly, by name; getting an answer to "what did my
last blood test say?" in seconds via semantic search over their *own* records, instead of waiting
weeks for a callback; being asked real follow-up questions about a new symptom — severity, duration,
what makes it worse — the way a careful clinician would, before any remedy is suggested, and with
that remedy checked against the patient's own allergies and medications; and booking, rescheduling,
or cancelling an appointment (synced straight to Google Calendar) from a chat message instead of a
phone queue.

**For hospital staff**, that means an auto-generated pre-consultation brief waiting for the doctor
before the patient sits down — symptoms, relevant history, allergies, current medications, already
synthesized into one page. That directly targets the same root cause research ties to a meaningful
share of diagnostic error and rushed visits: not enough time, not enough information, right when it
matters most.

None of this replaces clinical judgment, and Baymax doesn't claim to. It's a demo built to showcase
**LangChain · LangGraph · LangSmith · DeepAgents**, with **Supabase (Postgres + pgvector)** for data
& vector search and **Composio** for Google Calendar, as one concrete way these patterns can be
pointed at a real, well-documented problem.

> ⚠️ **Demo project.** There is **no authentication yet** — the client sends a `patient_id` and a
> `role`. Do not use with real patient data. See [review/REPORT.md](review/REPORT.md) for the full
> security assessment and roadmap.

---

## What it does
- **Proactive greeting** — on login, greets the patient by name and references their chronic
  conditions / upcoming appointment.
- **Symptom triage** — asks 1–2 follow-up questions *before* suggesting safe home remedies.
- **Records Q&A (RAG)** — semantic search over the patient's documents and visit notes.
- **Scheduling** — shows open slots, books/cancels/reschedules, and syncs to **Google Calendar**.
- **Staff view** — upload documents and view an auto-generated pre-consultation brief (hidden from
  patients).

---

## Architecture at a glance
```
React + Vite + Three.js (frontend, :3000)
        │  /api  (Vite proxy)
        ▼
FastAPI (server.py, :8000)
        ▼
LangGraph:  baymax_agent  ──▶  compliance_wrapper  ──▶  reply
            (one DeepAgent,       (adds medical
             ReAct + 7 tools)      disclaimer)
        ▼
MCP stdio server (database_mcp_server.py)
        ▼
Supabase Postgres + pgvector      Composio ─▶ Google Calendar
```
Deeper explanation in [docs/CODEBASE_GUIDE.md](docs/CODEBASE_GUIDE.md) and
[workshop/](workshop/).

---

## Prerequisites
- **Python ≥ 3.12** and **[uv](https://docs.astral.sh/uv/)** (package manager)
- **Node.js ≥ 18** and **npm**
- A **Supabase** project (Postgres with the `vector` extension)
- An **NVIDIA API key** (for the LLM + embeddings — [build.nvidia.com](https://build.nvidia.com))
- *(Optional)* A **Composio** account with Google Calendar connected (for calendar sync)

---

## Setup

### 1. Clone & install
```bash
git clone https://github.com/prasadgt007/project-baymax.git
cd project-baymax
uv sync                       # backend deps into .venv
cd frontend && npm install && cd ..
```

### 2. Configure environment
Copy the example and fill in your keys:
```bash
cp .env.example .env
```
| Variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | ✅ | LLM (`meta/llama-3.1-70b-instruct`) + embeddings (`nv-embedqa-e5-v5`) |
| `SUPABASE_DB_URI` | ✅ | Postgres connection string (pooler, port 6543) |
| `COMPOSIO_API_KEY` / `COMPOSIO_USER_ID` | ⛅ | Google Calendar sync (optional but recommended) |
| `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` | ⛅ | LangSmith tracing (optional) |
| `NGROK_AUTHTOKEN` | ⛅ | Only for sharing via `npm run share` |

### 3. Set up the database (Supabase SQL editor)
Enable pgvector, then run the migrations in `db/`:
```sql
create extension if not exists vector;
```
Run these files in the Supabase SQL editor (in order):
`db/supabase_schema.sql` → `db/migration_patient_documents.sql` → `db/migration_slots.sql`

Then seed appointment slots for the next 14 days (relative to today):
```bash
uv run python scripts/setup_hospital_slots.py
```

### 4. (Optional) Verify Composio / Google Calendar
```bash
uv run python scripts/check_composio.py
```

---

## Run

**Backend** (terminal 1):
```bash
uv run uvicorn server:app --port 8000
```
**Frontend** (terminal 2):
```bash
cd frontend && npm run dev      # opens http://localhost:3000
```
Open **http://localhost:3000**.

---

## Using the app
- **As a patient:** log in with a demo ID — `P001` (Chester V) or `P002` (John Doe). Try:
  - *"I've had a headache for two days"* → it asks a follow-up first, then suggests remedies.
  - *"What did my last blood test say?"* → RAG lookup over your records.
  - *"Book an appointment"* → pick a slot chip → confirmed + added to Google Calendar.
  - *"Cancel my 3pm"* / *"Reschedule to 11am"* → DB and calendar stay in sync.
- **As hospital staff:** toggle **Hospital Staff**, enter any staff ID (e.g. `E001`). Upload a PDF
  to a patient and view their pre-consultation brief.

---

## Project layout
```
server.py                  FastAPI app (endpoints + RBAC)
database_mcp_server.py     MCP stdio server: all Supabase/pgvector access
baymax/                    the agent
  graph.py                 LangGraph (agent → compliance → END)
  nodes.py                 the DeepAgent node + compliance node
  tools.py                 the 7 LangChain tools (bound per patient)
  mcp_client.py            sync wrappers that call the MCP server
  calendar_client.py       Composio Google Calendar helper
  briefs.py                pre-consultation brief generator
  skills.md                the agent's system prompt
  models.py                state + domain models
db/                        SQL schema & migrations
scripts/                   setup_hospital_slots.py, check_composio.py
frontend/                  React + Vite app
docs/                      journal + codebase guide + recommendations
workshop/                  presenter notes for the workshop
review/                    code + security review
.agents/skills/            Agent Skills (dev tooling)
```

---

## Troubleshooting
- **`SUPABASE_DB_URI not set`** — your `.env` isn't filled in, or you're not running from the repo
  root.
- **No slots appear** — run `scripts/setup_hospital_slots.py` (it seeds relative to *today*).
- **Calendar events don't appear on *your* calendar** — they're created on the **Composio-connected
  Google account**, which may differ from your personal one. Run `scripts/check_composio.py` to see
  which account is connected.
- **First response is slow** — the agent makes several model calls per turn and runs RAG on every
  message (a deliberate demo choice). Booking is the heaviest turn. See
  [docs/RECOMMENDATIONS.md](docs/RECOMMENDATIONS.md) for latency options.
- **Windows** — this project is developed on Windows; the backend uses UTF-8 + a clean-thread
  workaround for the asyncio/MCP interaction. Use `uv run …` so the correct venv Python is used.

---

## Learn more
- **[docs/CODEBASE_GUIDE.md](docs/CODEBASE_GUIDE.md)** — a beginner-friendly walkthrough of how a
  message flows through the code (assumes only LangChain/LangGraph basics).
- **[docs/PROJECT_JOURNAL.md](docs/PROJECT_JOURNAL.md)** — the development story & decisions.
- **[workshop/](workshop/)** — why single-DeepAgent over multi-agent, and how RAG works.
- **[review/](review/)** — full code & security review.
