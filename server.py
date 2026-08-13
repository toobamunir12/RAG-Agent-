"""
Thin API layer over rag_agent.ask() so the React frontend has something to talk to.
Doesn't touch the agent logic in rag_agent.py / ingestion_pipeline.py at all.

Run with:
    uvicorn server:app --reload --port 8000
"""

import logging
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from ingestion_pipeline import CHROMA_PATH, COLLECTION_NAME  # noqa: E402
from rag_agent import ask  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uet-rag-api")

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"

app = FastAPI(title="UET Mardan Prospectus RAG API")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


@app.on_event("startup")
async def check_index():
    """Warn early (in logs) if nobody has run ingestion_pipeline.py yet."""
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        client.get_collection(COLLECTION_NAME)
        logger.info("Chroma collection '%s' found at %s", COLLECTION_NAME, CHROMA_PATH)
    except Exception:
        logger.warning(
            "Chroma collection '%s' not found at %s. "
            "Run `python ingestion_pipeline.py --source <your_prospectus.pdf>` first.",
            COLLECTION_NAME,
            CHROMA_PATH,
        )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/")
async def serve_index():
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "frontend build not found"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        answer = await ask(question)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the UI
        logger.exception("Agent failed to answer question")
        raise HTTPException(
            status_code=500,
            detail=(
                "The agent couldn't answer that. If you haven't indexed the "
                "prospectus yet, run ingestion_pipeline.py first. "
                f"(details: {exc})"
            ),
        ) from exc

    return ChatResponse(answer=answer)


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "frontend build not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
