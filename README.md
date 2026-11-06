# Project Baymax — Agentic AI Healthcare Assistant

An AI assistant that gives patients symptom triage, answers from their own medical records, and
appointment booking in one chat, and gives doctors a pre-visit brief before the patient walks in.

- **Personal project**, designed and built solo. This repo is the 2026 rebuild.
- **Built with:** LangGraph · DeepAgents · MCP · Supabase (Postgres + pgvector) · LangSmith · FastAPI · React
- **Recognition:** the original version won the **Bold Leap Award** at Accelirate's Agentic Hackathon (2025).
  The rebuild was the main case study for a 3-country workshop series on building and tracing AI agents.

---

## The problem

Patients wait weeks for an appointment, then get a short visit where they re-explain their history.
Doctors spend close to
[two hours on EHR and desk work for every hour with patients](https://pnhp.org/news/physicians-spend-two-hours-on-ehrs-and-desk-work-for-every-hour-of-direct-patient-care/),
so the context that would speed up the visit is rarely read beforehand. The average wait for a new
physician appointment across major US cities was
[31 days in 2025](https://www.amnhealthcare.com/amn-insights/physician/whitepapers/2025-survey-of-physician-appointment-wait-times/).

Baymax targets both sides: patients get answers and bookings without a phone queue, and staff get a
one-page brief built from the patient's records.

## What it does

| For patients | For hospital staff |
|---|---|
| Greets the patient by name and references their chronic conditions | Uploads documents (PDFs) to a patient's record |
| Triages symptoms: asks follow-up questions **before** suggesting remedies, then checks remedies against the patient's allergies, medications, and chronic conditions | Gets an auto-generated pre-consultation brief (symptoms, history, allergies, medications), hidden from the patient view |
| Answers questions about their own records using RAG ("What did my last blood test say?") | Role-based access: patients cannot upload or view briefs |
| Books, cancels, and reschedules appointments, synced to Google Calendar | |

---

## Architecture

```
React + Vite + Three.js (frontend, :3000)
        │  /api
        ▼
FastAPI (server.py, :8000)
        ▼
LangGraph:  baymax_agent  ──▶  compliance_wrapper  ──▶  reply
            (one DeepAgent,       (deterministic node,
             ReAct loop, 7 tools)  adds medical disclaimer)
        ▼
MCP stdio server (database_mcp_server.py)
        ▼
Supabase Postgres + pgvector      Composio ─▶ Google Calendar
```

### Key design decision: one DeepAgent instead of a supervisor with sub-agents

The first version used a supervisor that routed each message to a Symptom, History, or Scheduling
agent. It failed in three ways:

1. **Misrouting.** "My head hurts, and did my last blood test show anything?" is both a symptom and
   a records query. The supervisor had to pick one, and often picked wrong.
2. **Latency.** Each hop was a sequential LLM call, so one turn could take 4–6 calls before the user
   saw a reply.
3. **Trivial steps as agents.** The disclaimer and the scope check were full LLM agents doing
   deterministic work.

I replaced it with a single DeepAgent running one ReAct loop over 7 tools. The disclaimer became a
plain code node and the scope check became a prompt rule. Mixed-intent messages are handled in one
context, and there is no routing step to get wrong. Full write-up:
[docs/architecture-decision.md](docs/architecture-decision.md).

### Other implementation details

- **Patient isolation by closure.** Tools are created per session and bound to the current
  `patient_id`, so the model never passes a patient ID and cannot query another patient.
- **All database access goes through an MCP server**, which keeps SQL and vector search out of the
  agent code.
- **LangSmith tracing** to check tool calls, latency, and token use for each turn.

---

## Testing

Seven flows tested end to end against the live database and calendar:

| # | Flow | Result |
|---|---|---|
| 1 | Greeting with name and chronic conditions | Pass |
| 2 | Triage asks a follow-up before suggesting remedies | Pass |
| 3 | Slot list shows plain times, no internal IDs | Pass |
| 4 | Booking writes to Supabase and creates a Google Calendar event | Pass |
| 5 | Cancellation frees the slot and deletes the calendar event | Pass |
| 6 | Patient upload blocked (403), staff upload allowed (200) | Pass |
| 7 | Staff brief adapts when no symptoms are on file | Pass |

## Known limitations

This is a demo built on synthetic patient data. Before any real use, it would need:

- **Authentication.** The client currently sends `patient_id` and `role`, and the server trusts them.
  The planned fix is Supabase Auth (JWT) with row-level security policies.
- **Code-level safety checks.** The triage follow-up and the remedy checks (allergies, medications,
  chronic conditions) are enforced by the system prompt, not by code, so the model can still skip
  them. They should move into graph state and code gates.
- **Lower latency.** RAG runs on every message (a deliberate choice for the workshop demo) and each
  MCP call starts a new subprocess.

---

## Run locally

**Prerequisites:** Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/), Node.js ≥ 18, a Supabase
project with the `vector` extension, and an [NVIDIA API key](https://build.nvidia.com).
Composio (Google Calendar) and LangSmith are optional.

```bash
git clone https://github.com/prasadgt007/project-baymax.git
cd project-baymax
uv sync
cd frontend && npm install && cd ..
cp .env.example .env          # fill in your keys
```

| Variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | LLM (`meta/llama-3.1-70b-instruct`) and embeddings (`nv-embedqa-e5-v5`) |
| `SUPABASE_DB_URI` | Yes | Postgres connection string |
| `COMPOSIO_API_KEY`, `COMPOSIO_USER_ID` | Optional | Google Calendar sync |
| `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` | Optional | LangSmith tracing |

**Database:** in the Supabase SQL editor, run `create extension if not exists vector;`, then
`db/supabase_schema.sql` → `db/migration_patient_documents.sql` → `db/migration_slots.sql`.
Seed 14 days of appointment slots:

```bash
uv run python scripts/setup_hospital_slots.py
```

**Start:**

```bash
uv run uvicorn server:app --port 8000      # terminal 1
cd frontend && npm run dev                 # terminal 2 → http://localhost:3000
```

Log in as a patient with demo ID `P001` or `P002`, or switch to **Hospital Staff** with any staff ID
(e.g. `E001`). Try "I've had a headache for two days", "What did my last blood test say?", or
"Book an appointment".

---

## Repository layout

```
server.py                  FastAPI app (endpoints and role checks)
database_mcp_server.py     MCP server: all Supabase and pgvector access
baymax/
  graph.py                 LangGraph (agent → compliance → END)
  nodes.py                 DeepAgent node and compliance node
  tools.py                 the 7 tools, bound per patient
  mcp_client.py            wrappers that call the MCP server
  calendar_client.py       Google Calendar via Composio
  briefs.py                pre-consultation brief generator
  skills.md                the agent's system prompt
  models.py                state and domain models
db/                        SQL schema and migrations
scripts/                   slot seeding, demo reset, calendar check
frontend/                  React + Vite app
docs/                      design write-ups (below)
```

## Docs

- [Architecture decision: single DeepAgent vs. multi-agent](docs/architecture-decision.md)
- [RAG with Supabase + pgvector, and the auth roadmap](docs/rag-and-data-model.md)
- [Codebase guide: one message traced through the system](docs/codebase-guide.md)

*Baymax does not replace clinical judgment. Medical replies end with a disclaimer added in code.*
