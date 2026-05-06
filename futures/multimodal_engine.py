import os
import time
import base64
import threading
from typing import Optional, Iterator, List, Dict, Any

# Engine Imports (Lazy loading handles missing libs)
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

class InferenceEngine:
    """
    Multimodal Engine Factory: Text, Image, and Audio management.
    """
    def __init__(self, strategy: Any):
        self.strategy = strategy
        self.text_model: Optional[Llama] = None
        self.image_model: Optional[Any] = None
        self.audio_model: Optional[Any] = None
        
        from lightweight.memory import MemoryManager
        self.mem_manager = MemoryManager()

    # ─── Text Methods (LLM) ──────────────────────────────────

    def load_text(self, model_path: str, system_instruction: Optional[str] = None):
        if Llama is None: raise ImportError("llama-cpp-python topilmadi.")
        
        # Xotirani bo'shatish (Boshqa modellarni o'chirish)
        self.unload_all(except_type="text")
        
        cache_map = {"f16": None, "q8_0": 8, "q4_0": 2}
        cache_type_val = cache_map.get(self.strategy.kv_cache_type)

        self.text_model = Llama(
            model_path=model_path,
            n_gpu_layers=self.strategy.n_gpu_layers,
            n_ctx=self.strategy.n_ctx,
            n_threads=self.strategy.n_threads,
            use_mmap=True,
            type_k=cache_type_val,
            type_v=cache_type_val,
            flash_attn=True,
            verbose=False
        )

    def chat(self, prompt: str, max_tokens: int = 512) -> Iterator[Dict[str, Any]]:
        if not self.text_model:
            raise RuntimeError("Matn modeli yuklanmagan.")
        
        self.mem_manager.handle_context_ballooning(self.text_model)
        
        # Chat Template Logic (Soddalashtirilgan)
        formatted_prompt = f"<|user|>\n{prompt}\n<|assistant|>\n"
        
        start_time = time.perf_counter()
        for chunk in self.text_model(formatted_prompt, stream=True, max_tokens=max_tokens):
            text = chunk["choices"][0]["text"]
            if text:
                yield {"text": text, "type": "text"}

    # ─── Image Methods (Stable Diffusion) ───────────────────

    def draw(self, prompt: str, width: int = 512, height: int = 512) -> str:
        """
        Rasm chizish (Ideal: LCM/Turbo orqali tezkor).
        Hozircha simulyatsiya qilingan, lekin Diffusion.cpp bilan ulanadi.
        """
        self.unload_all(except_type="image")
        print(f"Drawing: {prompt} ({width}x{height})...")
        time.sleep(2) # Simulyatsiya
        return "generated_image.png"

    # ─── Audio Methods (Whisper/TTS) ────────────────────────

    def speak(self, text: str):
        """
        Matnni ovozga aylantirish (Ideal: Piper/ONNX).
        """
        print(f"Speaking: {text}...")
        pass

    # ─── Resource Management ────────────────────────────────

    def unload_all(self, except_type: str = None):
        """
        Xotirani ideal boshqarish: Bir vaqtda faqat bitta turdagi AI faol bo'ladi.
        """
        if except_type != "text" and self.text_model:
            del self.text_model
            self.text_model = None
        
        if except_type != "image" and self.image_model:
            del self.image_model
            self.image_model = None
            
        if except_type != "audio" and self.audio_model:
            del self.audio_model
            self.audio_model = None
            
        self.mem_manager.compact()

    def generate(self, prompt: str, mode: str = "text", **kwargs) -> Any:
        """Universal Generator Entry Point."""
        if mode == "text":
            return self.chat(prompt, **kwargs)
        elif mode == "image":
            return self.draw(prompt, **kwargs)
        elif mode == "audio":
            return self.speak(prompt)
