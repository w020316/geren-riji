import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ===== 数据目录（支持环境变量覆盖，便于云端持久化磁盘）=====
# 默认数据存放在项目根目录，云端部署时通过 DATA_DIR 指向持久化挂载点
DATA_DIR = os.getenv("DATA_DIR", PROJECT_ROOT)

# ===== LLM 供应商配置（OpenAI 兼容协议）=====
# 当前默认接入 Agnes AI（https://agnes-ai.com/）聚合服务
# API 端点：https://apihub.agnes-ai.com/v1
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://apihub.agnes-ai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "agnes-2.0-flash")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# ===== 嵌入与向量库 =====
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

# ===== 短期记忆 =====
SHORT_MEMORY_MAX_TURNS = int(os.getenv("SHORT_MEMORY_MAX_TURNS", "10"))

# ===== HuggingFace 缓存目录（避免下载到 C 盘）=====
HF_HUB_CACHE = os.path.join(DATA_DIR, "models")
os.environ["HF_HUB_CACHE"] = HF_HUB_CACHE
