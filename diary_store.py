import json
import os
import threading
import uuid
from datetime import datetime
from config import DATA_DIR


class DiaryStore:
    def __init__(self):
        self.diary_dir = os.path.join(DATA_DIR, "diaries")
        os.makedirs(self.diary_dir, exist_ok=True)
        self.index_file = os.path.join(self.diary_dir, "index.json")
        self._lock = threading.Lock()
        self._ensure_index()

    def _ensure_index(self):
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False)

    def _read_index(self) -> list:
        with open(self.index_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_index(self, index: list):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def save_diary(self, user_input: str, diary_text: str, emotion: dict) -> str:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        # 时间戳 + uuid 短码，保证绝对唯一，避免同秒/同微秒并发写入冲突
        diary_id = now.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]

        entry = {
            "id": diary_id,
            "date": date_str,
            "time": time_str,
            "emotion": emotion.get("emotion", "平静"),
            "intensity": emotion.get("intensity", 5),
            "user_input": user_input,
            "diary": diary_text
        }

        diary_file = os.path.join(self.diary_dir, f"{diary_id}.json")
        with open(diary_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

        with self._lock:
            index = self._read_index()
            index.insert(0, {
                "id": diary_id,
                "date": date_str,
                "time": time_str,
                "emotion": emotion.get("emotion", "平静"),
                "intensity": emotion.get("intensity", 5),
                "preview": diary_text[:80] + "..." if len(diary_text) > 80 else diary_text
            })
            self._write_index(index)
        return diary_id

    def get_diary(self, diary_id: str) -> dict:
        diary_file = os.path.join(self.diary_dir, f"{diary_id}.json")
        if os.path.exists(diary_file):
            with open(diary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_all_diaries(self) -> list:
        with self._lock:
            return self._read_index()

    def search_diaries(self, keyword: str) -> list:
        """按关键词搜索日记（匹配预览文本）。"""
        if not keyword:
            return []
        kw = keyword.lower()
        with self._lock:
            index = self._read_index()
        return [d for d in index if kw in (d.get("preview", "") + d.get("emotion", "")).lower()]

    def delete_diary(self, diary_id: str) -> bool:
        diary_file = os.path.join(self.diary_dir, f"{diary_id}.json")
        with self._lock:
            if os.path.exists(diary_file):
                os.remove(diary_file)
                index = self._read_index()
                index = [d for d in index if d["id"] != diary_id]
                self._write_index(index)
                return True
            return False

    def export_markdown(self, diary_id: str) -> str:
        entry = self.get_diary(diary_id)
        if not entry:
            return ""
        md = f"# 📔 心语日记 — {entry['date']}\n\n"
        md += f"> {entry['time']} · 情绪：{entry['emotion']} · 强度：{entry['intensity']}/10\n\n"
        md += f"## 今日心语\n\n{entry['user_input']}\n\n"
        md += f"---\n\n{entry['diary']}\n"
        return md

    def export_all_markdown(self) -> str:
        diaries = self.get_all_diaries()
        if not diaries:
            return "# 心语日记\n\n暂无日记记录。"
        md = "# 📔 心语日记合集\n\n"
        for d in diaries:
            entry = self.get_diary(d["id"])
            if entry:
                md += f"## {entry['date']} {entry['time']}\n\n"
                md += f"> 情绪：{entry['emotion']} · 强度：{entry['intensity']}/10\n\n"
                md += f"{entry['diary']}\n\n---\n\n"
        return md
