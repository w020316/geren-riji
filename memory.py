import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from config import CHROMA_DB_DIR, EMBEDDING_MODEL
import uuid
from datetime import datetime


class MemoryManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.collection = self.client.get_or_create_collection(
            name="diary_memories",
            metadata={"hnsw:space": "cosine"}
        )
        self.encoder = SentenceTransformer(EMBEDDING_MODEL)

    def _encode(self, text: str) -> list:
        return self.encoder.encode(text, normalize_embeddings=True).tolist()

    def save_memory(self, content: str, metadata: dict = None) -> str:
        if metadata is None:
            metadata = {}
        metadata["timestamp"] = datetime.now().isoformat()
        memory_id = str(uuid.uuid4())
        embedding = self._encode(content)
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )
        return memory_id

    def search_memory(self, query: str, n_results: int = 5) -> list:
        if self.collection.count() == 0:
            return []
        query_embedding = self._encode(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count())
        )
        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 0
                memories.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist
                })
        return memories

    def forget_memory(self, memory_id: str) -> bool:
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False

    def get_all_memories(self, limit: int = 50) -> list:
        if self.collection.count() == 0:
            return []
        results = self.collection.get(limit=limit)
        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                mid = results["ids"][i] if results["ids"] else ""
                memories.append({
                    "id": mid,
                    "content": doc,
                    "metadata": meta
                })
        return memories


class ShortTermMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.messages = []

    def add(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2):]

    def get_context(self) -> str:
        if not self.messages:
            return ""
        lines = []
        for msg in self.messages:
            role_label = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role_label}: {msg['content']}")
        return "\n".join(lines)

    def clear(self):
        self.messages = []
