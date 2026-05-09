import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from huggingface_hub import hf_hub_download, list_repo_files

# 🚀 Model Aliases (Ollama-style short names)
MODEL_MAP = {
    "llama3.2:1b": "unsloth/Llama-3.2-1B-Instruct-GGUF",
    "llama3.2:3b": "unsloth/Llama-3.2-3B-Instruct-GGUF",
    "llama3:8b": "unsloth/Meta-Llama-3-8B-Instruct-GGUF",
    "llama3:70b": "mradermacher/Meta-Llama-3.1-70B-Instruct-i1-GGUF",
    "qwen:0.5b": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "qwen:1.5b": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "qwen:7b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
    "qwen:32b": "bartowski/Qwen2.5-32B-Instruct-GGUF",
    "deepseek:r1": "unsloth/DeepSeek-R1-Distill-Llama-8B-GGUF",
    "deepseek:v3": "unsloth/DeepSeek-V3-GGUF",
    "phi3.5": "unsloth/Phi-3.5-mini-instruct-GGUF",
    "smollm2": "unsloth/SmolLM2-1.7B-Instruct-GGUF"
}

class ModelManager:
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path.home() / ".cache" / "lightweight" / "models"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_path / "registry.json"
        self._load_registry()

    def _load_registry(self):
        try:
            self.registry = json.loads(self.registry_path.read_text()) if self.registry_path.exists() else {}
        except Exception: self.registry = {}

    def _save_registry(self):
        self.registry_path.write_text(json.dumps(self.registry, indent=4))

    def resolve_id(self, model_id: str) -> str:
        """Short name-ni (llama3) haqiqiy HF repo-ga aylantirish."""
        return MODEL_MAP.get(model_id.lower(), model_id)

    def select_optimal_quant(self, model_id: str, hardware_report) -> str:
        total_ram = hardware_report.total_ram if hardware_report else 16384
        mid = model_id.upper()
        if any(x in mid for x in ["70B", "405B", "KIMI", "V3"]):
            return "IQ2_XS" if total_ram <= 16384 else "IQ3_M"
        return "IQ4_XS" if total_ram <= 8192 else "Q4_K_M"

    def get_remote_metadata(self, repo_id: str) -> Dict[str, Any]:
        """HuggingFace-dan model haqida haqiqiy ma'lumotlarni olish."""
        from huggingface_hub import model_info
        try:
            info = model_info(repo_id)
            # Safetensors metadata or tags or file size-dan parametrni aniqlash
            params = 7.0 # Default
            for tag in info.tags:
                if tag.endswith("b") and tag[:-1].replace(".", "").isdigit():
                    params = float(tag[:-1])
                    break
            
            # Agar taglarda yo'q bo'lsa, fayl o'lchamidan taxmin qilish (GGUF bo'lmasa)
            if params == 7.0 and info.siblings:
                total_size = sum(s.size for s in info.siblings if s.size)
                if total_size > 0:
                    params = total_size / (2 * 1024 * 1024 * 1024) # FP16 deb hisoblab

            return {
                "params": params,
                "architecture": getattr(info, "config", {}).get("architectures", ["unknown"])[0],
                "id": repo_id
            }
        except Exception:
            return {"params": 7.0, "architecture": "unknown", "id": repo_id}

    def pull(self, model_id: str, hardware_report=None, manual_quant: Optional[str] = None) -> str:
        actual_repo = self.resolve_id(model_id)
        metadata = self.get_remote_metadata(actual_repo)
        
        preferred_quant = manual_quant.upper() if manual_quant else self.select_optimal_quant(actual_repo, hardware_report)
        fallbacks = [preferred_quant, "IQ4_XS", "Q4_K_M", "Q4_0"]
        
        try:
            files = list_repo_files(repo_id=actual_repo)
        except Exception as e: raise Exception(f"HF Error: {actual_repo} topilmadi. {e}")

        gguf_files = [f for f in files if f.endswith(".gguf")]
        target_file = None
        for q in fallbacks:
            target_file = next((f for f in gguf_files if q.lower() in f.lower()), None)
            if target_file: break

        if not target_file: raise Exception(f"No valid GGUF found for {actual_repo}")

        file_path = hf_hub_download(repo_id=actual_repo, filename=target_file, 
                                     local_dir=str(self.base_path / actual_repo.replace("/", "--")))
        
        actual_size = os.path.getsize(file_path)
        if actual_size < 1024 * 1024:
            os.remove(file_path)
            raise Exception("File corrupted. Try again.")

        model_name = model_id.split("/")[-1]
        self.registry[model_name] = {
            "path": str(file_path), "quant": preferred_quant,
            "size": actual_size // (1024 * 1024),
            "repo": actual_repo
        }
        self._save_registry()
        return str(file_path)

    def get_model_path(self, model_name: str) -> Optional[str]:
        return self.registry.get(model_name, {}).get("path")

    def list_local_models(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.registry.items()]
