"""ShortTermMemory 单元测试。

注：MemoryManager 依赖 ChromaDB + SentenceTransformer，启动成本高，
其集成测试在 test_api.py 中通过 FakeOrchestrator 间接覆盖。
"""
from datetime import datetime


def test_add_and_get_context(short_memory):
    short_memory.add("user", "你好")
    short_memory.add("assistant", "你好呀")

    ctx = short_memory.get_context()
    assert "用户: 你好" in ctx
    assert "助手: 你好呀" in ctx


def test_empty_memory_context(short_memory):
    assert short_memory.get_context() == ""


def test_max_turns_trims_old_messages(short_memory):
    """max_turns=3，每轮 user+assistant 共 2 条，最多保留 6 条。"""
    for i in range(10):
        short_memory.add("user", f"u{i}")
        short_memory.add("assistant", f"a{i}")

    # 最多保留 max_turns * 2 = 6 条
    assert len(short_memory.messages) == 6
    # 保留的是最后 6 条（即 u7 u8 u9 a7 a8 a9，按 append 顺序）
    contents = [m["content"] for m in short_memory.messages]
    assert "u7" in contents
    assert "u9" in contents
    assert "u0" not in contents


def test_clear_resets_messages(short_memory):
    short_memory.add("user", "test")
    assert len(short_memory.messages) == 1
    short_memory.clear()
    assert short_memory.messages == []
    assert short_memory.get_context() == ""


def test_message_has_timestamp(short_memory):
    short_memory.add("user", "时间检查")
    msg = short_memory.messages[-1]
    assert "timestamp" in msg
    # 时间戳格式可被 ISO 解析
    datetime.fromisoformat(msg["timestamp"])
