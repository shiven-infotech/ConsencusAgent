import os
import threading
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.coach import (
    generate_coaching_prompt,
    evaluate_user_response,
    GeneratedPrompt,
    EvaluationResult,
    analyze_convo_turn,
    ConvoAnalysisResponse
)
from src.tg_bot import bot, IS_BOT_DUMMY

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run Telegram Bot polling in a background thread if credentials are set
    bot_thread = None
    if bot and not IS_BOT_DUMMY:
        print("Starting Telegram bot polling in a background thread...")
        bot_thread = threading.Thread(target=bot.infinity_polling, daemon=True)
        bot_thread.start()
    else:
        print("Telegram bot not starting (missing TELEGRAM_BOT_TOKEN).")
    
    yield
    
    # Shutdown: Stop polling if it was running
    if bot and bot_thread:
        print("Stopping Telegram bot polling...")
        bot.stop_polling()

app = FastAPI(title="Humor & Misinterpretation Coach API", lifespan=lifespan)

# Configure CORS for React frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Schemas

class ChatMessage(BaseModel):
    role: str
    content: str

class ConvoReplyRequest(BaseModel):
    history: List[ChatMessage]

class NextPromptRequest(BaseModel):
    difficulty: str
    category: str
    history: List[str] = []

class EvaluateRequest(BaseModel):
    prompt_text: str
    context_hint: str
    user_response: str
    allowed_styles: List[str] = []

@app.post("/api/session/next", response_model=GeneratedPrompt)
async def get_next_prompt(req: NextPromptRequest):
    try:
        # Standardize difficulty and category
        difficulty = req.difficulty.lower().strip()
        category = req.category.lower().strip()
        if difficulty not in ["simple", "intermediate", "expert"]:
            difficulty = "simple"
        
        prompt_data = generate_coaching_prompt(difficulty, category, req.history)
        return prompt_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/evaluate", response_model=EvaluationResult)
async def evaluate_response(req: EvaluateRequest):
    try:
        if not req.prompt_text or not req.user_response:
            raise HTTPException(status_code=400, detail="Prompt text and user response are required.")
        
        evaluation = evaluate_user_response(
            prompt_text=req.prompt_text,
            context_hint=req.context_hint,
            user_response=req.user_response,
            allowed_styles=req.allowed_styles
        )
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/convo/reply", response_model=ConvoAnalysisResponse)
async def convo_reply(req: ConvoReplyRequest):
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in req.history]
        analysis = analyze_convo_turn(history_dicts)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static frontend files if they exist
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
else:
    @app.get("/")
    async def index():
        return {"status": "backend running", "message": "Frontend build not found. Run dev servers separately."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
