from llm_client import call_llm
from tools import analyze_emotion, generate_diary
from memory import MemoryManager, ShortTermMemory
from config import SHORT_MEMORY_MAX_TURNS
from datetime import datetime
import json


class EmotionSensorAgent:
    name = "情绪感知器"
    description = "识别用户情绪，分析情感状态"

    def run(self, user_input: str) -> dict:
        return analyze_emotion(user_input)


class MemoryManagerAgent:
    name = "记忆管家"
    description = "管理长期记忆，提取关键信息、存储、检索、遗忘"

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    def extract_and_save(self, user_input: str, emotion_info: dict) -> list:
        system_prompt = """你是一个信息提取专家。从用户输入和情绪分析中提取值得长期记住的关键信息。
返回JSON数组，每个元素是一个字符串，表示一条关键信息。
只提取重要、值得记住的信息（如重要事件、偏好、人际关系、成就等）。
如果没有什么值得记住的，返回空数组 []。
只返回JSON数组，不要其他内容。"""

        user_message = f"用户输入：{user_input}\n情绪：{emotion_info.get('emotion', '平静')}"
        try:
            result = call_llm(system_prompt, user_message, temperature=0.3)
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            key_infos = json.loads(clean)
            saved_ids = []
            for info in key_infos:
                mid = self.memory.save_memory(
                    info,
                    metadata={
                        "emotion": emotion_info.get("emotion", "平静"),
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                )
                saved_ids.append(mid)
            return saved_ids
        except Exception:
            return []

    def search_relevant(self, user_input: str, n_results: int = 5) -> list:
        return self.memory.search_memory(user_input, n_results=n_results)


class DiaryGeneratorAgent:
    name = "日记生成器"
    description = "根据情绪和记忆生成温暖、个性化的日记"

    def run(self, user_input: str, emotion_info: dict, memories: list) -> str:
        return generate_diary(user_input, emotion_info, memories)


class DialogElfAgent:
    name = "对话精灵"
    description = "生成最终回复，协调其他智能体输出"

    def run(self, user_input: str, emotion_info: dict, diary: str, memories: list) -> str:
        from datetime import datetime
        today = datetime.now().strftime("%Y年%m月%d日")

        system_prompt = f"""你是一个温暖、贴心的日记助手。你需要根据情绪分析、生成的日记和相关记忆，
给用户一个综合性的回复。要求：
1. 先简要回应情绪（共情）
2. 呈现生成的日记（不要修改日记中的日期）
3. 如果有相关历史记忆，可以自然提及
4. 语气温暖亲切，像一个知心朋友
5. 今天是{today}，回复中提及日期时使用这个真实日期"""

        memory_text = ""
        if memories:
            items = [m["content"] for m in memories[:3]]
            memory_text = "相关记忆：\n" + "\n".join(f"- {m}" for m in items)

        user_message = f"""用户说：{user_input}
情绪状态：{emotion_info.get('emotion', '平静')}（强度：{emotion_info.get('intensity', 5)}）

生成的日记：
{diary}

{memory_text}

请给用户一个温暖的综合回复。"""

        return call_llm(system_prompt, user_message, temperature=0.7)


class MultiAgentOrchestrator:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.short_memory = ShortTermMemory(max_turns=SHORT_MEMORY_MAX_TURNS)
        self.emotion_agent = EmotionSensorAgent()
        self.memory_agent = MemoryManagerAgent(self.memory_manager)
        self.diary_agent = DiaryGeneratorAgent()
        self.dialog_agent = DialogElfAgent()

    def process(self, user_input: str) -> dict:
        self.short_memory.add("user", user_input)

        emotion_info = self.emotion_agent.run(user_input)

        relevant_memories = self.memory_agent.search_relevant(user_input)

        self.memory_agent.extract_and_save(user_input, emotion_info)

        diary = self.diary_agent.run(user_input, emotion_info, relevant_memories)

        response = self.dialog_agent.run(user_input, emotion_info, diary, relevant_memories)

        self.short_memory.add("assistant", response)

        return {
            "emotion": emotion_info,
            "diary": diary,
            "response": response,
            "memories_found": len(relevant_memories),
            "short_memory_context": self.short_memory.get_context()
        }

    def get_all_memories(self) -> list:
        return self.memory_manager.get_all_memories()

    def clear_short_memory(self):
        self.short_memory.clear()
