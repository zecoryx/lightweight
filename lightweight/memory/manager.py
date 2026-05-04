import psutil
import os
from pathlib import Path
from typing import Dict, Any

class MemoryManager:
    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def get_current_usage(self) -> Dict[str, float]:
        """
        Joriy jarayon qancha RAM ishlatayotganini aniqlash (MB).
        """
        mem_info = self.process.memory_info()
        return {
            "rss": mem_info.rss / (1024 * 1024),  # Resident Set Size
            "vms": mem_info.vms / (1024 * 1024)   # Virtual Memory Size
        }

    def optimize_layout(self, model_size_mb: int, vram_free_mb: int) -> Dict[str, Any]:
        """
        Modelni VRAM, RAM va SSD orasida qanday taqsimlashni rejalashtirish.
        """
        # KV Cache va tizim uchun 10% VRAM olib qo'yamiz
        safe_vram = vram_free_mb * 0.9
        
        vram_part = min(model_size_mb, safe_vram)
        remaining = model_size_mb - vram_part
        
        # RAM-dan qancha joy ajratish mumkin (mavjud RAM-ning 70% ini ishlatamiz)
        available_ram = psutil.virtual_memory().available / (1024 * 1024)
        safe_ram = available_ram * 0.7
        
        ram_part = min(remaining, safe_ram)
        ssd_part = max(0, remaining - ram_part)
        
        return {
            "vram_mb": vram_part,
            "ram_mb": ram_part,
            "ssd_mb": ssd_part,
            "can_run": ssd_part < 10240  # Agar 10GB dan ko'p SSD-ga tushsa, juda sekin bo'ladi
        }

    def clear_cache(self):
        """
        Keraksiz keshni tozalash
        """
        import gc
        gc.collect()
