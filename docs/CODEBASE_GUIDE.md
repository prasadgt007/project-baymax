# Codebase Guide — Understanding Baymax

*For someone who knows the **basics** of LangChain and LangGraph and wants to understand how this
specific app is wired. Read top to bottom; it follows one message through the whole system.*

---

## 0. The one-sentence mental model
> Baymax is **one LangGraph** with **two nodes**: a single **DeepAgent** that does the thinking and
> tool-calling, followed by a plain Python node that appends a medical disclaimer. Everything else
> (FastAPI, the MCP server, Supabase, Composio) is plumbing around that graph.

If you remember only that, the rest falls into place.

---

## 1. The pieces (and the LangChain/LangGraph concept each maps to)

| Concept you know | Where it lives here | Notes |
|---|---|---|
| **Graph / nodes / edges** | `baymax/graph.py` | `agent → compliance → END`. Compiled with a `MemorySaver`. |
| **State** (the dict passed between nodes) | `baymax/models.py` → `BaymaxState` | Holds `patient_id`, `user_input`, `messages`, `available_slots`, `pre_consultation_brief`, `final_response`. |
| **Agent / ReAct loop** | `baymax/nodes.py` → `baymax_agent()` | Uses `deepagents.create_deep_agent(...)`. This *is* the "think → call tool → observe → repeat" loop. |
| **Tools** (`@tool`) | `baymax/tools.py` | 7 tools. Created by a **factory** so each is bound to the current patient. |
| **LLM** | `baymax/nodes.py` | `ChatNVIDIA("meta/llama-3.1-70b-instruct")`. |
| **Prompt** | `baymax/skills.md` | Loaded as the agent's system prompt; patient context is appended at runtime. |
| **Retrievers / DB** | `database_mcp_server.py` + `baymax/mcp_client.py` | All Supabase/pgvector access is behind an MCP server. |

---

## 2. Follow one message end-to-end

Say a patient types **"What did my last blood test say?"**

### Step 1 — HTTP in (`server.py`)
The frontend POSTs to `/api/chat` with `{user_message, patient_id, user_role}`. The handler
`chat()` runs the graph and returns the reply. (RBAC lives here too: the doctor brief is only put
in the response for staff.)

> **Why the "clean thread"?** `_run_in_clean_thread(...)` runs the graph in a fresh OS thread with
> no event loop. This is a Windows-specific fix: the MCP client calls `asyncio.run()` internally,
> which clashes with uvicorn's running loop. Don't remove it on Windows.

### Step 2 — Build state & invoke the graph (`server.py` → `_invoke_graph`)
It looks up the cached patient baseline (from `/api/initialize_session`), builds the `state` dict,
sets a `thread_id = "{patient_id}:{user_role}"` (so LangGraph's `MemorySaver` keeps per-user
history), and calls `graph.invoke(state, config)`.

