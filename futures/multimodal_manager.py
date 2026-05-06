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
        """Model turini va o'lchamini aniqlash."""
        mid = model_id.upper()
        
        # 🎙️ Voice & 🖼️ Image Detection
        if any(x in mid for x in ["STABLE-DIFFUSION", "SDXL", "FLUX", "STABLE-VIDEO"]):
            return "image"
        if any(x in mid for x in ["WHISPER", "VOICE", "TTS", "BARK"]):
            return "voice"
            
        # 📝 Text (LLM) Detection
        if any(x in mid for x in ["70B", "405B", "671B", "DEEPSEEK-V3"]):
            return "giant"
        if any(x in mid for x in ["14B", "32B"]):
            return "medium"
        return "small"

    def select_optimal_quant(self, model_id: str, hardware_report) -> str:
        """Hardware imkoniyatlaridan kelib chiqib optimal kvantlashni tanlash."""
        total_ram = hardware_report.total_ram if hardware_report else 16384
        category = self._get_model_category(model_id)
        
        if category == "image":
            return "Q4_K" if total_ram > 8192 else "Q2_K"
            
        if category == "voice":
            return "Q5_0" # Ovoz uchun juda yuqori siqish sifatni buzadi
            
        if category == "small":
            return "Q4_K_M" if total_ram > 8192 else "IQ3_M"
        
        if category == "medium":
            return "Q4_K_M" if total_ram > 16384 else "DQ3"
        
        if category == "giant":
            return "IQ2_XS" if total_ram > 32768 else "IQ1_S"

        return "IQ3_M"

    def pull(self, model_id: str, hardware_report=None, manual_quant: Optional[str] = None) -> str:
        """Modelni yuklab olish (Smart Default + Manual Override)."""
        category = self._get_model_category(model_id)
        
        # Agar foydalanuvchi o'zi tanlagan bo'lsa, o'shani ishlatamiz
        if manual_quant:
            preferred_quant = manual_quant.upper()
            fallbacks = [preferred_quant]
        else:
            # Qat'iy fallback strategiyalari (Smart Defaults)
            strategies = {
                "small": ["IQ4_XS", "Q4_K_M", "Q4_0"],
                "medium": ["IQ3_M", "IQ4_XS", "Q4_K_M"],
                "giant": ["IQ2_XS", "IQ1_S", "IQ3_M"]
            }
            fallbacks = strategies.get(category, strategies["small"])
            preferred_quant = self.select_optimal_quant(model_id, hardware_report)
        
        try:
            files = list_repo_files(repo_id=model_id)
        except Exception as e:
            raise Exception(f"HuggingFace repo topilmadi: {str(e)}")

        gguf_files = [f for f in files if f.endswith((".gguf", ".bitnet"))]
        if not gguf_files:
            raise Exception(f"Repo ichida GGUF/BitNet fayllari topilmadi: {model_id}")

        target_file = None
        quantization = preferred_quant
        
        # 1. Tanlangan kvantni qidirish
        target_file = next((f for f in gguf_files if preferred_quant.lower() in f.lower()), None)

        # 2. Agar foydalanuvchi manual tanlamagan bo'lsa, fallback bo'yicha qidirish
        if not target_file and not manual_quant:
            for fallback in fallbacks:
                target_file = next((f for f in gguf_files if fallback.lower() in f.lower()), None)
                if target_file:
                    quantization = fallback
                    break

        if not target_file:
            error_msg = f"Model uchun '{preferred_quant}' varianti topilmadi."
            if not manual_quant:
                error_msg += f" Tavsiya etilganlar: {fallbacks}"
            raise Exception(error_msg)

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
