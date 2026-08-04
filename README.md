# 🏥 Project Baymax — AI Healthcare Companion

Baymax is an agentic healthcare assistant that greets patients with context from their records,
triages symptoms with safe follow-up questions, answers questions about their medical history
(RAG), and schedules doctor appointments — with a separate view for hospital staff.

Built to showcase **LangChain · LangGraph · LangSmith · DeepAgents**, with **Supabase (Postgres +
pgvector)** for data & vector search and **Composio** for Google Calendar.

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
