import os
import json
import mmap
from pathlib import Path
from typing import List, Dict, Optional
from huggingface_hub import hf_hub_download, list_repo_files

class ModelManager:
    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path.home() / ".cache" / "lightweight" / "models"
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_path / "registry.json"
        self._load_registry()

    def _load_registry(self):
        try:
            if self.registry_path.exists():
                with open(self.registry_path, "r") as f:
                    self.registry = json.load(f)
            else:
                self.registry = {}
        except Exception:
            self.registry = {}

    def _save_registry(self):
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=4)

    def select_optimal_quant(self, model_id: str, hardware_report) -> str:
        total_ram = hardware_report.total_ram if hardware_report else 16384
        is_large = any(x in model_id.upper() for x in ["70B", "120B", "405B"])
        
        if is_large:
            # iMatrix va BitNet prioriteti katta modellar uchun
            return "IQ3_M" if total_ram > 16384 else "IQ1_S" # IQ1_S for BitNet 1.58
        
        if total_ram <= 8192:
            return "IQ2_XS"
        elif total_ram <= 16384:
            return "DQ3" # Dynamic Quantization
        else:
            return "Q4_K_M"

    def pull(self, model_id: str, hardware_report=None) -> str:
        quantization = self.select_optimal_quant(model_id, hardware_report)
        
        try:
            files = list_repo_files(repo_id=model_id)
        except Exception as e:
            raise Exception(f"HuggingFace repo topilmadi yoki tarmoq xatosi: {str(e)}")

        gguf_files = [f for f in files if f.endswith(".gguf") or f.endswith(".bitnet")]
        
        # IQ va standart quantization qidirish
        target_file = next((f for f in gguf_files if quantization.lower() in f.lower()), None)
        
        if not target_file:
            # Fallback zanjiri: Dinamik -> iMatrix -> BitNet -> Oddiy
            fallbacks = ["DQ3", "IQ3_M", "IQ2_XS", "IQ1_S", "Q4_K_M", "Q4_0"]
            for fallback in fallbacks:
                target_file = next((f for f in gguf_files if fallback.lower() in f.lower()), None)
                if target_file: 
                    quantization = fallback
                    break

        if not target_file:
            if gguf_files: target_file = gguf_files[0]
            else: raise Exception(f"Repo ichida GGUF fayllar topilmadi: {model_id}")

        import psutil
        disk = psutil.disk_usage(self.base_path)
        if disk.free < 1024 * 1024 * 1024 * 5: # 5GB min
            raise Exception("Diskda yetarli joy yo'q (kamida 5GB bo'sh joy kerak)")

        file_path = hf_hub_download(
            repo_id=model_id,
            filename=target_file,
            local_dir=self.base_path / model_id.replace("/", "--"),
            local_dir_use_symlinks=False
        )

        model_name = model_id.split("/")[-1]
        
        # MoE aniqlash
        is_moe = any(k in model_id.upper() or k in target_file.upper() 
                     for k in ["MIXTRAL", "MOE", "DEEPSEEK-V2", "DEEPSEEK-V3", "GROK"])

        self.registry[model_name] = {
            "repo": model_id,
            "file": target_file,
            "path": str(file_path),
            "quant": quantization,
            "size": os.path.getsize(file_path) // (1024 * 1024),
            "is_moe": is_moe
        }
        self._save_registry()
        return str(file_path)

    def get_model_path(self, model_name: str) -> Optional[str]:
        return self.registry.get(model_name, {}).get("path")

    def prefetch(self, model_name: str):
        """
        Modelni OS keshiga yuklash (Optimallashtirilgan mmap yordamida).
        """
        path = self.get_model_path(model_name)
        if not path or not os.path.exists(path): return
        
        print(f"Prefetching (Fast I/O): {model_name}...")
        try:
            with open(path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    mm.read()
        except Exception:
            pass

    def list_local_models(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.registry.items()]
