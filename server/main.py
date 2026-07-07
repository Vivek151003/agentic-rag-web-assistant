from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.embedders.fastembed import FastembedDocumentEmbedder
from pydantic import BaseModel

from src.agent import build_agent, extract_tool_names
from src.config import EMBEDDING_MODEL
from src.ingest import ingest_pdf_bytes

load_dotenv()

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# Max number of past messages (user + assistant turns combined) kept per session
# and replayed back to the agent as conversation context.
MAX_HISTORY_MESSAGES = 20

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10MB, generous for a free-tier instance

agent_state: dict = {}
sessions: dict[str, list[ChatMessage]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent, document_store = build_agent()
    agent_state["agent"] = agent
    agent_state["document_store"] = document_store

    upload_embedder = FastembedDocumentEmbedder(model=EMBEDDING_MODEL)
    upload_embedder.warm_up()
    agent_state["upload_embedder"] = upload_embedder

    yield
    agent_state.clear()


app = FastAPI(title="Agentic RAG + Web Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Matches any localhost/127.0.0.1 dev port, since Vite silently picks the next
    # free port (5174, 5175, ...) when 5173 is already taken.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    session_id: str


class KBSource(BaseModel):
    file: str
    snippet: str
    score: float | None = None


class WebSource(BaseModel):
    title: str | None = None
    url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str]
    kb_sources: list[KBSource]
    web_sources: list[WebSource]


class UploadResponse(BaseModel):
    filename: str
    chunks_added: int


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    agent = agent_state["agent"]
    history = sessions.setdefault(req.session_id, [])

    response = agent.run(messages=history + [ChatMessage.from_user(req.question)])
    assistant_message = response["last_message"]

    # Only persist the plain user/assistant turns (not the intermediate tool-call
    # bookkeeping messages), so replayed history is always a valid alternating
    # conversation regardless of which tools a given turn used.
    history.append(ChatMessage.from_user(req.question))
    history.append(assistant_message)
    del history[:-MAX_HISTORY_MESSAGES]

    return ChatResponse(
        answer=assistant_message.text,
        tools_used=extract_tool_names(response["messages"]),
        kb_sources=response.get("kb_sources") or [],
        web_sources=response.get("web_sources") or [],
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (10MB limit).")

    chunks_added = ingest_pdf_bytes(
        agent_state["document_store"],
        agent_state["upload_embedder"],
        pdf_bytes,
        file.filename,
    )
    return UploadResponse(filename=file.filename, chunks_added=chunks_added)


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
