try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

import os
import time
from typing import Optional, Iterator, Dict, Any
from lightweight.strategy import Strategy
from lightweight.memory import MemoryManager

class InferenceEngine:
    """
    Pure Inference Engine: No hardcoded personality.
    Purely focused on speed, compression, and stability.
    """
    def __init__(self, model_path: str, strategy: Strategy, system_instruction: Optional[str] = None):
        self.model_path = model_path
        self.strategy = strategy
        self.system_instruction = system_instruction # Foydalanuvchi bergan buyruq (optional)
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

    def generate(self, prompt: str, max_tokens: int = 2048) -> Iterator[Dict[str, Any]]:
        if not self.model: self.load()
        self.mem_manager.handle_context_ballooning(self.model)

        # ─── FREE PROMPT LOGIC ──────────────────────────────────
        # Biz modelga "bunday javob ber" deb buyruq bermaymiz.
        # Faqatgina chat strukturasini saqlaymiz (erkin muloqot uchun).
        
        m_path = self.model_path.lower()
        if "llama-3" in m_path or "llama3" in m_path:
            # Llama-3 Native format (shaxsiyatsiz)
            formatted_prompt = ""
            if self.system_instruction:
                formatted_prompt += f"<|start_header_id|>system<|end_header_id|>\n\n{self.system_instruction}<|eot_id|>"
            formatted_prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            stop_tokens = ["<|eot_id|>", "<|start_header_id|>"]
        else:
            # Universal format
            formatted_prompt = ""
            if self.system_instruction:
                formatted_prompt += f"System: {self.system_instruction}\n\n"
            formatted_prompt += f"User: {prompt}\nAssistant: "
            stop_tokens = ["User:", "</s>"]

        try:
            stream = self.model(
                formatted_prompt,
                max_tokens=max_tokens,
                stream=True,
                stop=stop_tokens,
                temperature=0.8, # Ko'proq erkinlik uchun biroz yuqori temp
                top_p=0.95,
                repeat_penalty=1.1
            )
            
            for chunk in stream:
                text = chunk["choices"][0]["text"]
                if text:
                    yield {"text": text}
        except Exception as e:
            yield {"text": f"\n[Error]: {str(e)}"}
