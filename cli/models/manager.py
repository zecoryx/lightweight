import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from huggingface_hub import hf_hub_download, list_repo_files

# 🚀 Model Aliases
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
        return MODEL_MAP.get(model_id.lower(), model_id)

    def select_optimal_quant(self, model_id: str, hardware_report) -> str:
        total_ram = hardware_report.total_ram if hardware_report else 16384
        mid = model_id.upper()
        if any(x in mid for x in ["70B", "405B", "KIMI", "V3"]):
            return "IQ2_XS" if total_ram <= 16384 else "IQ3_M"
        return "IQ4_XS" if total_ram <= 8192 else "Q4_K_M"

    def get_remote_metadata(self, repo_id: str) -> Dict[str, Any]:
        from huggingface_hub import model_info
        try:
            info = model_info(repo_id)
            params = 7.0
            for tag in info.tags:
                if tag.endswith("b") and tag[:-1].replace(".", "").isdigit():
                    params = float(tag[:-1])
                    break
            return {"params": params, "id": repo_id}
        except Exception:
            return {"params": 7.0, "id": repo_id}

    def pull(self, model_id: str, hardware_report=None, manual_quant: Optional[str] = None) -> str:
        actual_repo = self.resolve_id(model_id)
        preferred_quant = manual_quant.upper() if manual_quant else self.select_optimal_quant(actual_repo, hardware_report)
        
        try:
            files = list_repo_files(repo_id=actual_repo)
        except Exception as e: raise Exception(f"HF Error: {actual_repo} not found. {e}")

        gguf_files = [f for f in files if f.endswith(".gguf")]
        
        # 1. Tanlangan kvantni qidirish
        main_file = next((f for f in gguf_files if preferred_quant.lower() in f.lower()), None)
        if not main_file:
            # Fallback
            for q in ["IQ4_XS", "Q4_K_M", "Q4_0"]:
                main_file = next((f for f in gguf_files if q.lower() in f.lower()), None)
                if main_file: break

        if not main_file: raise Exception(f"No GGUF found for {actual_repo}")

        # 🚀 SHARD DETECTION: Bo'laklangan modellarni aniqlash
        # Agar fayl nomi '00001-of-' bilan tugasa, barcha bo'laklarni yuklash kerak
        target_files = [main_file]
        if "-00001-of-" in main_file:
            shard_prefix = main_file.split("-00001-of-")[0]
            shard_suffix = main_file.split("-00001-of-")[1].split(".")[1] # Masalan 'gguf'
            target_files = [f for f in gguf_files if f.startswith(shard_prefix) and f.endswith(shard_suffix)]
            print(f"[Info] Sharded model detected: {len(target_files)} parts.")

        first_file_path = ""
        local_dir = self.base_path / actual_repo.replace("/", "--")
        
        for i, filename in enumerate(sorted(target_files)):
            print(f"Downloading part {i+1}/{len(target_files)}: {filename}")
            path = hf_hub_download(repo_id=actual_repo, filename=filename, local_dir=str(local_dir))
            if i == 0: first_file_path = path

        model_name = model_id.split("/")[-1]
        self.registry[model_name] = {
            "path": str(first_file_path), 
            "quant": preferred_quant,
            "size": sum(os.path.getsize(local_dir / f) for f in target_files) // (1024 * 1024),
            "repo": actual_repo,
            "is_sharded": len(target_files) > 1
        }
        self._save_registry()
        return str(first_file_path)

    def get_model_path(self, model_name: str) -> Optional[str]:
        return self.registry.get(model_name, {}).get("path")

    def list_local_models(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.registry.items()]
