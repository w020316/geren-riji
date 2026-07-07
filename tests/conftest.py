"""pytest 全局 fixtures。"""
import os
import sys
import json
import tempfile
import shutil
import types
from pathlib import Path

import pytest

# 将项目根目录加入 sys.path，便于 import 业务模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------- 注入轻量替身模块（仅在真实模块未安装时）----------
# 测试不依赖真实的向量库，FakeOrchestrator 不会实例化 MemoryManager。
# 但 import 链会触发模块加载，若环境未装 chromadb / sentence_transformers，注入假模块避免 ImportError。
def _try_import(module_name):
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def _install_fake_modules():
    if not _try_import("chromadb"):
        fake_chroma = types.ModuleType("chromadb")
        fake_chroma.__path__ = []  # 标记为 package，允许 from chromadb.config import ...

        class _Settings:
            pass

        class _PersistentClient:
            def __init__(self, path=None, **kwargs):
                self.path = path

            def get_or_create_collection(self, name=None, metadata=None, **kwargs):
                return _FakeCollection()

        class _FakeCollection:
            def __init__(self):
                self._data = {}

            def add(self, ids=None, embeddings=None, documents=None, metadatas=None, **kwargs):
                for i, mid in enumerate(ids or []):
                    self._data[mid] = {
                        "embedding": embeddings[i] if embeddings else [],
                        "document": documents[i] if documents else "",
                        "metadata": metadatas[i] if metadatas else {},
                    }

            def query(self, query_embeddings=None, n_results=5, **kwargs):
                return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

            def get(self, limit=50, **kwargs):
                ids = list(self._data.keys())[:limit]
                return {
                    "ids": ids,
                    "documents": [self._data[i]["document"] for i in ids],
                    "metadatas": [self._data[i]["metadata"] for i in ids],
                }

            def delete(self, ids=None, **kwargs):
                for mid in ids or []:
                    self._data.pop(mid, None)

            def count(self):
                return len(self._data)

        fake_chroma_config = types.ModuleType("chromadb.config")
        fake_chroma_config.Settings = _Settings
        fake_chroma.PersistentClient = _PersistentClient
        fake_chroma.config = fake_chroma_config
        sys.modules["chromadb"] = fake_chroma
        sys.modules["chromadb.config"] = fake_chroma_config

    if not _try_import("sentence_transformers"):
        fake_st = types.ModuleType("sentence_transformers")

        class _FakeSentenceTransformer:
            def __init__(self, model_name=None, **kwargs):
                self.model_name = model_name

            def encode(self, text, normalize_embeddings=False, **kwargs):
                if isinstance(text, str):
                    return [0.1] * 8
                return [[0.1] * 8 for _ in text]

        fake_st.SentenceTransformer = _FakeSentenceTransformer
        sys.modules["sentence_transformers"] = fake_st


_install_fake_modules()


@pytest.fixture()
def tmp_diary_dir(tmp_path, monkeypatch):
    """为 DiaryStore 提供独立临时目录，避免污染真实数据。"""
    # 临时改写 config.PROJECT_ROOT，使 DiaryStore 落在 tmp_path 下
    import config
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    yield tmp_path


@pytest.fixture()
def fresh_diary_store(tmp_diary_dir):
    """构造一个干净的 DiaryStore 实例。"""
    # 重新导入以让 monkeypatch 生效
    import importlib
    import diary_store
    importlib.reload(diary_store)
    return diary_store.DiaryStore()


@pytest.fixture()
def short_memory():
    from memory import ShortTermMemory
    return ShortTermMemory(max_turns=3)


@pytest.fixture()
def fake_emotion():
    return {"emotion": "开心", "intensity": 8, "keywords": ["阳光", "散步"], "brief_analysis": "用户语气轻松愉悦"}


# ---------- FastAPI TestClient 相关 ----------

class _FakeOrchestrator:
    """替身 orchestrator，避免真实调用 LLM / ChromaDB。"""

    class _EmotionAgent:
        def run(self, user_input: str) -> dict:
            return {"emotion": "平静", "intensity": 5, "keywords": [], "brief_analysis": "测试情绪"}

    class _MemoryAgent:
        def search_relevant(self, user_input: str, n_results: int = 5) -> list:
            return [{"content": "用户上周去了公园", "metadata": {}, "distance": 0.1}]

        def extract_and_save(self, user_input: str, emotion_info: dict) -> list:
            return ["fake-mid"]

    class _DiaryAgent:
        def run(self, user_input, emotion_info, memories) -> str:
            return "这是一篇测试日记正文。"

    class _DialogAgent:
        def run(self, user_input, emotion_info, diary, memories) -> str:
            return "这是测试回复。"

    class _MemoryManager:
        def __init__(self):
            self._memories = [
                {"id": "m1", "content": "测试记忆1", "metadata": {"emotion": "开心"}},
                {"id": "m2", "content": "测试记忆2", "metadata": {"emotion": "平静"}},
            ]

        def count(self) -> int:
            return len(self._memories)

        def forget_memory(self, memory_id: str) -> bool:
            before = len(self._memories)
            self._memories = [m for m in self._memories if m["id"] != memory_id]
            return len(self._memories) < before

    class _ShortMemory:
        def __init__(self):
            self.messages = []

        def add(self, role, content):
            self.messages.append({"role": role, "content": content})

        def clear(self):
            self.messages = []

    def __init__(self):
        self.emotion_agent = self._EmotionAgent()
        self.memory_agent = self._MemoryAgent()
        self.diary_agent = self._DiaryAgent()
        self.dialog_agent = self._DialogAgent()
        self.memory_manager = self._MemoryManager()
        self.short_memory = self._ShortMemory()

    def process(self, user_input: str) -> dict:
        emotion = self.emotion_agent.run(user_input)
        memories = self.memory_agent.search_relevant(user_input)
        diary = self.diary_agent.run(user_input, emotion, memories)
        response = self.dialog_agent.run(user_input, emotion, diary, memories)
        return {
            "emotion": emotion,
            "diary": diary,
            "response": response,
            "memories_found": len(memories),
            "short_memory_context": "",
        }

    def get_all_memories(self) -> list:
        return self.memory_manager._memories

    def clear_short_memory(self):
        self.short_memory.clear()


@pytest.fixture()
def fake_app(tmp_diary_dir, monkeypatch):
    """构造使用 FakeOrchestrator 的 FastAPI app，避免外部依赖。

    通过 monkeypatch 替换 agents.MultiAgentOrchestrator，再 reload main，
    避免 main 模块加载时真实初始化 ChromaDB / SentenceTransformer。

    注意：reload(config) 会重新执行 config.py 的 `PROJECT_ROOT = os.path.dirname(...)`，
    覆盖 tmp_diary_dir 的 monkeypatch，故 reload 后需重新设置。
    """
    import importlib
    import config
    importlib.reload(config)
    # reload(config) 重置了 PROJECT_ROOT，需重新指向临时目录
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_diary_dir))

    # 先 reload agents，再替换其 Orchestrator 类
    import agents as agents_module
    importlib.reload(agents_module)
    # 备份原类以便测试结束后恢复
    original_cls = agents_module.MultiAgentOrchestrator
    agents_module.MultiAgentOrchestrator = _FakeOrchestrator

    try:
        import diary_store
        importlib.reload(diary_store)
        import main
        importlib.reload(main)
        yield main.app
    finally:
        # 恢复原始类，避免污染其他测试
        agents_module.MultiAgentOrchestrator = original_cls


@pytest.fixture()
def client(fake_app):
    from fastapi.testclient import TestClient
    return TestClient(fake_app)
