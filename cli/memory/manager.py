import psutil
import os
import gc
from pathlib import Path
from typing import Dict, List, Any, Optional

class MemoryManager:
    """
    Real-time Memory Orchestrator & Context Guard
    """
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        # Xotira chegaralari (MB)
        self.critical_threshold_pct = 90.0
        self.warning_threshold_pct = 75.0

    def handle_context_ballooning(self, model: Any = None):
        """
        Xotira to'lishini nazorat qilish va kerak bo'lsa model xotirasini bo'shatish.
        """
        mem = psutil.virtual_memory()
        
        if mem.percent > self.critical_threshold_pct:
            # Kritik holat: KV Cache-ni tozalash
            if model:
                try:
                    # llama-cpp-python-da reset() kontekstni tozalaydi
                    model.reset()
                    gc.collect()
                except Exception:
                    pass
        elif mem.percent > self.warning_threshold_pct:
            # Ogohlantirish holati: GC chaqirish
            gc.collect()

    def get_current_usage(self) -> Dict[str, float]:
        """Joriy jarayonning RAM sarfini aniqlash (MB)"""
        mem_info = self.process.memory_info()
        return {
            "rss": mem_info.rss / (1024 * 1024),
            "vms": mem_info.vms / (1024 * 1024),
            "system_pct": psutil.virtual_memory().percent
        }

    def optimize_layout(self, model_size_mb: int, vram_free_mb: int) -> Dict[str, Any]:
        """
        Modelni GPU/RAM/SSD o'rtasida optimal taqsimlashni hisoblash.
        """
        safe_vram = vram_free_mb * 0.90 # 90% xavfsiz buffer
        vram_part = min(model_size_mb, safe_vram)
        
        available_ram = psutil.virtual_memory().available / (1024 * 1024)
        ram_part = min(model_size_mb - vram_part, available_ram * 0.8)
        
        ssd_part = max(0, model_size_mb - vram_part - ram_part)
        
        return {
            "vram_mb": vram_part,
            "ram_mb": ram_part,
            "ssd_mb": ssd_part
        }

    def compact(self, model: Any = None):
        """
        Xotirani majburiy tozalash va optimallash.
        """
        if model:
            try:
                model.reset()
            except Exception:
                pass
        
        gc.collect()
        # Windows-da xotirani OS-ga qaytarishga urinish
        if os.name == 'nt':
            import ctypes
            # GetCurrentProcess() har doim joriy jarayon pseudo-handle-ni qaytaradi (-1)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.EmptyWorkingSet(handle)
