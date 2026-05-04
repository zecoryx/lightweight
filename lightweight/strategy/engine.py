from dataclasses import dataclass
from typing import Dict, Any, Optional
from lightweight.hardware import HardwareReport

@dataclass
class Strategy:
    n_gpu_layers: int
    use_expert_offloading: bool
    use_mlock: bool
    kv_cache_type: str 
    recommended_quant: str
    vram_used_estimate: int
    ram_used_estimate: int

class StrategyEngine:
    def __init__(self, hardware: HardwareReport):
        self.hardware = hardware

    def _estimate_layers(self, model_size_mb: int) -> int:
        """
        Model hajmiga qarab taxminiy qatlamlar sonini aniqlash.
        """
        if model_size_mb < 5000: # 7B-8B
            return 32
        elif model_size_mb < 15000: # 14B-20B
            return 40
        elif model_size_mb < 30000: # 30B-35B
            return 60
        else: # 70B+
            return 80

    def determine_strategy(self, model_size_mb: int, model_name: str = "", is_moe: bool = False) -> Strategy:
        # Avtomatik MoE aniqlash
        if not is_moe and model_name:
            moe_keywords = ["MIXTRAL", "MOE", "DEEPSEEK-V2", "DEEPSEEK-V3", "GROK", "A14B", "A34B"]
            is_moe = any(k in model_name.upper() for k in moe_keywords)

        n_layers = self._estimate_layers(model_size_mb)
        free_vram = self.hardware.gpus[0].free_vram if self.hardware.gpus else 0
        total_available_memory = self.hardware.available_ram + free_vram
        
        # KV Cache va overhead uchun 1GB buffer
        safe_vram = max(0, free_vram - 1024)
        
        kv_cache_type = "f16"
        if total_available_memory < (model_size_mb + 2048):
            kv_cache_type = "q4_0"
        elif total_available_memory < (model_size_mb + 4096):
            kv_cache_type = "q8_0"

        # Qatlamlarni taqsimlash
        layer_size = model_size_mb / n_layers
        
        if is_moe:
            # MoE Expert Offloading: Faqat Attention/Router GPUda.
            # Experts RAM/SSDda qoladi. Bu GPU VRAM-ni tejaydi va katta MoE-larni ishlatishga imkon beradi.
            n_gpu_layers = min(n_layers, 16) 
        else:
            n_gpu_layers = int(safe_vram // layer_size)
            n_gpu_layers = min(n_gpu_layers, n_layers)

        use_streaming = model_size_mb > (total_available_memory - 1024)
        use_mlock = not use_streaming and total_available_memory > (model_size_mb + 1024)

        # iMatrix Quantization Priority (70B+ modellar uchun)
        if model_size_mb > 35000 or any(x in model_name.upper() for x in ["70B", "120B", "405B"]):
            recommended_quant = "IQ3_M" if free_vram > 12000 else "IQ2_XS"
        else:
            recommended_quant = "Q4_K_M" if model_size_mb > 8000 else "Q8_0"

        return Strategy(
            n_gpu_layers=max(0, n_gpu_layers),
            use_expert_offloading=is_moe,
            use_mlock=use_mlock,
            kv_cache_type=kv_cache_type,
            recommended_quant=recommended_quant,
            vram_used_estimate=min(model_size_mb, safe_vram),
            ram_used_estimate=min(max(0, model_size_mb - safe_vram), self.hardware.available_ram)
        )
