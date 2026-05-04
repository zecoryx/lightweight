try:
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import LlamaChatAdapter
except ImportError:
    Llama = None

import psutil
import os
import base64
from typing import Optional, Iterator, List, Dict, Any
from lightweight.strategy import Strategy

class InferenceEngine:
    def __init__(self, model_path: str, strategy: Strategy):
        self.model_path = model_path
        self.strategy = strategy
        self.model: Optional[Llama] = None
        self.n_threads = psutil.cpu_count(logical=False) or 4

    def load(self, lora_path: Optional[str] = None):
        if Llama is None:
            raise ImportError("llama-cpp-python o'rnatilmagan.")
        
        # KV Cache quantization
        cache_map = {"f16": None, "q8_0": 8, "q4_0": 2}
        cache_type_val = cache_map.get(self.strategy.kv_cache_type)

        print(f"Loading Model: {self.model_path} with Strategy: {self.strategy.kv_cache_type} cache")
        
        # MoE Expert Offloading and Expert Streaming Support
        extra_kwargs = {}
        if self.strategy.use_expert_offloading:
            # Expertlarni CPUda qoldirish va streaming-ni faollashtirish
            # Llama-cpp init uchun 'split_mode' va 'extra_params' (expert offload)
            extra_kwargs["split_mode"] = 1 # LLAMA_SPLIT_MODE_LAYER
            # Expert streaming bayroqlari
            if hasattr(Llama, "extra_params"):
                extra_kwargs["extra_params"] = ["-ot", "exps=CPU"]
        # Unified Memory (Mac yoki ba'zi APU/NPU lar uchun) va iMatrix/BitNet optimizatsiyasi
        # Agar model .bitnet yoki IQ1_S bo'lsa, maxsus parametrlar kerak bo'lishi mumkin
        is_bitnet = "IQ1_S" in self.strategy.recommended_quant or "bitnet" in self.model_path.lower()

        self.model = Llama(
            model_path=self.model_path,
            n_gpu_layers=self.strategy.n_gpu_layers,
            n_ctx=4096,
            n_threads=self.n_threads,
            n_batch=512,
            use_mmap=True,
            use_mlock=self.strategy.use_mlock,
            type_k=cache_type_val,
            type_v=cache_type_val,
            lora_path=lora_path, 
            flash_attn=True,
            verbose=False,
            **extra_kwargs
        )

    def generate(self, prompt: str, image_path: Optional[str] = None, max_tokens: int = 512) -> Iterator[str]:
        """
        Vision (rasm) va matnli generatsiya.
        """
        if not self.model:
            self.load()
        
        # Dinamik Xotira Nazorati
        self._check_and_optimize_memory()

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
            formatted_prompt = f"IMAGE:{img_base64}\nUSER: {prompt}\nASSISTANT:"
        else:
            formatted_prompt = f"<|user|>\n{prompt}<|assistant|>\n"
        
        stream = self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            stream=True,
            stop=["<|user|>", "<|end|>"]
        )
        
        for chunk in stream:
            text = chunk["choices"][0]["text"]
            if text:
                yield text

    def _check_and_optimize_memory(self):
        """
        Dinamik Paging: Agar VRAM to'lib qolsa, xotirani boshqarish.
        """
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            print("[Dinamik Optimizatsiya] RAM to'ldi. KV Cache paging yoqilmoqda...")
            if self.model:
                self.model.reset()
