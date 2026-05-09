try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

import os
import time
from typing import Optional, Iterator, Dict, Any

# Relative imports for package consistency
from .memory import MemoryManager

class InferenceEngine:
    def __init__(self, model_path: str, strategy: Any, system_instruction: Optional[str] = None):
        self.model_path = model_path
        self.strategy = strategy
        self.system_instruction = system_instruction
        self.model: Optional[Llama] = None
        self.n_threads = strategy.n_threads
        self.mem_manager = MemoryManager()

    def load(self, lora_path: Optional[str] = None):
        """Modelni xotiraga yuklash (LoRA qo'llab-quvvatlanadi)."""
        if Llama is None: raise ImportError("llama-cpp-python topilmadi.")
        
        cache_map = {"f16": None, "q8_0": 8, "q4_0": 2}
        cache_type_val = cache_map.get(self.strategy.kv_cache_type)

        try:
            self.model = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.strategy.n_gpu_layers,
                n_ctx=self.strategy.n_ctx,
                n_threads=self.n_threads,
                use_mmap=True,
                type_k=cache_type_val,
                type_v=cache_type_val,
                lora_path=lora_path, # API talab qilgan parametr
                flash_attn=False,
                verbose=False
            )
        except Exception as e:
            raise RuntimeError(f"Model load error: {e}")

    def generate(self, prompt: str, max_tokens: int = 2048) -> Iterator[Dict[str, Any]]:
        if not self.model: self.load()
        self.mem_manager.handle_context_ballooning(self.model)

        try:
            # GGUF ichidagi shablonni ishlatish (Jinja2 kerak!)
            messages = []
            if self.system_instruction:
                messages.append({"role": "system", "content": self.system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            stream = self.model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                stream=True,
                temperature=0.7
            )
            
            for chunk in stream:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield {"text": delta["content"]}
        except Exception:
            # Fallback: Agar template yoki jinja2 xato bersa raw mode
            for chunk in self.model(prompt, stream=True, max_tokens=max_tokens):
                yield {"text": chunk["choices"][0]["text"]}
