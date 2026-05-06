import psutil
import os
import time
import warnings
from dataclasses import dataclass
from typing import Optional, Dict, List

# Silence pynvml/nvidia-ml-py warnings
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import pynvml
except ImportError:
    try:
        import nvidia_ml_py as pynvml
    except ImportError:
        pynvml = None

@dataclass
class GPUInfo:
    name: str
    total_vram: int  # in MB
    free_vram: int   # in MB
    index: int

@dataclass
class HardwareReport:
    total_ram: int      # in MB
    available_ram: int  # in MB
    gpus: List[GPUInfo]
    disk_free: int     # in MB
    has_cuda: bool
    timestamp: float

class Detector:
    _cache: Optional[HardwareReport] = None
    _cache_ttl: float = 5.0 # 5 seconds cache

    def __init__(self):
        self.has_nvml = False
        if pynvml:
            try:
                pynvml.nvmlInit()
                self.has_nvml = True
            except Exception:
                pass

    def get_report(self, force: bool = False) -> HardwareReport:
        """
        Get hardware status (with caching).
        """
        now = time.time()
        if not force and self._cache and (now - self._cache.timestamp) < self._cache_ttl:
            return self._cache

        ram = psutil.virtual_memory()
        gpus = []
        
        if self.has_nvml:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpus.append(GPUInfo(
                        name=name,
                        total_vram=mem.total // (1024 * 1024),
                        free_vram=mem.free // (1024 * 1024),
                        index=i
                    ))
            except Exception:
                pass

        try:
            stat = psutil.disk_usage(os.path.abspath("."))
            disk_free = stat.free // (1024 * 1024)
        except Exception:
            disk_free = 0
        
        self._cache = HardwareReport(
            total_ram=ram.total // (1024 * 1024),
            available_ram=ram.available // (1024 * 1024),
            gpus=gpus,
            disk_free=disk_free,
            has_cuda=len(gpus) > 0,
            timestamp=now
        )
        return self._cache

    def __del__(self):
        if hasattr(self, 'has_nvml') and self.has_nvml:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
