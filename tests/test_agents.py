"""智能体编排逻辑单元测试（mock call_llm，不依赖真实 LLM）。"""
import json
from unittest.mock import patch


def test_emotion_sensor_agent_calls_analyze_emotion():
    """情绪感知器应委托给 tools.analyze_emotion。"""
    from agents import EmotionSensorAgent
    fake_emotion = {"emotion": "开心", "intensity": 9, "keywords": ["阳光"], "brief_analysis": "愉悦"}

    with patch("agents.analyze_emotion", return_value=fake_emotion) as mock_fn:
        agent = EmotionSensorAgent()
        result = agent.run("今天阳光真好")
        mock_fn.assert_called_once_with("今天阳光真好")
        assert result == fake_emotion


def test_memory_manager_agent_extract_and_save_parses_json():
    """记忆管家应将 LLM 返回的 JSON 数组解析并逐条保存。"""
    from agents import MemoryManagerAgent

    class FakeMemory:
        def __init__(self):
            self.saved = []

        def save_memory(self, content, metadata=None):
            self.saved.append((content, metadata or {}))
            return f"mid-{len(self.saved)}"

    fake_memory = FakeMemory()
    agent = MemoryManagerAgent(fake_memory)

    # LLM 返回 JSON 数组字符串
    llm_response = json.dumps(["用户喜欢散步", "用户今天去了公园"], ensure_ascii=False)
    with patch("agents.call_llm", return_value=llm_response):
        ids = agent.extract_and_save("今天去公园散步了", {"emotion": "开心"})

    assert len(ids) == 2
    assert len(fake_memory.saved) == 2
    assert fake_memory.saved[0][0] == "用户喜欢散步"
    # metadata 应携带 emotion 与 date
    assert fake_memory.saved[0][1]["emotion"] == "开心"
    assert "date" in fake_memory.saved[0][1]


def test_memory_manager_agent_handles_codeblock_wrapped_json():
    """LLM 有时会把 JSON 用 ``` 包裹，应能正确解析。"""
    from agents import MemoryManagerAgent

    class FakeMemory:
        def __init__(self):
            self.saved = []

        def save_memory(self, content, metadata=None):
            self.saved.append(content)
            return f"mid-{len(self.saved)}"

    agent = MemoryManagerAgent(FakeMemory())
    wrapped = "```json\n[\"信息1\", \"信息2\"]\n```"
    with patch("agents.call_llm", return_value=wrapped):
        ids = agent.extract_and_save("输入", {"emotion": "平静"})
    assert len(ids) == 2


def test_memory_manager_agent_returns_empty_on_llm_failure():
    """LLM 调用失败时，extract_and_save 应返回空列表而非抛异常。"""
    from agents import MemoryManagerAgent

    class FakeMemory:
        def save_memory(self, content, metadata=None):
            return "mid"

    agent = MemoryManagerAgent(FakeMemory())
    with patch("agents.call_llm", side_effect=Exception("API 不可用")):
        ids = agent.extract_and_save("输入", {"emotion": "平静"})
    assert ids == []


def test_memory_manager_agent_returns_empty_on_invalid_json():
    """LLM 返回非 JSON 时，应返回空列表。"""
    from agents import MemoryManagerAgent

    class FakeMemory:
        def save_memory(self, content, metadata=None):
            return "mid"

    agent = MemoryManagerAgent(FakeMemory())
    with patch("agents.call_llm", return_value="这不是合法JSON"):
        ids = agent.extract_and_save("输入", {"emotion": "平静"})
    assert ids == []


def test_memory_manager_agent_search_relevant_delegates():
    """search_relevant 应委托给 memory.search_memory。"""
    from agents import MemoryManagerAgent

    class FakeMemory:
        def __init__(self):
            self.calls = []

        def search_memory(self, query, n_results=5):
            self.calls.append((query, n_results))
            return [{"content": "历史记忆", "metadata": {}, "distance": 0.2}]

    fake = FakeMemory()
    agent = MemoryManagerAgent(fake)
    results = agent.search_relevant("查询词", n_results=3)
    assert len(results) == 1
    assert results[0]["content"] == "历史记忆"
    assert fake.calls == [("查询词", 3)]


def test_diary_generator_agent_delegates_to_generate_diary():
    """日记生成器应委托给 tools.generate_diary。"""
    from agents import DiaryGeneratorAgent

    with patch("agents.generate_diary", return_value="生成的日记正文") as mock_fn:
        agent = DiaryGeneratorAgent()
        diary = agent.run("用户输入", {"emotion": "平静"}, [{"content": "记忆"}])
        assert diary == "生成的日记正文"
        mock_fn.assert_called_once_with("用户输入", {"emotion": "平静"}, [{"content": "记忆"}])


def test_dialog_elf_agent_builds_prompt_and_calls_llm():
    """对话精灵应构造含情绪/日记/记忆的 prompt 并调用 LLM。"""
    from agents import DialogElfAgent

    captured = {}

    def fake_call_llm(system_prompt, user_message, temperature=0.7, max_tokens=None):
        captured["system"] = system_prompt
        captured["user"] = user_message
        captured["temperature"] = temperature
        return "温暖的回复"

    with patch("agents.call_llm", side_effect=fake_call_llm):
        agent = DialogElfAgent()
        resp = agent.run(
            "用户输入",
            {"emotion": "感动", "intensity": 8},
            "日记正文",
            [{"content": "用户上周也感动过"}],
        )

    assert resp == "温暖的回复"
    assert "感动" in captured["user"]
    assert "8" in captured["user"]
    assert "日记正文" in captured["user"]
    assert "用户上周也感动过" in captured["user"]
    assert captured["temperature"] == 0.7


def test_dialog_elf_agent_handles_empty_memories():
    """无相关记忆时，prompt 不应崩溃。"""
    from agents import DialogElfAgent

    with patch("agents.call_llm", return_value="回复"):
        agent = DialogElfAgent()
        resp = agent.run("输入", {"emotion": "平静", "intensity": 5}, "日记", [])
    assert resp == "回复"
