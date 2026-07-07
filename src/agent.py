import os
import pickle

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.tools import ComponentTool
from haystack.utils import Secret

from src.config import GROQ_BASE_URL, GROQ_MODEL, INDEX_PATH
from src.tools import KnowledgeBaseSearch, TavilyWebSearch

SYSTEM_PROMPT = """You are an assistant that answers questions using two tools:

1. knowledge_base_search - searches a private local knowledge base built from PDF documents.
2. web_search - searches the live web via Tavily for current, real-time, or recent information.

Rules:
- Always try knowledge_base_search first.
- Only use web_search if the knowledge base has no relevant answer, or the question is about
  recent events, current data, or anything that could have changed since the documents were written.
- You may use both tools if the knowledge base only partially answers the question.
- Ground your final answer in the retrieved context. If neither tool has relevant information,
  say so clearly instead of guessing.
- Be concise and cite whether the answer came from the knowledge base, the web, or both.
"""


def load_document_store() -> InMemoryDocumentStore:
    if not INDEX_PATH.exists():
        raise SystemExit(
            "No index found. Add PDFs to data/ and run `python -m src.ingest` first."
        )
    with open(INDEX_PATH, "rb") as f:
        docs = pickle.load(f)

    store = InMemoryDocumentStore()
    store.write_documents(docs)
    return store


def build_agent() -> tuple[Agent, InMemoryDocumentStore]:
    document_store = load_document_store()

    rag_tool = ComponentTool(
        component=KnowledgeBaseSearch(document_store=document_store),
        name="knowledge_base_search",
        description="Search the private local PDF knowledge base for relevant context.",
        outputs_to_string={"source": "context"},
        outputs_to_state={"kb_sources": {"source": "sources"}},
    )

    web_tool = ComponentTool(
        component=TavilyWebSearch(api_key=os.environ["TAVILY_API_KEY"]),
        name="web_search",
        description="Search the live web for current, real-time, or recent information.",
        outputs_to_string={"source": "results"},
        outputs_to_state={"web_sources": {"source": "sources"}},
    )

    chat_generator = OpenAIChatGenerator(
        api_key=Secret.from_env_var("GROQ_API_KEY"),
        api_base_url=GROQ_BASE_URL,
        model=GROQ_MODEL,
        generation_kwargs={"temperature": 0},
    )

    agent = Agent(
        chat_generator=chat_generator,
        tools=[rag_tool, web_tool],
        system_prompt=SYSTEM_PROMPT,
        state_schema={
            "kb_sources": {"type": list},
            "web_sources": {"type": list},
        },
    )
    return agent, document_store


def extract_tool_names(messages) -> list[str]:
    names = []
    for msg in messages:
        tool_call = getattr(msg, "tool_call", None)
        if tool_call is not None:
            names.append(tool_call.tool_name)
        for tc in getattr(msg, "tool_calls", None) or []:
            names.append(tc.tool_name)
    return list(dict.fromkeys(names))
