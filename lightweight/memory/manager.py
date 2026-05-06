import psutil
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

class MemoryPage:
    def __init__(self, page_id: int, size_mb: int):
        self.page_id = page_id
        self.size_mb = size_mb
        self.is_in_ram = True
        self.last_access = time.time()

class MemoryManager:
    """
    PagedAttention v2 Simulation & Memory Orchestrator
    """
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.pages: Dict[int, MemoryPage] = {}
        self.page_size_mb = 128 # Har bir xotira sahifasi 128MB
        self.ssd_swap_path = Path.home() / ".cache" / "lightweight" / "swap"
        self.ssd_swap_path.mkdir(parents=True, exist_ok=True)

    def allocate_context_page(self) -> int:
        """Yangi KV Cache sahifasini ajratish"""
        page_id = len(self.pages)
        self.pages[page_id] = MemoryPage(page_id, self.page_size_mb)
        return page_id

    def handle_context_ballooning(self):
        """
        PagedAttention v2 mantiqi: RAM to'lganda eski sahifalarni SSD-ga surish.
        """
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            # Eng eski ishlatilgan sahifani topish (LRU)
            ram_pages = [p for p in self.pages.values() if p.is_in_ram]
            if not ram_pages: return

            lru_page = min(ram_pages, key=lambda x: x.last_access)
            self._swap_to_ssd(lru_page)

    def _swap_to_ssd(self, page: MemoryPage):
        """Xotira sahifasini diskka ko'chirish"""
        # Haqiqiy implementatsiyada bu yerda KV Cache tensorlari faylga yoziladi
        # Bizda hozircha mantiqiy simulyatsiya
        page.is_in_ram = False
        print(f"[PagedAttention] Page {page.page_id} swapped to SSD to free RAM.")

    def get_current_usage(self) -> Dict[str, float]:
        mem_info = self.process.memory_info()
        return {"rss": mem_info.rss / (1024 * 1024)}

    def optimize_layout(self, model_size_mb: int, vram_free_mb: int) -> Dict[str, Any]:
        safe_vram = vram_free_mb * 0.85
        vram_part = min(model_size_mb, safe_vram)
        available_ram = psutil.virtual_memory().available / (1024 * 1024)
        ram_part = min(model_size_mb - vram_part, available_ram * 0.7)
        ssd_part = max(0, model_size_mb - vram_part - ram_part)
        
        return {
            "vram_mb": vram_part,
            "ram_mb": ram_part,
            "ssd_mb": ssd_part
        }

    def compact(self):
        """
        KV cache-ni nolga tushirish va xotirani bo'shatish.
        """
        self.pages.clear()
        
        # SSD keshni tozalash
        if self.ssd_swap_path.exists():
            for swap_file in self.ssd_swap_path.glob("*"):
                try:
                    swap_file.unlink()
                except Exception as e:
                    print(f"[MemoryManager] Swap faylni o'chirishda xato: {e}")
        
        import gc
        gc.collect()
        print("[MemoryManager] KV Cache tozalandi va xotira optimallashdi.")
