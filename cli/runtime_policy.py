from dataclasses import replace
from typing import Optional, Dict, Any

try:
    from strategy import Strategy
    from metadata import ModelMetadata
except ImportError:
    from cli.strategy import Strategy
    from cli.metadata import ModelMetadata


def apply_metadata(strategy: Strategy, metadata: Optional[ModelMetadata], user_ctx: Optional[int] = None) -> Strategy:
    if not metadata:
        return strategy
    updated = replace(strategy)
    if metadata.n_layer:
        updated.model_layers = metadata.n_layer
        updated.n_gpu_layers = min(updated.n_gpu_layers, metadata.n_layer)
    if metadata.is_moe:
        updated.use_expert_offloading = True
        if updated.moe_offload == "off":
            updated.moe_offload = "first-n"
        if metadata.n_layer and updated.n_cpu_moe is None:
            updated.n_cpu_moe = max(1, min(metadata.n_layer, int(metadata.n_layer * 0.50)))
        updated.active_set_policy = "moe-experts+kv"
    requested_ctx = user_ctx or updated.n_ctx
    if metadata.n_ctx_train and requested_ctx > metadata.n_ctx_train and not updated.long_context:
        requested_ctx = metadata.n_ctx_train
    updated.n_ctx = max(128, requested_ctx)
    return updated


def auto_profile_needed(profile: Optional[Dict[str, Any]], metadata: Optional[ModelMetadata], strategy: Strategy) -> bool:
    if not profile:
        return True
    if metadata and profile.get("model_size_mb") != strategy.model_total_size_mb:
        return True
    return False


def choose_backend(requested: str, has_server: bool, cache_reuse: int = 0, parallel: int = 1) -> str:
    backend = (requested or "auto").lower()
    if backend in {"python", "llama-server"}:
        return backend
    if has_server and (cache_reuse > 0 or parallel > 1):
        return "llama-server"
    return "python"


def next_recovery_strategy(strategy: Strategy, step: int) -> Optional[Strategy]:
    candidate = replace(strategy)
    if step == 0 and candidate.use_expert_offloading and candidate.moe_offload == "off":
        candidate.moe_offload = "first-n"
        if candidate.n_cpu_moe is None and candidate.model_layers:
            candidate.n_cpu_moe = max(1, candidate.model_layers // 2)
        return candidate
    if step == 0 and candidate.flash_attn:
        candidate.flash_attn = False
        return candidate
    if step <= 1 and candidate.kv_cache_type != "q4_0":
        candidate.kv_cache_type = "q4_0"
        candidate.flash_attn = False
        return candidate
    if step <= 2 and candidate.n_batch > 128:
        candidate.n_batch = max(128, candidate.n_batch // 2)
        candidate.n_ubatch = max(64, candidate.n_ubatch // 2)
        return candidate
    if step <= 3 and candidate.n_gpu_layers > 0:
        candidate.n_gpu_layers = max(0, candidate.n_gpu_layers // 2)
        return candidate
    if step <= 4 and candidate.n_ctx > 1024:
        candidate.n_ctx = max(1024, candidate.n_ctx // 2)
        return candidate
    return None


def adapt_after_generation(strategy: Strategy, ram_delta_mb: float, tokens_per_second: float) -> Strategy:
    updated = replace(strategy)
    if ram_delta_mb > 1024 and updated.n_batch > 128:
        updated.n_batch = max(128, updated.n_batch // 2)
        updated.n_ubatch = max(64, updated.n_ubatch // 2)
    if tokens_per_second > 0 and tokens_per_second < 1.0:
        updated.thermal_mode = "cool"
        updated.n_threads = max(2, min(updated.n_threads, 4))
    return updated
