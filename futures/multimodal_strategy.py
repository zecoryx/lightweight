from dataclasses import dataclass
from typing import Dict, Any, Optional
from lightweight.hardware import HardwareReport

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
    # 🖼️ Image/Voice specific
    image_steps: int = 20
    use_vae_tiling: bool = False

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

    def estimate_performance(self, model_id: str) -> Dict[str, Any]:
        """Model yuklanishidan oldin uning samaradorligini bashorat qilish."""
        # Model hajmini ID'dan aniqlash (masalan "7B")
        import re
        params = 7 # Default 7B
        match = re.search(r"(\d+)[Bb]", model_id)
        if match:
            params = int(match.group(1))

        original_size_gb = params * 2 # FP16: 2 bytes per param
        
        # Bizning strategiyamiz bo'yicha
        strategy = self.determine_strategy(original_size_gb * 1024, model_name=model_id)
        
        # Sifat yo'qolishini hisoblash (iMatrix orqali juda past)
        quality_loss = "5% (iMatrix)" if "IQ" in strategy.recommended_quant else "12% (Standard)"
        
        # Tezlik bashorati (Bandwidth va threadlarga asoslanib)
        vram_speed = 300 # GB/s
        ram_speed = 50 # GB/s
        
        if strategy.n_gpu_layers > 0:
            est_speed = 5 + (strategy.n_gpu_layers * 0.5)
        else:
            est_speed = ram_speed / (original_size_gb / 4) # Taxminiy
            
        return {
            "original_gb": original_size_gb,
            "compressed_gb": strategy.ram_used_estimate / 1024 + strategy.vram_used_estimate / 1024,
            "quant": strategy.recommended_quant,
            "speed_before": "Crash (OOM)" if original_size_gb > (self.hardware.total_ram / 1024) else "Slow (~1 tok/s)",
            "speed_after": f"{min(est_speed, 80):.1f} tok/s",
            "quality": quality_loss,
            "threads": strategy.n_threads
        }

    def determine_strategy(self, model_size_mb: int, model_name: str = "", is_moe: bool = False) -> Strategy:
        import psutil
        # Avtomatik MoE aniqlash
        if not is_moe and model_name:
            moe_keywords = ["MIXTRAL", "MOE", "DEEPSEEK-V2", "DEEPSEEK-V3", "GROK", "A14B", "A34B"]
            is_moe = any(k in model_name.upper() for k in moe_keywords)

        n_layers = self._estimate_layers(model_size_mb)
        
        # Multi-GPU support: Barcha GPU'lardagi bo'sh VRAMni hisoblash
        total_free_vram = sum(g.free_vram for g in self.hardware.gpus) if self.hardware.gpus else 0
        total_ram = self.hardware.total_ram
        available_ram = self.hardware.available_ram
        
        # KV Cache va overhead uchun 1GB buffer
        safe_vram = max(0, total_free_vram - 1024)

        # Threadlarni hisoblash: 1B-3B modellar uchun 4 ta thread kifoya
        physical_cores = psutil.cpu_count(logical=False) or 4
        if model_size_mb < 4000: # 1B-3B
            n_threads = min(4, physical_cores)
        else:
            n_threads = physical_cores
        
        kv_cache_type = "f16"

        # 🧠 Dynamic Context Window Scaling
        if total_ram <= 4096:
            n_ctx = 2048
        elif total_ram <= 8192:
            n_ctx = 4096
        elif total_ram <= 32768:
            n_ctx = 8192
        else:
            n_ctx = 16384

        # 🖼️ Image/Voice Specific Logic
        image_steps = 20
        use_vae_tiling = False
        category = self._get_model_category(model_name)
        
        if category == "image":
            # 4GB RAM uchun LCM (Latent Consistency) majburiy
            image_steps = 4 if total_ram <= 8192 else 8
            use_vae_tiling = total_ram <= 4096
            recommended_quant = "Q4_K" if total_ram > 8192 else "Q2_K"
            n_gpu_layers = 100 
        elif category == "voice":
            recommended_quant = "Q5_0"
            n_gpu_layers = 100
        else:
            # 4GB/8GB RAM uchun kvantlash strategiyasi (Yuqori sifatli iMatrix)
            if total_ram <= 8192:
                if model_size_mb > 20000 or any(x in model_name.upper() for x in ["70B", "120B", "405B"]):
                    recommended_quant = "IQ2_XS"
                else:
                    recommended_quant = "IQ4_XS" 
                kv_cache_type = "q4_0" 
            else:
                if model_size_mb > 35000 or any(x in model_name.upper() for x in ["70B", "120B", "405B"]):
                    recommended_quant = "IQ3_M" if total_free_vram > 12000 else "IQ2_XS"
                else:
                    recommended_quant = "Q4_K_M" if model_size_mb > 8000 else "Q8_0"
                
                if available_ram + total_free_vram < (model_size_mb + 2048):
                    kv_cache_type = "q4_0"

        # Qatlamlarni taqsimlash
        layer_size = model_size_mb / n_layers
        
        if is_moe:
            n_gpu_layers = min(n_layers, 16) 
        elif category not in ["image", "voice"]:
            n_gpu_layers = int(safe_vram // layer_size)
            n_gpu_layers = min(n_gpu_layers, n_layers)

        use_streaming = model_size_mb > (available_ram + total_free_vram - 1024)
        use_mlock = not use_streaming and (available_ram + total_free_vram) > (model_size_mb + 2048)

        return Strategy(
            n_gpu_layers=max(0, n_gpu_layers),
            n_threads=n_threads,
            n_ctx=n_ctx,
            use_expert_offloading=is_moe,
            use_mlock=use_mlock,
            kv_cache_type=kv_cache_type,
            recommended_quant=recommended_quant,
            vram_used_estimate=min(model_size_mb, safe_vram),
            ram_used_estimate=min(max(0, model_size_mb - safe_vram), available_ram),
            image_steps=image_steps,
            use_vae_tiling=use_vae_tiling
        )

    def _get_model_category(self, model_id: str) -> str:
        mid = model_id.upper()
        if any(x in mid for x in ["STABLE-DIFFUSION", "SDXL", "FLUX"]): return "image"
        if any(x in mid for x in ["WHISPER", "VOICE", "TTS"]): return "voice"
        if any(x in mid for x in ["70B", "405B", "671B"]): return "giant"
        if any(x in mid for x in ["14B", "32B"]): return "medium"
        return "small"
