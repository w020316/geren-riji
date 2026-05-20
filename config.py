import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

CHROMA_DB_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

SHORT_MEMORY_MAX_TURNS = int(os.getenv("SHORT_MEMORY_MAX_TURNS", "10"))

HF_HUB_CACHE = os.path.join(PROJECT_ROOT, "models")
os.environ["HF_HUB_CACHE"] = HF_HUB_CACHE
