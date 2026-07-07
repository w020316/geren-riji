"""API 集成测试：使用 FastAPI TestClient + FakeOrchestrator。

覆盖所有 REST 端点的成功与错误分支。
"""
import json


# ---------- 根页面与静态资源 ----------

def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    # 应包含心语日记标题
    assert "心语日记" in resp.text or "心语" in resp.text


# ---------- /api/chat/stream (SSE) ----------

def test_chat_stream_success(client):
    with client.stream("POST", "/api/chat/stream", json={"message": "你好"}) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        events = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        # 应包含 progress / emotion / diary / complete
        types = [e.get("type") for e in events]
        assert "complete" in types
        assert "emotion" in types
        assert "diary" in types
        # complete 事件含 response
        complete = [e for e in events if e["type"] == "complete"][0]
        assert complete["response"] == "这是测试回复。"
        assert complete["diary_id"]


def test_chat_stream_empty_message_rejected(client):
    """空消息应被 Pydantic 校验拦截（422）。"""
    resp = client.post("/api/chat/stream", json={"message": ""})
    assert resp.status_code == 422


def test_chat_stream_too_long_message_rejected(client):
    """超过 2000 字应被 Pydantic 校验拦截。"""
    resp = client.post("/api/chat/stream", json={"message": "x" * 2001})
    assert resp.status_code == 422


# ---------- /api/chat (普通对话) ----------

def test_chat_success(client):
    resp = client.post("/api/chat", json={"message": "今天很开心"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "这是测试回复。"
    assert body["diary"] == "这是一篇测试日记正文。"
    assert body["emotion"]["emotion"] == "平静"
    assert body["diary_id"]


def test_chat_empty_message_rejected(client):
    resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 422


# ---------- 日记 CRUD ----------

def test_get_diaries_initially_empty(client):
    resp = client.get("/api/diaries")
    assert resp.status_code == 200
    assert resp.json() == {"diaries": []}


def test_create_then_get_diaries(client):
    # 先通过 /api/chat 触发一次日记保存
    client.post("/api/chat", json={"message": "记录一天"})
    resp = client.get("/api/diaries")
    assert resp.status_code == 200
    diaries = resp.json()["diaries"]
    assert len(diaries) == 1
    assert diaries[0]["emotion"] == "平静"


def test_get_diary_by_id(client):
    chat = client.post("/api/chat", json={"message": "获取详情"}).json()
    did = chat["diary_id"]
    resp = client.get(f"/api/diaries/{did}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == did
    assert body["user_input"] == "获取详情"


def test_get_diary_not_found(client):
    resp = client.get("/api/diaries/nonexistent_id")
    assert resp.status_code == 404
    assert resp.json()["error"] == "Diary not found"


def test_delete_diary_success(client):
    chat = client.post("/api/chat", json={"message": "待删除日记"}).json()
    did = chat["diary_id"]
    resp = client.delete(f"/api/diaries/{did}")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    # 再查应 404
    assert client.get(f"/api/diaries/{did}").status_code == 404


def test_delete_diary_not_found(client):
    resp = client.delete("/api/diaries/nonexistent_id")
    assert resp.status_code == 404


# ---------- 搜索 ----------

def test_search_diaries(client):
    client.post("/api/chat", json={"message": "公园散步"})
    client.post("/api/chat", json={"message": "工作汇报"})
    # 搜索 "公园"
    resp = client.get("/api/diaries/search", params={"keyword": "公园"})
    assert resp.status_code == 200
    body = resp.json()
    # 至少 1 条（预览含日记正文，但 fake diary 正文是固定字符串，所以可能匹配不到 "公园"）
    # 这里仅验证接口可用且返回结构正确
    assert "diaries" in body
    assert "total" in body
    assert body["total"] == len(body["diaries"])


def test_search_diaries_empty_keyword(client):
    """空关键词应返回空（接口层未做 422，DiaryStore 返回 []）。"""
    resp = client.get("/api/diaries/search", params={"keyword": ""})
    assert resp.status_code == 200
    assert resp.json()["diaries"] == []


# ---------- 导出 ----------

def test_export_single_diary(client):
    chat = client.post("/api/chat", json={"message": "导出测试"}).json()
    did = chat["diary_id"]
    resp = client.get(f"/api/diaries/{did}/export")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers.get("content-type", "")
    assert "📔 心语日记" in resp.text
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_export_single_not_found(client):
    resp = client.get("/api/diaries/nonexistent/export")
    assert resp.status_code == 404


def test_export_all_diaries(client):
    client.post("/api/chat", json={"message": "导出全部1"})
    resp = client.get("/api/diaries/export/all")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")


# ---------- 记忆管理 ----------

def test_get_memories(client):
    resp = client.get("/api/memories")
    assert resp.status_code == 200
    body = resp.json()
    assert "memories" in body
    assert body["total"] == len(body["memories"])
    # FakeOrchestrator 预置 2 条
    assert body["total"] == 2


def test_delete_memory_success(client):
    resp = client.delete("/api/memories/m1")
    assert resp.status_code == 200
    # 删除后总数应减少
    after = client.get("/api/memories").json()
    assert after["total"] == 1


def test_delete_memory_not_found(client):
    resp = client.delete("/api/memories/nonexistent_mid")
    assert resp.status_code == 404


# ---------- 短期记忆 ----------

def test_clear_context(client):
    resp = client.post("/api/clear_context")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}


# ---------- 统计 ----------

def test_stats_empty(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_diaries"] == 0
    assert body["total_memories"] == 2  # FakeOrchestrator 预置
    assert body["emotion_distribution"] == {}
    assert body["avg_intensity"] == 0
    assert body["recent_diaries"] == []


def test_stats_after_some_diaries(client):
    client.post("/api/chat", json={"message": "日记1"})
    client.post("/api/chat", json={"message": "日记2"})
    resp = client.get("/api/stats")
    body = resp.json()
    assert body["total_diaries"] == 2
    assert body["total_memories"] == 2
    # FakeOrchestrator 情绪固定为 "平静"，强度 5
    assert body["emotion_distribution"] == {"平静": 2}
    assert body["avg_intensity"] == 5.0
    assert len(body["recent_diaries"]) == 2


# ---------- 健康检查 ----------

def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body
    assert "llm_configured" in body
    assert "llm_model" in body
    assert "llm_base_url" in body
