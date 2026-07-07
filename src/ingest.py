import pickle

from haystack import Pipeline
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import ByteStream
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.document_stores.types import DocumentStore, DuplicatePolicy
from haystack_integrations.components.embedders.fastembed import FastembedDocumentEmbedder

from src.config import DATA_DIR, EMBEDDING_MODEL, INDEX_PATH


def build_index() -> None:
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit(
            f"No PDFs found in {DATA_DIR}. Add PDF files there and re-run this script."
        )

    document_store = InMemoryDocumentStore()

    pipeline = Pipeline()
    pipeline.add_component("converter", PyPDFToDocument())
    pipeline.add_component(
        "splitter", DocumentSplitter(split_by="sentence", split_length=5, split_overlap=1)
    )
    pipeline.add_component("embedder", FastembedDocumentEmbedder(model=EMBEDDING_MODEL))
    pipeline.add_component("writer", DocumentWriter(document_store=document_store))

    pipeline.connect("converter", "splitter")
    pipeline.connect("splitter", "embedder")
    pipeline.connect("embedder", "writer")

    pipeline.run({"converter": {"sources": pdf_files}})

    docs = document_store.filter_documents()
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(docs, f)

    print(f"Indexed {len(docs)} chunks from {len(pdf_files)} PDF(s) -> {INDEX_PATH}")


def ingest_pdf_bytes(
    document_store: DocumentStore,
    embedder: FastembedDocumentEmbedder,
    pdf_bytes: bytes,
    filename: str,
) -> int:
    """Embeds an uploaded PDF and writes it into a live document store immediately.

    Reuses the given (already-warmed-up) embedder rather than loading a fresh
    ONNX model per upload.
    """
    source = ByteStream(data=pdf_bytes, meta={"file_path": filename})
    docs = PyPDFToDocument().run(sources=[source])["documents"]
    docs = DocumentSplitter(split_by="sentence", split_length=5, split_overlap=1).run(
        documents=docs
    )["documents"]
    docs = embedder.run(documents=docs)["documents"]
    document_store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
    return len(docs)


if __name__ == "__main__":
    build_index()
