from dataclasses import dataclass
from typing import Dict, Any, Optional, List

# ─── ROBUST INTERNAL IMPORTS ────────────────────────────────
try:
    from hardware import HardwareReport
except ImportError:
    try:
        from cli.hardware import HardwareReport
    except ImportError:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from hardware import HardwareReport

@dataclass
class Strategy:
    n_gpu_layers: int = 0
    n_threads: int = 4
    n_threads_batch: Optional[int] = None
    n_ctx: int = 4096
    n_batch: int = 512
    n_ubatch: int = 256
    split_mode: str = "layer"
    main_gpu: int = 0
    tensor_split: Optional[List[float]] = None
    use_expert_offloading: bool = False
    use_mlock: bool = False
    use_mmap: bool = True
    flash_attn: bool = True
    offload_kqv: bool = True
    op_offload: Optional[bool] = None
    swa_full: Optional[bool] = None
    numa: bool = False
    kv_cache_type: str = "f16"
    recommended_quant: str = "Q4_K_M"
    thermal_mode: str = "balanced"
    model_layers: Optional[int] = None
    long_context: bool = False
    spec_mode: str = "off"
    cache_prompt: bool = True
    cache_reuse: int = 256
    moe_offload: str = "off"
    n_cpu_moe: Optional[int] = None
    override_tensors: Optional[List[str]] = None
    native_fit: bool = True
    active_set_policy: str = "none"
    ssd_policy: str = "storage-only"
    backend: str = "auto"
    vram_used_estimate: int = 0
    ram_used_estimate: int = 0
    model_total_size_mb: int = 0

