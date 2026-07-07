import sys
import os
import json
import asyncio
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from agents import MultiAgentOrchestrator
from diary_store import DiaryStore
from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL

# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("xinyu-diary")

app = FastAPI(title="心语日记 - 多智能体AI日记助手")

# CORS：允许所有源，但禁用 credentials（避免与通配符冲突的安全隐患）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MultiAgentOrchestrator()
diary_store = DiaryStore()

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 输入限制
MAX_MESSAGE_LENGTH = 2000


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)


@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    user_msg = request.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="消息不能为空")

    async def event_generator():
        try:
            # 1. 情绪感知
            yield _sse({"type": "progress", "agent": "emotion", "status": "working"})
            emotion_info = await asyncio.to_thread(orchestrator.emotion_agent.run, user_msg)
            yield _sse({"type": "progress", "agent": "emotion", "status": "done"})
            yield _sse({"type": "emotion", "data": emotion_info})

            # 2. 记忆检索
            yield _sse({"type": "progress", "agent": "memory", "status": "working"})
            relevant_memories = await asyncio.to_thread(orchestrator.memory_agent.search_relevant, user_msg)
            yield _sse({"type": "progress", "agent": "memory", "status": "done"})

            # 记忆保存（不阻塞主流程过久，失败不影响响应）
            await asyncio.to_thread(orchestrator.memory_agent.extract_and_save, user_msg, emotion_info)

            # 3. 日记生成
            yield _sse({"type": "progress", "agent": "diary", "status": "working"})
            diary = await asyncio.to_thread(orchestrator.diary_agent.run, user_msg, emotion_info, relevant_memories)
            yield _sse({"type": "progress", "agent": "diary", "status": "done"})
            yield _sse({"type": "diary", "data": diary})

            # 4. 对话整合
            yield _sse({"type": "progress", "agent": "dialog", "status": "working"})
            response = await asyncio.to_thread(orchestrator.dialog_agent.run, user_msg, emotion_info, diary, relevant_memories)
            yield _sse({"type": "progress", "agent": "dialog", "status": "done"})

            # 5. 持久化
            diary_id = diary_store.save_diary(user_msg, diary, emotion_info)
            orchestrator.short_memory.add("user", user_msg)
            orchestrator.short_memory.add("assistant", response)

            yield _sse({
                "type": "complete",
                "response": response,
                "emotion": emotion_info,
                "diary": diary,
                "diary_id": diary_id,
                "memories_found": len(relevant_memories)
            })
        except Exception as e:
            logger.exception("对话流处理失败")
            yield _sse({"type": "error", "message": f"处理失败：{e}"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_msg = request.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="消息不能为空")
    try:
        result = orchestrator.process(user_msg)
        diary_id = diary_store.save_diary(user_msg, result["diary"], result["emotion"])
        return {
            "response": result["response"],
            "emotion": result["emotion"],
            "diary": result["diary"],
            "diary_id": diary_id,
            "memories_found": result["memories_found"]
        }
    except Exception as e:
        logger.exception("对话处理失败")
        raise HTTPException(status_code=500, detail=f"处理失败：{e}")


@app.get("/api/diaries")
async def get_diaries():
    return {"diaries": diary_store.get_all_diaries()}


@app.get("/api/diaries/search")
async def search_diaries(keyword: str):
    """按关键词搜索日记。"""
    results = diary_store.search_diaries(keyword)
    return {"diaries": results, "total": len(results)}


@app.get("/api/diaries/{diary_id}")
async def get_diary(diary_id: str):
    entry = diary_store.get_diary(diary_id)
    if entry:
        return entry
    raise HTTPException(status_code=404, detail="Diary not found")


@app.delete("/api/diaries/{diary_id}")
async def delete_diary(diary_id: str):
    success = diary_store.delete_diary(diary_id)
    if not success:
        raise HTTPException(status_code=404, detail="Diary not found")
    return {"success": True}


@app.get("/api/diaries/{diary_id}/export")
async def export_diary(diary_id: str):
    md = diary_store.export_markdown(diary_id)
    if not md:
        raise HTTPException(status_code=404, detail="Diary not found")
    return StreamingResponse(
        iter([md]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=diary_{diary_id}.md"}
    )


@app.get("/api/diaries/export/all")
async def export_all_diaries():
    md = diary_store.export_all_markdown()
    return StreamingResponse(
        iter([md]),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=all_diaries.md"}
    )


@app.get("/api/memories")
async def get_memories():
    memories = orchestrator.get_all_memories()
    return {"memories": memories, "total": len(memories)}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
    success = orchestrator.memory_manager.forget_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}


@app.post("/api/clear_context")
async def clear_context():
    orchestrator.clear_short_memory()
    return {"success": True}


@app.get("/api/stats")
async def get_stats():
    diaries = diary_store.get_all_diaries()
    emotion_counts = {}
    total_intensity = 0
    for d in diaries:
        e = d.get("emotion", "平静")
        emotion_counts[e] = emotion_counts.get(e, 0) + 1
        total_intensity += d.get("intensity", 5)
    avg_intensity = round(total_intensity / len(diaries), 1) if diaries else 0
    memory_count = orchestrator.memory_manager.count()
    return {
        "total_diaries": len(diaries),
        "total_memories": memory_count,
        "emotion_distribution": emotion_counts,
        "avg_intensity": avg_intensity,
        "recent_diaries": diaries[:5]
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "llm_configured": bool(LLM_API_KEY),
        "llm_model": LLM_MODEL,
        "llm_base_url": LLM_BASE_URL,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
