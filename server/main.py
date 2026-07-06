from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from haystack.dataclasses import ChatMessage
from pydantic import BaseModel

from src.agent import build_agent, extract_tool_names

load_dotenv()

agent_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_state["agent"] = build_agent()
    yield
    agent_state.clear()


app = FastAPI(title="Agentic RAG + Web Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


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


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    agent = agent_state["agent"]
    response = agent.run(messages=[ChatMessage.from_user(req.question)])

    return ChatResponse(
        answer=response["last_message"].text,
        tools_used=extract_tool_names(response["messages"]),
        kb_sources=response.get("kb_sources") or [],
        web_sources=response.get("web_sources") or [],
    )
