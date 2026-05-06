try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

import psutil
import os
import base64
import threading
import queue
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
        self.n_threads = psutil.cpu_count(logical=False) or 4
        self.mem_manager = MemoryManager()
        
        # Predictive Prefetching uchun background worker
        self.prefetch_queue = queue.Queue()
        self._stop_prefetch = False
        self.prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)

    def _prefetch_worker(self):
        """
        Predictive Prefetcher: SSD-dan keyingi expertlarni oldindan o'qib keshlaydi.
        """
        while not self._stop_prefetch:
            try:
                # Navbatdagi expert manzilini kutamiz
                expert_id = self.prefetch_queue.get(timeout=1)
                if expert_id is None: break
                
                # SSD-dan RAM-ga "touch" qilish (os.read or mmap advice)
                # Bu OS darajasida faylni Page Cache-ga tortib keladi
                if os.path.exists(self.model_path):
                    with open(self.model_path, "rb") as f:
                        # MoE modellarda expertlar faylning ma'lum offsetida bo'ladi
                        # Biz butun faylni kichik bo'laklab "o'qib" chiqamiz (Async I/O simulyatsiyasi)
                        f.seek(0) # Soddalashtirilgan: miyani doim keshda saqlash
                        f.read(1024 * 1024 * 5) # 5MB prefetch
                
                self.prefetch_queue.task_done()
            except queue.Empty:
                continue

    def load(self, lora_path: Optional[str] = None, system_instruction: Optional[str] = None):
        if Llama is None:
            raise ImportError("llama-cpp-python o'rnatilmagan.")
        
        if system_instruction:
            self.system_instruction = system_instruction

        cache_map = {"f16": None, "q8_0": 8, "q4_0": 2}
        cache_type_val = cache_map.get(self.strategy.kv_cache_type)

        extra_kwargs = {}
        if self.strategy.use_expert_offloading:
            extra_kwargs["split_mode"] = 1
            if hasattr(Llama, "extra_params"):
                extra_kwargs["extra_params"] = ["-ot", "exps=CPU"]

        import sys
        old_stderr, devnull = None, None
        try:
            old_stderr = os.dup(sys.stderr.fileno())
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stderr.fileno())
        except Exception:
            pass

        try:
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
        finally:
            if old_stderr is not None and devnull is not None:
                try:
                    os.dup2(old_stderr, sys.stderr.fileno())
                    os.close(devnull)
                    os.close(old_stderr)
                except Exception:
                    pass
        
        # Prefetch threadni ishga tushirish
        if not self.prefetch_thread.is_alive():
            self.prefetch_thread.start()

    def generate(self, prompt: str, image_path: Optional[str] = None, max_tokens: int = 512) -> Iterator[Dict[str, Any]]:
        if not self.model:
            self.load()
        
        # PagedAttention v2: Har bir generatsiya oldidan xotirani tekshirish
        self.mem_manager.handle_context_ballooning()

        # Latency o'lchash boshlanishi
        start_time = time.perf_counter()
        first_token_time = None
        token_count = 0

        # Vision logic
        image_data = None
        if image_path:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Rasm topilmadi: {image_path}")
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

        # Llama-3 va Llama-3.2 uchun qat'iy Chat Template
        system_content = self.system_instruction or "You are a helpful assistant. Always respond in the user's language."
        model_path_lower = self.model_path.lower()
        if "llama-3" in model_path_lower or "llama3" in model_path_lower:
            formatted_prompt = (
                f"<|start_header_id|>system<|end_header_id|>\n\n"
                f"{system_content}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n"
                f"{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            )
            stop_tokens = ["<|eot_id|>", "<|start_header_id|>", "<|end_of_text|>"]
        else:
            formatted_prompt = f"<|system|>\n{system_content}\n<|user|>\n{prompt}\n<|assistant|>\n"
            stop_tokens = ["<|user|>", "<|end|>"]
        
        # Generatsiya boshlanishidan oldin prefetch queue-ni to'ldiramiz
        for i in range(3): self.prefetch_queue.put(i)

        stream = self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            stream=True,
            stop=stop_tokens,
            repeat_penalty=1.1,
            top_p=0.9,
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
                    "ttft": (first_token_time - start_time) * 1000, # ms
                    "itl": (current_time - first_token_time) / token_count * 1000 if token_count > 1 else 0,
                    "total_time": (current_time - start_time) * 1000
                }
                # Keyingi token uchun prefetch-ni faollashtirish
                self.prefetch_queue.put("next_chunk") 
                yield {"text": text, "latency": latency}

    def __del__(self):
        self._stop_prefetch = True
        if hasattr(self, 'prefetch_thread') and self.prefetch_thread.is_alive():
            self.prefetch_thread.join(timeout=1)
