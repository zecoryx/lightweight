try:
    from llama_cpp import Llama
    import llama_cpp
except ImportError:
    Llama = None
    llama_cpp = None

import os
import inspect
import threading
import time
import contextlib
from typing import Optional, Iterator, Dict, Any, List

# ─── ROBUST INTERNAL IMPORTS ────────────────────────────────
try:
    from memory import MemoryManager
    from strategy import Strategy
    from runtime_policy import next_recovery_strategy, adapt_after_generation
except ImportError:
    try:
        from cli.memory import MemoryManager
        from cli.strategy import Strategy
        from cli.runtime_policy import next_recovery_strategy, adapt_after_generation
    except ImportError:
        # Final fallback for deep nested structures
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from memory import MemoryManager
        from strategy import Strategy
        from runtime_policy import next_recovery_strategy, adapt_after_generation

class InferenceEngine:
    """
    Universal Inference Engine: Automatically detects and uses 
    model-native chat templates.
    """
    def __init__(self, model_path: str, strategy: Strategy, system_instruction: Optional[str] = None):
        self.model_path = model_path
        self.strategy = strategy
        self._disable_unsupported_gpu_offload()
        self.system_instruction = system_instruction
        self.model: Optional[Llama] = None
        self.n_threads = strategy.n_threads
        self.mem_manager = MemoryManager()
        self.generation_lock = threading.Lock()

    def _disable_unsupported_gpu_offload(self):
        if llama_cpp is None or self.strategy.n_gpu_layers <= 0:
            return
        support_fn = getattr(llama_cpp, "llama_supports_gpu_offload", None)
        if callable(support_fn) and not support_fn():
            self.strategy.n_gpu_layers = 0
            self.strategy.offload_kqv = False
            self.strategy.op_offload = None

    def load(self, lora_path: Optional[str] = None):
        if Llama is None: raise ImportError("llama-cpp-python topilmadi.")
        strategy = self.strategy
        errors = []
        for step in range(6):
            self.strategy = strategy
            cache_type_val = self._cache_type_value(self.strategy.kv_cache_type)
            try:
                with self._suppress_llama_stderr():
                    self.model = Llama(**self._llama_kwargs(cache_type_val, lora_path))
                return
            except Exception as exc:
                errors.append(str(exc))
                strategy = next_recovery_strategy(strategy, step)
                if strategy is None:
                    break
        raise RuntimeError(f"Model load error after recovery attempts: {' | '.join(errors[-3:])}")

    @contextlib.contextmanager
    def _suppress_llama_stderr(self):
        if os.environ.get("LIGHTWEIGHT_LLAMA_LOGS") == "1":
            yield
            return
        stdout_fd = 1
        stderr_fd = 2
        saved_stdout_fd = os.dup(stdout_fd)
        saved_stderr_fd = os.dup(stderr_fd)
        try:
            with open(os.devnull, "w") as devnull:
                os.dup2(devnull.fileno(), stdout_fd)
                os.dup2(devnull.fileno(), stderr_fd)
                yield
        finally:
            os.dup2(saved_stdout_fd, stdout_fd)
            os.dup2(saved_stderr_fd, stderr_fd)
            os.close(saved_stdout_fd)
            os.close(saved_stderr_fd)

    def _cache_type_value(self, cache_type: str):
        if llama_cpp is None:
            return None
        cache_map = {
            "f16": getattr(llama_cpp, "GGML_TYPE_F16", None),
            "q8_0": getattr(llama_cpp, "GGML_TYPE_Q8_0", None),
            "q4_0": getattr(llama_cpp, "GGML_TYPE_Q4_0", None),
        }
        return cache_map.get((cache_type or "f16").lower())

    def _llama_kwargs(self, cache_type_val, lora_path: Optional[str]) -> Dict[str, Any]:
        split_mode = self._split_mode_value(self.strategy.split_mode)
        kwargs: Dict[str, Any] = {
            "model_path": self.model_path,
            "n_gpu_layers": self.strategy.n_gpu_layers,
            "split_mode": split_mode,
            "main_gpu": self.strategy.main_gpu,
            "tensor_split": self.strategy.tensor_split,
            "n_ctx": self.strategy.n_ctx,
            "n_batch": self.strategy.n_batch,
            "n_ubatch": self.strategy.n_ubatch,
            "n_threads": self.n_threads,
            "n_threads_batch": self.strategy.n_threads_batch,
            "use_mmap": self.strategy.use_mmap,
            "use_mlock": self.strategy.use_mlock,
            "offload_kqv": self.strategy.offload_kqv and self.strategy.n_gpu_layers > 0,
            "op_offload": self.strategy.op_offload,
            "swa_full": self.strategy.swa_full,
            "numa": self.strategy.numa,
            "type_k": cache_type_val,
            "type_v": cache_type_val,
            "lora_path": lora_path,
            "flash_attn": self.strategy.flash_attn,
            "verbose": False,
        }
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        signature = inspect.signature(Llama.__init__)
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
            return kwargs
        return {key: value for key, value in kwargs.items() if key in signature.parameters}

    def _split_mode_value(self, split_mode: str):
        if llama_cpp is None:
            return None
        normalized = (split_mode or "layer").lower()
        mapping = {
            "none": getattr(llama_cpp, "LLAMA_SPLIT_MODE_NONE", None),
            "layer": getattr(llama_cpp, "LLAMA_SPLIT_MODE_LAYER", None),
            "row": getattr(llama_cpp, "LLAMA_SPLIT_MODE_ROW", None),
        }
        return mapping.get(normalized, mapping["layer"])

    def generate(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        max_tokens: int = 2048,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Iterator[Dict[str, Any]]:
        if not self.model: self.load()
        self.mem_manager.handle_context_ballooning(self.model)
        usage_before = self.mem_manager.get_current_usage().get("rss", 0)
        started = time.perf_counter()
        token_count = 0

        try:
            chat_messages = messages or []
            if not chat_messages:
                if self.system_instruction:
                    chat_messages.append({"role": "system", "content": self.system_instruction})
                chat_messages.append({"role": "user", "content": prompt})
            
            stream = self.model.create_chat_completion(
                messages=chat_messages,
                max_tokens=max_tokens,
                stream=True,
                temperature=0.7
            )
            
            for chunk in stream:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        token_count += 1
                        yield {"text": delta["content"]}
        except Exception:
            fallback_prompt = prompt
            if messages:
                fallback_prompt = "\n".join(
                    f"{message.get('role', 'user')}: {message.get('content', '')}"
                    for message in messages
                )
            for chunk in self.model(fallback_prompt, stream=True, max_tokens=max_tokens):
                token_count += 1
                yield {"text": chunk["choices"][0]["text"]}
        finally:
            elapsed = max(time.perf_counter() - started, 0.001)
            usage_after = self.mem_manager.get_current_usage().get("rss", usage_before)
            self.strategy = adapt_after_generation(
                self.strategy,
                ram_delta_mb=max(0, usage_after - usage_before),
                tokens_per_second=token_count / elapsed,
            )
