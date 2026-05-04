from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from collections import OrderedDict
from lightweight.inference import InferenceEngine
from lightweight.models import ModelManager
from lightweight.hardware import Detector
from lightweight.strategy import StrategyEngine
import os
import time
import logging

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LightWeightAPI")

app = FastAPI(title="LightWeight Production API")

# LRU Cache for Engines (Maksimal 3 ta model xotirada)
class EngineCache:
    def __init__(self, capacity: int = 2):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key: str) -> Optional[InferenceEngine]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: InferenceEngine):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            # Eng kam ishlatilgan modelni o'chiramiz
            old_key, old_engine = self.cache.popitem(last=False)
            logger.info(f"Evicting model from cache: {old_key}")
            del old_engine

engine_cache = EngineCache(capacity=2)

class ChatRequest(BaseModel):
    model: str
    messages: List[dict]
    lora: Optional[str] = None
    stream: bool = False
    max_tokens: int = 512

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    model_name = request.model
    engine = engine_cache.get(model_name)
    
    if not engine:
        manager = ModelManager()
        model_path = manager.get_model_path(model_name)
        if not model_path:
            # Qisman qidiruv
            local_models = manager.list_local_models()
            for m in local_models:
                if model_name.lower() in m["name"].lower():
                    model_path = m["path"]
                    model_name = m["name"]
                    break
        
        if not model_path:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' topilmadi.")

        detector = Detector()
        report = detector.get_report()
        model_info = manager.registry.get(model_name, {})
        is_moe = model_info.get("is_moe", False)
        model_size = os.path.getsize(model_path) // (1024 * 1024)
        
        strategy = StrategyEngine(report).determine_strategy(
            model_size, 
            model_name=model_name, 
            is_moe=is_moe
        )
        
        logger.info(f"Loading engine for {model_name}...")
        engine = InferenceEngine(model_path, strategy)
        engine.load(lora_path=request.lora)
        engine_cache.put(model_name, engine)

    prompt = request.messages[-1]["content"]

    if request.stream:
        async def event_generator():
            for chunk in engine.generate(prompt, max_tokens=request.max_tokens):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    full_text = "".join(list(engine.generate(prompt, max_tokens=request.max_tokens)))
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{"message": {"role": "assistant", "content": full_text}, "index": 0, "finish_reason": "stop"}]
    }

@app.get("/v1/models")
async def list_models():
    manager = ModelManager()
    return {"data": manager.list_local_models()}

@app.get("/health")
async def health_check():
    detector = Detector()
    return {"status": "ok", "hardware": detector.get_report()}
