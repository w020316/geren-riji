import sys
import os
import json
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from agents import MultiAgentOrchestrator
from diary_store import DiaryStore

app = FastAPI(title="心语日记 - 多智能体AI日记助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MultiAgentOrchestrator()
diary_store = DiaryStore()

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        yield f"data: {json.dumps({'type': 'progress', 'agent': 'emotion', 'status': 'working'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        emotion_info = await asyncio.to_thread(orchestrator.emotion_agent.run, request.message)
        yield f"data: {json.dumps({'type': 'progress', 'agent': 'emotion', 'status': 'done'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'emotion', 'data': emotion_info}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'progress', 'agent': 'memory', 'status': 'working'}, ensure_ascii=False)}\n\n"
        relevant_memories = await asyncio.to_thread(orchestrator.memory_agent.search_relevant, request.message)
        yield f"data: {json.dumps({'type': 'progress', 'agent': 'memory', 'status': 'done'}, ensure_ascii=False)}\n\n"

        await asyncio.to_thread(orchestrator.memory_agent.extract_and_save, request.message, emotion_info)

        yield f"data: {json.dumps({'type': 'progress', 'agent': 'diary', 'status': 'working'}, ensure_ascii=False)}\n\n"
        diary = await asyncio.to_thread(orchestrator.diary_agent.run, request.message, emotion_info, relevant_memories)
        yield f"data: {json.dumps({'type': 'progress', 'agent': 'diary', 'status': 'done'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'diary', 'data': diary}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'progress', 'agent': 'dialog', 'status': 'working'}, ensure_ascii=False)}\n\n"
        response = await asyncio.to_thread(orchestrator.dialog_agent.run, request.message, emotion_info, diary, relevant_memories)
        yield f"data: {json.dumps({'type': 'progress', 'agent': 'dialog', 'status': 'done'}, ensure_ascii=False)}\n\n"

        diary_id = diary_store.save_diary(request.message, diary, emotion_info)

        orchestrator.short_memory.add("user", request.message)
        orchestrator.short_memory.add("assistant", response)

        yield f"data: {json.dumps({'type': 'complete', 'response': response, 'emotion': emotion_info, 'diary': diary, 'diary_id': diary_id, 'memories_found': len(relevant_memories)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    result = orchestrator.process(request.message)
    diary_id = diary_store.save_diary(request.message, result["diary"], result["emotion"])
    return {
        "response": result["response"],
        "emotion": result["emotion"],
        "diary": result["diary"],
        "diary_id": diary_id,
        "memories_found": result["memories_found"]
    }


@app.get("/api/diaries")
async def get_diaries():
    return {"diaries": diary_store.get_all_diaries()}


@app.get("/api/diaries/{diary_id}")
async def get_diary(diary_id: str):
    entry = diary_store.get_diary(diary_id)
    if entry:
        return entry
    return {"error": "Diary not found"}


@app.delete("/api/diaries/{diary_id}")
async def delete_diary(diary_id: str):
    success = diary_store.delete_diary(diary_id)
    return {"success": success}


@app.get("/api/diaries/{diary_id}/export")
async def export_diary(diary_id: str):
    md = diary_store.export_markdown(diary_id)
    if not md:
        return {"error": "Diary not found"}
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
    return {"memories": memories}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
    success = orchestrator.memory_manager.forget_memory(memory_id)
    return {"success": success}


@app.post("/api/clear_context")
async def clear_context():
    orchestrator.clear_short_memory()
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
