# Agentic RAG + Web Search Assistant

An agent that answers questions by searching a private local knowledge base first, and
falling back to live web search only when the knowledge base can't help. Built to
demonstrate agentic tool-routing, grounded/cited answers, and honest refusal when neither
source has the information.

**Live demo:** _TODO: fill in after deploy_

## How it works

```mermaid
flowchart LR
    U[User] -->|question| FE[React + Vite UI]
    FE -->|POST /api/chat| API[FastAPI server]
    API --> AG[Haystack Agent]
    AG -->|tried first| KB[knowledge_base_search]
    AG -->|fallback: recent/current info| WEB[web_search]
    KB --> STORE[(In-memory vector store<br/>sentence-transformers embeddings)]
    WEB --> TAVILY[(Tavily Search API)]
    AG -->|grounded answer + citations| API
    API -->|answer, tools_used, kb_sources, web_sources| FE
```

The agent is instructed to always try `knowledge_base_search` first, and only reach for
`web_search` when the knowledge base has nothing relevant or the question is about
something that could have changed since the documents were written. Every response
returns which tool(s) were used and the underlying sources (file + snippet + similarity
score for the knowledge base, title + URL for the web), so answers are traceable rather
than opaque.

## Tech stack

| Layer | Choice |
|---|---|
| Agent framework | [Haystack](https://haystack.deepset.ai/) `Agent` with tool calling |
| LLM | Groq-hosted `openai/gpt-oss-20b` (OpenAI-compatible endpoint) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | Haystack `InMemoryDocumentStore` |
| Web search | [Tavily](https://tavily.com/) |
| API | FastAPI |
| Frontend | React + Vite + TypeScript |
| Packaging | Single multi-stage Dockerfile (frontend build → bundled into the API image) |

## Project structure

```
src/          agent definition, tools (KB search, web search), config, ingestion
server/       FastAPI app (/api/chat, /api/health, serves the built frontend)
frontend/     React + Vite chat UI
data/         source PDFs indexed into the knowledge base
eval/         eval set + runner for measuring retrieval/routing quality
Dockerfile    multi-stage build: frontend -> static assets, backend -> API + index
render.yaml   Render Blueprint for one-step deploy
```

## Running locally (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY and TAVILY_API_KEY

python -m src.ingest    # builds the embedding index from data/*.pdf
uvicorn server.main:app --reload --port 8000
```

In a separate terminal, run the frontend dev server:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Running with Docker

```bash
docker build -t agentic-rag-web-assistant .
docker run --rm -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e TAVILY_API_KEY=your_key \
  agentic-rag-web-assistant
```

The image builds the frontend and bakes the embedding index in at build time, so the
container is self-contained — visit `http://localhost:8000` for the full app (UI + API
on the same origin).

## Deploying

This repo includes a `render.yaml` Blueprint. On [Render](https://render.com/):
`New +` → `Blueprint` → connect this repo → set `GROQ_API_KEY` and `TAVILY_API_KEY` in
the service's environment variables → deploy. Render builds the Dockerfile directly.

## Evaluating retrieval quality

`eval/eval_set.json` has 12 hand-written questions across four categories:

- **kb** — answerable only from the local PDF knowledge base (checks retrieval works and the agent picks the right tool)
- **web** — requires current information not in the knowledge base (checks web fallback)
- **hybrid** — needs both sources combined
- **refusal** — asks for something neither source has, to check the agent says so instead of guessing

Run it with:

```bash
python -m eval.run_eval
```

Each case checks both **tool routing** (did it call the tool(s) the question actually
requires) and **answer content** (does the answer contain the expected grounded facts).
Results are printed to stdout and written to `eval/results.json`.

**Latest run: 11/12 passed.**

The one failure (`refusal-2`, "What is Project Aurora's public stock ticker symbol?")
is a real and informative finding, not a harness bug: "Project Aurora" is a generic
codename, so Tavily's web search surfaces an unrelated real company using the same name,
and the agent confidently answers with that company's ticker instead of recognizing the
name collision and saying the knowledge base/web have no information about *this*
Project Aurora. This is a known limitation of naive knowledge-base + web-search fallback
for internal-only codenames that happen to collide with public entities — a system
prompt change to explicitly check for name-scope mismatches would be the fix, not
attempted here to keep this eval an honest measurement rather than a tuned-to-pass one.
