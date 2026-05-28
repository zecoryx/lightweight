import os
import re
import contextlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ModelMetadata:
    path: str
    architecture: Optional[str] = None
    name: Optional[str] = None
    n_ctx_train: Optional[int] = None
    n_layer: Optional[int] = None
    n_embd: Optional[int] = None
    n_params: Optional[int] = None
    quant: Optional[str] = None
    is_moe: bool = False
    expert_count: Optional[int] = None
    expert_used_count: Optional[int] = None
    source: str = "fallback"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_quant_from_name(path: str) -> Optional[str]:
    name = os.path.basename(path).upper()
    match = re.search(r"(IQ\d_[A-Z0-9]+|Q\d_K_[MSL]|Q\d_\d|Q\d_[A-Z0-9]+)", name)
    return match.group(1) if match else None


def read_model_metadata(path: str) -> ModelMetadata:
    metadata = ModelMetadata(path=path, quant=_parse_quant_from_name(path))
    try:
        from llama_cpp import llama_model_default_params, llama_model_load_from_file, llama_model_free
        import llama_cpp

        params = llama_model_default_params()
        with _suppress_native_logs():
            model = llama_model_load_from_file(path.encode("utf-8"), params)
            if not model:
                return metadata

            try:
                metadata.source = "llama_cpp"
                metadata.n_params = int(llama_cpp.llama_model_n_params(model))
                metadata.n_layer = int(llama_cpp.llama_model_n_layer(model))
                metadata.n_ctx_train = int(llama_cpp.llama_model_n_ctx_train(model))
                metadata.n_embd = int(llama_cpp.llama_model_n_embd(model))
                metadata.architecture = _get_model_meta(model, "general.architecture")
                metadata.name = _get_model_meta(model, "general.name")
                expert_count = (
                    _get_model_meta(model, "llama.expert_count")
                    or _get_model_meta(model, "qwen2moe.expert_count")
                    or _get_model_meta(model, "qwen3moe.expert_count")
                )
                expert_used_count = (
                    _get_model_meta(model, "llama.expert_used_count")
                    or _get_model_meta(model, "qwen2moe.expert_used_count")
                    or _get_model_meta(model, "qwen3moe.expert_used_count")
                )
                metadata.expert_count = _safe_int(expert_count)
                metadata.expert_used_count = _safe_int(expert_used_count)
                metadata.is_moe = bool(metadata.expert_count and metadata.expert_count > 0)
            finally:
                llama_model_free(model)
    except Exception:
        pass
    return metadata


@contextlib.contextmanager
def _suppress_native_logs():
    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        try:
            yield
        finally:
            os.dup2(stdout_fd, 1)
            os.dup2(stderr_fd, 2)
            os.close(stdout_fd)
            os.close(stderr_fd)
            os.close(devnull_fd)
    except Exception:
        yield


def _get_model_meta(model, key: str) -> Optional[str]:
    try:
        import ctypes
        import llama_cpp

        buf = ctypes.create_string_buffer(2048)
        result = llama_cpp.llama_model_meta_val_str(model, key.encode("utf-8"), buf, len(buf))
        if result < 0:
            return None
        return buf.value.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _safe_int(value: Optional[str]) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None
