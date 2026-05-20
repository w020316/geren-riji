import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agents import MultiAgentOrchestrator

app = FastAPI(title="心语日记 - 多智能体AI日记助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MultiAgentOrchestrator()

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    result = orchestrator.process(request.message)
    return {
        "response": result["response"],
        "emotion": result["emotion"],
        "diary": result["diary"],
        "memories_found": result["memories_found"]
    }


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
