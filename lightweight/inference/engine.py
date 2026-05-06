try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

import psutil
import os
import base64
import time
from typing import Optional, Iterator, List, Dict, Any
from lightweight.strategy import Strategy
from lightweight.memory import MemoryManager

class InferenceEngine:
    def __init__(self, model_path: str, strategy: Strategy, system_instruction: Optional[str] = None):
        self.model_path = model_path
        self.strategy = strategy
        self.system_instruction = system_instruction
        self.model: Optional[Llama] = None
        self.n_threads = strategy.n_threads
        self.mem_manager = MemoryManager()

    def load(self, lora_path: Optional[str] = None, system_instruction: Optional[str] = None):
        if Llama is None:
            raise ImportError("llama-cpp-python o'rnatilmagan.")
        
        if system_instruction:
            self.system_instruction = system_instruction

        cache_map = {"f16": None, "q8_0": 8, "q4_0": 2}
        cache_type_val = cache_map.get(self.strategy.kv_cache_type)

        try:
            self.model = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.strategy.n_gpu_layers,
                n_ctx=self.strategy.n_ctx,
                n_threads=self.n_threads,
                n_batch=512,
                use_mmap=True,
                use_mlock=self.strategy.use_mlock,
                type_k=cache_type_val,
                type_v=cache_type_val,
                lora_path=lora_path, 
                flash_attn=True,
                verbose=False
            )
        except Exception as e:
            raise RuntimeError(f"Modelni yuklashda xato: {e}")

    def generate(self, prompt: str, image_path: Optional[str] = None, max_tokens: int = 512) -> Iterator[Dict[str, Any]]:
        if not self.model:
            self.load()
        
        self.mem_manager.handle_context_ballooning(self.model)

        start_time = time.perf_counter()
        first_token_time = None
        token_count = 0

        # Llama-3 Chat Template
        system_content = self.system_instruction or "You are a helpful assistant."
        formatted_prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{system_content}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        
        stream = self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            stream=True,
            stop=["<|eot_id|>"],
            temperature=0.7
        )
        
        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            
            text = chunk["choices"][0]["text"]
            if text:
                token_count += 1
                current_time = time.perf_counter()
                latency = {
                    "ttft": (first_token_time - start_time) * 1000,
                    "itl": (current_time - first_token_time) / token_count * 1000 if token_count > 1 else 0
                }
                yield {"text": text, "latency": latency}
