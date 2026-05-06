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

    def _get_model_category(self, model_id: str) -> str:
        """Model o'lchamini aniqlash (small: 1B-8B, medium: 14B-32B, giant: 70B+)."""
        mid = model_id.upper()
        if any(x in mid for x in ["70B", "405B", "671B", "DEEPSEEK-V3"]):
            return "giant"
        if any(x in mid for x in ["14B", "32B"]):
            return "medium"
        if any(x in mid for x in ["1B", "3B", "7B", "8B"]):
            return "small"
        return "small"

    def select_optimal_quant(self, model_id: str, hardware_report) -> str:
        """Hardware imkoniyatlaridan kelib chiqib optimal kvantlashni tanlash."""
        total_ram = hardware_report.total_ram if hardware_report else 16384
        category = self._get_model_category(model_id)
        
        if category == "small":
            # IQ1/IQ2 kichik modellar uchun yaroqsiz, minimal 600MB+ (IQ3_M) kerak
            return "Q4_K_M" if total_ram > 8192 else "IQ3_M"
        
        if category == "medium":
            return "Q4_K_M" if total_ram > 16384 else "DQ3"
        
        if category == "giant":
            return "IQ2_XS" if total_ram > 32768 else "IQ1_S"

        return "IQ3_M"

    def pull(self, model_id: str, hardware_report=None) -> str:
        """Modelni qat'iy cheklovlar bilan yuklab olish."""
        category = self._get_model_category(model_id)
        
        # Qat'iy fallback strategiyalari (User requirements)
        strategies = {
            "small": ["IQ3_M", "Q4_K_M"],
            "medium": ["DQ3", "IQ3_M", "IQ2_XS", "Q4_K_M"],
            "giant": ["IQ2_XS", "IQ1_S", "IQ3_M", "Q4_K_M"]
        }
        
        fallbacks = strategies.get(category, strategies["small"])
        preferred_quant = self.select_optimal_quant(model_id, hardware_report)
        
        try:
            files = list_repo_files(repo_id=model_id)
        except Exception as e:
            raise Exception(f"HuggingFace repo topilmadi yoki tarmoq xatosi: {str(e)}")

        # BitNet (.bitnet) yoki GGUF (.gguf) fayllarini qidirish
        gguf_files = [f for f in files if f.endswith((".gguf", ".bitnet"))]
        if not gguf_files:
            raise Exception(f"Repo ichida GGUF yoki BitNet fayllari topilmadi: {model_id}")

        # 1. Optimal tanlovni qidirish (agar u ruxsat etilgan strategiyada bo'lsa)
        target_file = None
        quantization = preferred_quant
        
        if preferred_quant in fallbacks:
            target_file = next((f for f in gguf_files if preferred_quant.lower() in f.lower()), None)

        # 2. Fallback zanjiri bo'yicha qat'iy qidiruv
        if not target_file:
            for fallback in fallbacks:
                target_file = next((f for f in gguf_files if fallback.lower() in f.lower()), None)
                if target_file:
                    quantization = fallback
                    break

        if not target_file:
            raise Exception(
                f"Model uchun mos kvantlash varianti topilmadi ({category}). "
                f"Kerakli fallback list: {fallbacks}"
            )

        file_path = hf_hub_download(
            repo_id=model_id,
            filename=target_file,
            local_dir=str(self.base_path / model_id.replace("/", "--")),
            local_dir_use_symlinks=False
        )

        model_name = model_id.split("/")[-1]
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
