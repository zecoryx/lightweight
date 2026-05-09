import os
import sys
import time
import logging
import asyncio
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from collections import OrderedDict

# Package relative imports for EXE stability
from .inference import InferenceEngine
from .models import ModelManager
from .hardware import Detector
from .strategy import StrategyEngine

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LightWeightAPI")

app = FastAPI(title="LightWeight Production API")
inference_lock = asyncio.Lock()

# LRU Cache
class EngineCache:
    def __init__(self, capacity: int = 2):
        self.cache = OrderedDict()
        self.capacity = capacity
    def get(self, key: str):
        if key not in self.cache: return None
        self.cache.move_to_end(key); return self.cache[key]
    def put(self, key: str, value: InferenceEngine):
        if key in self.cache: self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            old_key, old_engine = self.cache.popitem(last=False)
            if hasattr(old_engine, 'mem_manager'): old_engine.mem_manager.compact(old_engine.model)

engine_cache = EngineCache(capacity=1) # 4GB RAM uchun xavfsizroq

class ChatRequest(BaseModel):
    model: str
    messages: List[dict]
    lora: Optional[str] = None
    stream: bool = False
    max_tokens: int = 512

@app.get("/")
async def root():
    return {"status": "running", "api": "OpenAI Compatible", "version": "0.1.0"}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    async with inference_lock:
        model_name = request.model
        engine = engine_cache.get(model_name)
        
        if not engine:
            manager = ModelManager()
            model_path = manager.get_model_path(model_name)
            if not model_path:
                for m in manager.list_local_models():
                    if model_name.lower() in m["name"].lower():
                        model_path, model_name = m["path"], m["name"]; break
            
            if not model_path: raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

            detector = Detector(); report = detector.get_report()
            model_size = os.path.getsize(model_path) // (1024 * 1024)
            strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model_name)
            
            engine = InferenceEngine(model_path, strategy)
            engine.load(lora_path=request.lora) # Fixed Signature!
            engine_cache.put(model_name, engine)

        prompt = request.messages[-1]["content"]

        if request.stream:
            async def event_generator():
                try:
                    for chunk in engine.generate(prompt, max_tokens=request.max_tokens):
                        # Proper OpenAI Stream Format
                        data = {
                            "choices": [{"delta": {"content": chunk["text"]}, "index": 0, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return StreamingResponse(event_generator(), media_type="text/event-stream")

        full_text = ""
        for chunk in engine.generate(prompt, max_tokens=request.max_tokens):
            full_text += chunk["text"]
                
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "model": model_name,
            "choices": [{"message": {"role": "assistant", "content": full_text}, "index": 0, "finish_reason": "stop"}]
        }
