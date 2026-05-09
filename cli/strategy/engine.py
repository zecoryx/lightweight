from dataclasses import dataclass
from typing import Dict, Any, Optional
from hardware import HardwareReport

@dataclass
class Strategy:
    n_gpu_layers: int
    n_threads: int
    n_ctx: int
    use_expert_offloading: bool
    use_mlock: bool
    kv_cache_type: str 
    recommended_quant: str
    vram_used_estimate: int
    ram_used_estimate: int
    model_total_size_mb: int # Yangi: Modelning jami siqilgan hajmi

class StrategyEngine:
    def __init__(self, hardware: HardwareReport):
        self.hardware = hardware

    def _estimate_layers(self, model_size_mb: int) -> int:
        if model_size_mb < 5000: return 32
        elif model_size_mb < 15000: return 40
        elif model_size_mb < 30000: return 60
        else: return 80

    def estimate_performance(self, model_id: str) -> Dict[str, Any]:
        """HuggingFace-dan real metadata olib tahlil qilish."""
        from models.manager import ModelManager
        manager = ModelManager()
        actual_repo = manager.resolve_id(model_id)
        metadata = manager.get_remote_metadata(actual_repo)
        
        params = metadata["params"]
        original_size_gb = params * 2 
        
        # Bizning strategiyamizni aniqlash
        strategy = self.determine_strategy(original_size_gb * 1024, model_name=actual_repo)
        
        # 4. Siqilgan hajmni aniq hisoblash
        # IQ2: ~0.4 byte/param, Q4: ~0.7 byte/param, Q8: ~1.1 byte/param
        q = strategy.recommended_quant
        mult = 0.7 # Default Q4
        if "IQ2" in q: mult = 0.4
        elif "IQ1" in q: mult = 0.3
        elif "Q8" in q: mult = 1.1
        
        compressed_size_gb = params * mult
        
        # 5. Laptop bilan moslik (Compatibility)
        vram_free = (self.hardware.gpus[0].free_vram / 1024) if self.hardware.gpus else 0
        ram_free = self.hardware.available_ram / 1024
        total_free_gb = vram_free + ram_free
        
        if compressed_size_gb < (total_free_gb * 0.85):
            compatibility = "[green]✓ Ready[/green]"
        elif compressed_size_gb < total_free_gb:
            compatibility = "[yellow]⚠ Tight[/yellow]"
        else:
            compatibility = "[red]✗ Heavy[/red]"

        # 6. Tezlik bashorati
        if strategy.n_gpu_layers > 0:
            est_speed = 5 + (strategy.n_gpu_layers * 0.4)
        else:
            est_speed = 40 / (compressed_size_gb / 4) # RAM tezligiga qarab

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

    def determine_strategy(self, model_size_mb: int, model_name: str = "", is_moe: bool = False) -> Strategy:
        import psutil
        if not is_moe and model_name:
            moe_keywords = ["MIXTRAL", "MOE", "DEEPSEEK-V2", "DEEPSEEK-V3", "GROK"]
            is_moe = any(k in model_name.upper() for k in moe_keywords)

        n_layers = self._estimate_layers(model_size_mb)
        total_free_vram = sum(g.free_vram for g in self.hardware.gpus) if self.hardware.gpus else 0
        total_ram = self.hardware.total_ram
        available_ram = self.hardware.available_ram
        safe_vram = max(0, total_free_vram - 1024)

        physical_cores = psutil.cpu_count(logical=False) or 4
        n_threads = min(4, physical_cores) if model_size_mb < 4000 else physical_cores

        if total_ram <= 4096: n_ctx = 2048
        elif total_ram <= 8192: n_ctx = 4096
        else: n_ctx = 8192

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

        return Strategy(
            n_gpu_layers=max(0, n_gpu_layers),
            n_threads=n_threads,
            n_ctx=n_ctx,
            use_expert_offloading=is_moe,
            use_mlock=False,
            kv_cache_type=kv_cache_type,
            recommended_quant=recommended_quant,
            vram_used_estimate=min(model_size_mb, safe_vram),
            ram_used_estimate=min(max(0, model_size_mb - safe_vram), available_ram),
            model_total_size_mb=model_size_mb
        )
