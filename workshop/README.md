# Project Baymax — Workshop Materials

Presenter-facing notes for the workshop. These explain the *why* behind Baymax's design so you
can talk through the engineering decisions, not just the code.

**Workshop theme:** building a real agentic app with **LangChain · LangGraph · LangSmith ·
DeepAgents**, plus **Agent Skills**, developed in a systematic, efficient way.

## Contents
1. **[architecture-single-deepagent-vs-multi-agent.md](architecture-single-deepagent-vs-multi-agent.md)**
   — Why we started with a multi-agent (supervisor + sub-agents) design, the problems it caused
   (mis-routing, hallucination, latency), and why we moved to a single DeepAgent. Includes the
   nuance: *when* multi-agent is actually worth it.
2. **[rag-supabase-pgvector-and-auth.md](rag-supabase-pgvector-and-auth.md)**
   — How Retrieval-Augmented Generation works in Baymax using Supabase + pgvector, the data model
   and query flow, and how Supabase unlocks the next features (Auth, Row-Level Security, Storage).

## How these map to the demo
- **LangGraph** — the 2-node graph (`agent → compliance`) is the smallest honest example of a
  stateful graph; see doc 1.
- **DeepAgents** — the single agent's ReAct tool loop, and where sub-agents *would* fit; doc 1.
- **LangSmith** — tracing is enabled (`LANGCHAIN_TRACING_V2`); use a trace to *show* the tool
  calls per turn live.
- **RAG / pgvector** — doc 2, with the actual SQL and embedding model.
- **Agent Skills** — the `.agents/skills/` folder (Supabase + the three frontend skills) shows how
  skills guide the assistant while building.

> These docs describe the system as built (single DeepAgent, RAG-every-query, no auth yet). Where
> something is a *roadmap* item (e.g. authentication), it is labelled as such.
