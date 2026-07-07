from haystack import component
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.document_stores.types import DocumentStore
from haystack_integrations.components.embedders.fastembed import FastembedTextEmbedder
from tavily import TavilyClient

from src.config import EMBEDDING_MODEL, RAG_TOP_K, WEB_MAX_RESULTS


@component
class KnowledgeBaseSearch:
    """Searches the local PDF knowledge base for content relevant to a query."""

    def __init__(self, document_store: DocumentStore, top_k: int = RAG_TOP_K):
        self.document_store = document_store
        self.text_embedder = FastembedTextEmbedder(model=EMBEDDING_MODEL)
        self.text_embedder.warm_up()
        self.retriever = InMemoryEmbeddingRetriever(document_store=document_store, top_k=top_k)

    @component.output_types(context=str, sources=list)
    def run(self, query: str):
        embedding = self.text_embedder.run(text=query)["embedding"]
        docs = self.retriever.run(query_embedding=embedding)["documents"]

        if not docs:
            return {
                "context": "No relevant information was found in the local knowledge base.",
                "sources": [],
            }

        formatted = "\n\n".join(
            f"[Source: {doc.meta.get('file_path', 'unknown')}]\n{doc.content}" for doc in docs
        )
        sources = [
            {
                "file": doc.meta.get("file_path", "unknown"),
                "snippet": doc.content[:200].strip() + ("..." if len(doc.content) > 200 else ""),
                "score": round(doc.score, 3) if doc.score is not None else None,
            }
            for doc in docs
        ]
        return {"context": formatted, "sources": sources}


@component
class TavilyWebSearch:
    """Searches the live web via Tavily for current or real-time information."""

    def __init__(self, api_key: str, max_results: int = WEB_MAX_RESULTS):
        self.api_key = api_key
        self.client = TavilyClient(api_key=api_key)
        self.max_results = max_results

    @component.output_types(results=str, sources=list)
    def run(self, query: str):
        response = self.client.search(
            query=query, max_results=self.max_results, include_answer=True
        )

        lines = []
        if response.get("answer"):
            lines.append(f"Summary: {response['answer']}")
        for r in response.get("results", []):
            lines.append(f"- {r.get('title')}: {r.get('content')}\n  Source: {r.get('url')}")

        sources = [
            {"title": r.get("title"), "url": r.get("url")} for r in response.get("results", [])
        ]
        return {
            "results": "\n".join(lines) if lines else "No web results were found.",
            "sources": sources,
        }
