from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INDEX_PATH = ROOT_DIR / "index_store.pkl"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

RAG_TOP_K = 5
WEB_MAX_RESULTS = 5