class StrategyEngine:
    def __init__(self, hardware: HardwareReport):
        self.hardware = hardware

    def _estimate_layers(self, model_size_mb: int) -> int:
        if model_size_mb < 5000: return 32
        elif model_size_mb < 15000: return 40
        elif model_size_mb < 30000: return 60
        else: return 80

    def estimate_performance(self, model_id: str) -> Dict[str, Any]:
        import re
        # ─── ROBUST MODEL MANAGER IMPORT ─────────────────────
        try:
            from models import ModelManager
        except ImportError:
            from cli.models import ModelManager
            
        manager = ModelManager()
        actual_repo = manager.resolve_id(model_id)
        metadata = manager.get_remote_metadata(actual_repo)
        
        params = metadata["params"]
        original_size_gb = params * 2 
        strategy = self.determine_strategy(original_size_gb * 1024, model_name=actual_repo)
        
        q = strategy.recommended_quant
        mult = 0.7 
        if "IQ2" in q: mult = 0.4
        elif "IQ1" in q: mult = 0.3
        elif "Q8" in q: mult = 1.1
        
        compressed_size_gb = params * mult
        
        vram_free = (self.hardware.gpus[0].free_vram / 1024) if self.hardware.gpus else 0
        ram_free = self.hardware.available_ram / 1024
        total_free_gb = vram_free + ram_free
        
        if compressed_size_gb < (total_free_gb * 0.85):
            compatibility = "[green]✓ Ready[/green]"
        elif compressed_size_gb < total_free_gb:
            compatibility = "[yellow]⚠ Tight[/yellow]"
        else:
            compatibility = "[red]✗ Heavy[/red]"

        if strategy.n_gpu_layers > 0:
            est_speed = 5 + (strategy.n_gpu_layers * 0.4)
        else:
            est_speed = 40 / (compressed_size_gb / 4)

        return {
            "original_gb": original_size_gb,
            "compressed_gb": compressed_size_gb,
            "quant": strategy.recommended_quant,
            "speed_before": "Crash (OOM)" if original_size_gb > (self.hardware.total_ram / 1024) else "Slow (~1 tok/s)",
            "speed_after": f"{min(est_speed, 90):.1f} tok/s",
            "quality": "95% (iMatrix)" if "IQ" in strategy.recommended_quant else "90% (Standard)",
            "compatibility": compatibility,
            "threads": strategy.n_threads
        }

    def determine_strategy(
        self,
        model_size_mb: int,
        model_name: str = "",
        is_moe: bool = False,
        thermal_mode: str = "balanced",
    ) -> Strategy:
        import psutil
        thermal_mode = (thermal_mode or "balanced").lower()
        if thermal_mode not in {"cool", "balanced", "performance"}:
            thermal_mode = "balanced"

        if not is_moe and model_name:
            moe_keywords = ["MIXTRAL", "MOE", "DEEPSEEK-V2", "DEEPSEEK-V3", "GROK"]
            is_moe = any(k in model_name.upper() for k in moe_keywords)

        n_layers = self._estimate_layers(model_size_mb)
        total_free_vram = sum(g.free_vram for g in self.hardware.gpus) if self.hardware.gpus else 0
        total_ram = self.hardware.total_ram
        available_ram = self.hardware.available_ram

        physical_cores = psutil.cpu_count(logical=False) or 4
        if thermal_mode == "cool":
            n_threads = max(2, min(4, physical_cores // 2 or 2))
            n_threads_batch = max(2, min(4, physical_cores))
            vram_reserve = 1536
        elif thermal_mode == "performance":
            n_threads = max(4, physical_cores)
            n_threads_batch = max(4, psutil.cpu_count(logical=True) or physical_cores)
            vram_reserve = 512
        else:
            n_threads = min(4, physical_cores) if model_size_mb < 4000 else max(4, physical_cores - 1)
            n_threads_batch = max(n_threads, physical_cores)
            vram_reserve = 1024

        safe_vram = max(0, total_free_vram - vram_reserve)

        if total_ram <= 4096: n_ctx = 2048
        elif total_ram <= 8192: n_ctx = 4096
        else: n_ctx = 8192

        if thermal_mode == "cool":
            n_ctx = min(n_ctx, 4096)
            n_batch = 256
            n_ubatch = 128
        elif thermal_mode == "performance":
            n_batch = 1024 if total_ram > 8192 else 512
            n_ubatch = 512 if total_ram > 8192 else 256
        else:
            n_batch = 512
            n_ubatch = 256

        if total_ram <= 8192:
            if model_size_mb > 20000 or any(x in model_name.upper() for x in ["70B", "405B", "KIMI"]):
                recommended_quant = "IQ2_XS"
            else:
                recommended_quant = "IQ4_XS" 
            kv_cache_type = "q4_0" 
        else:
            if model_size_mb > 35000: recommended_quant = "IQ2_XS"
            else: recommended_quant = "Q4_K_M"
            kv_cache_type = "f16"
            if available_ram + total_free_vram < (model_size_mb + 2048):
                kv_cache_type = "q4_0"

        layer_size = model_size_mb / n_layers
        if is_moe: n_gpu_layers = min(n_layers, 16) 
        else:
            n_gpu_layers = int(safe_vram // layer_size)
            n_gpu_layers = min(n_gpu_layers, n_layers)

        memory_tight = available_ram + safe_vram < (model_size_mb + 2048)
        moe_offload = "off"
        n_cpu_moe = None
        active_set_policy = "kv"
        if is_moe:
            active_set_policy = "moe-experts+kv"
            moe_offload = "first-n" if safe_vram > 0 else "all"
            if moe_offload == "first-n":
                if memory_tight:
                    n_cpu_moe = max(1, min(n_layers, int(n_layers * 0.60)))
                else:
                    n_cpu_moe = max(1, min(n_layers, int(n_layers * 0.35)))

        return Strategy(
            n_gpu_layers=max(0, n_gpu_layers),
            n_threads=n_threads,
            n_threads_batch=n_threads_batch,
            n_ctx=n_ctx,
            n_batch=n_batch,
            n_ubatch=n_ubatch,
            split_mode="layer",
            main_gpu=0,
            tensor_split=None,
            use_expert_offloading=is_moe,
            use_mlock=False,
            use_mmap=True,
            flash_attn=True,
            offload_kqv=True,
            op_offload=True if n_gpu_layers > 0 else None,
            swa_full=None,
            numa=False,
            kv_cache_type=kv_cache_type,
            recommended_quant=recommended_quant,
            thermal_mode=thermal_mode,
            model_layers=n_layers,
            long_context=False,
            spec_mode="off",
            cache_prompt=True,
            cache_reuse=256,
            moe_offload=moe_offload,
            n_cpu_moe=n_cpu_moe,
            override_tensors=None,
            native_fit=True,
            active_set_policy=active_set_policy,
            ssd_policy="fallback-only" if memory_tight else "storage-only",
            backend="auto",
            vram_used_estimate=min(model_size_mb, safe_vram),
            ram_used_estimate=min(max(0, model_size_mb - safe_vram), available_ram),
            model_total_size_mb=model_size_mb
        )