### Step 3 — The agent node (`baymax/nodes.py` → `baymax_agent`)
This is the heart. Each turn it:
1. Calls `create_baymax_tools(patient_id)` — builds the 7 tools **bound to this patient**.
2. Builds the system prompt (`skills.md` + the patient's name/conditions/allergies).
3. Creates the DeepAgent and calls `agent.invoke({"messages": history + [new message]})`.
4. The DeepAgent runs its **ReAct loop**: it reads the prompt, decides to call
   `search_patient_records("cholesterol")`, gets the result, and writes a final answer.
5. The node then extracts structured bits from the run — any `available_slots`, any generated
   `brief` — and **cleans the text** (strips slot UUIDs / brief blocks that shouldn't reach the
   patient).

> **Key idea — tools bound by closure.** `create_baymax_tools(patient_id)` returns functions that
> *close over* `patient_id`. The LLM never passes a patient id; it literally cannot query another
> patient. That's the main isolation boundary in the app (`baymax/tools.py`).

### Step 4 — The tool calls the MCP server (`baymax/tools.py` → `baymax/mcp_client.py`)
`search_patient_records` calls `search_patient_documents_mcp(...)` and `search_interactions_mcp(...)`.
Each wrapper spawns the MCP server as a subprocess, calls the tool over stdio, and returns parsed
JSON. (One subprocess **per call** — simple, but a latency cost; see RECOMMENDATIONS.)

### Step 5 — The actual DB / RAG (`database_mcp_server.py`)
The MCP tool embeds the query with NVIDIA `nv-embedqa-e5-v5` (1024-d) and runs:
```sql
SELECT content_text, created_at FROM patient_documents
WHERE patient_id = %s AND embedding IS NOT NULL
ORDER BY embedding <=> %s::vector   -- <=> = cosine distance
LIMIT %s;
```
The closest documents come back, get returned to the tool, and land in the agent's context.

### Step 6 — Compliance node (`baymax/nodes.py` → `compliance_wrapper`)
A plain function (no LLM). If the reply looks medical, it appends the standard disclaimer. This is
a node *on purpose* — a disclaimer is deterministic, so it should never depend on the model
remembering to add it.

### Step 7 — HTTP out (`server.py`)
`chat()` returns `{response, available_slots, doctor_brief}`. For a patient, `doctor_brief` is
`None`. The frontend renders the text and, if `available_slots` is non-empty, shows slot chips.

---

## 3. How the other features map (same pattern, different tools)

- **Greeting** — `/api/initialize_session` (not the agent) fetches the profile and builds a
  deterministic greeting, and caches the baseline for later chat turns.
- **Triage** — pure prompt behavior (`skills.md`): the "ask a follow-up before remedies" rule is a
  two-stage instruction, not code.
- **Booking** — `get_available_slots` → `book_appointment` (writes the DB **and** creates a Google
  Calendar event via `baymax/calendar_client.py`, storing the event id on the slot).
- **Cancel / reschedule** — `cancel_appointment` resolves the slot from a time hint (e.g. "3pm"),
  frees the DB slot, and deletes the stored calendar event.
- **Brief** — `generate_brief_for_doctor` builds a Markdown brief (`baymax/briefs.py`); it's
  captured into state and only shown to staff.

---

## 4. Things that will surprise you (gotchas)
- **State is in memory.** `MemorySaver` + a module-level `_session_cache` dict. Restart the server
  and all conversations/baselines are gone. Fine for a demo, not for production.
- **RAG runs every turn.** Deliberate for the workshop (easy to show); a production build would
  only retrieve when needed and cache embeddings.
- **The agent must never *invent* IDs.** Slot booking/cancel use real UUIDs from tool output. The
  cancel tool is written defensively (resolve by time) because LLMs fumble UUIDs across turns.
- **`skills.md` is the brain.** Most "behavior" changes (triage, tone, refusals, not leaking IDs)
  are prompt edits there, not code.
- **No auth yet.** `patient_id`/`role` are trusted from the client. See `review/REPORT.md`.

---

## 5. "I want to change X — where do I look?"
| Goal | File |
|---|---|
| Change how it triages / talks / what it refuses | `baymax/skills.md` |
| Add or change a capability (a new tool) | `baymax/tools.py` (+ maybe `database_mcp_server.py`) |
| Change DB queries / RAG | `database_mcp_server.py` |
| Change the graph shape / add a node | `baymax/graph.py`, `baymax/nodes.py` |
| Change the doctor brief format | `baymax/briefs.py` |
| Change calendar behavior | `baymax/calendar_client.py`, `baymax/tools.py` |
| Change API shape / RBAC | `server.py` |
| Change the UI | `frontend/src/App.jsx`, `frontend/src/services/api.js` |

---

## 6. Suggested reading order for the code
1. `baymax/graph.py` (tiny — see the whole shape)
2. `baymax/models.py` (`BaymaxState`)
3. `baymax/nodes.py` (`baymax_agent`, then `compliance_wrapper`)
4. `baymax/tools.py` (skim all 7 tools)
5. `database_mcp_server.py` (the RAG + scheduling SQL)
6. `server.py` (endpoints)

Then open **LangSmith** (tracing is on) and send one message — you'll *see* the ReAct loop and each
tool call, which makes all of the above concrete.
