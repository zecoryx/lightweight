try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

import os
import time
from typing import Optional, Iterator, Dict, Any
from strategy import Strategy
from memory import MemoryManager

class InferenceEngine:
    """
    Universal Inference Engine: Automatically detects and uses 
    model-native chat templates.
    """
    def __init__(self, model_path: str, strategy: Strategy, system_instruction: Optional[str] = None):
        self.model_path = model_path
        self.strategy = strategy
        self.system_instruction = system_instruction
        self.model: Optional[Llama] = None
        self.n_threads = strategy.n_threads
        self.mem_manager = MemoryManager()

    def load(self):
        if Llama is None: raise ImportError("llama-cpp-python topilmadi.")
        cache_map = {"f16": None, "q8_0": 8, "q4_0": 2}
        cache_type_val = cache_map.get(self.strategy.kv_cache_type)

        self.model = Llama(
            model_path=self.model_path,
            n_gpu_layers=self.strategy.n_gpu_layers,
            n_ctx=self.strategy.n_ctx,
            n_threads=self.n_threads,
            use_mmap=True,
            type_k=cache_type_val,
            type_v=cache_type_val,
            flash_attn=False,
            verbose=False
        )

    def generate(self, prompt: str, image_path: Optional[str] = None, max_tokens: int = 2048) -> Iterator[Dict[str, Any]]:
        if not self.model: self.load()
        self.mem_manager.handle_context_ballooning(self.model)

        # ─── UNIVERSAL CHAT TEMPLATE ───────────────────────────
        # GGUF ichidagi tokenizer.chat_template-dan foydalanish
        try:
            messages = []
            if self.system_instruction:
                messages.append({"role": "system", "content": self.system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            # create_chat_completion avtomatik ravishda modelning o'z formatini ishlatadi
            stream = self.model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                stream=True,
                temperature=0.8,
                top_p=0.95
            )
            
            for chunk in stream:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield {"text": delta["content"]}
        except Exception:
            # Fallback: Agar template topilmasa raw mode
            for chunk in self.model(prompt, stream=True, max_tokens=max_tokens):
                yield {"text": chunk["choices"][0]["text"]}
