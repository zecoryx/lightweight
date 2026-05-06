import os
import json
import mmap
from pathlib import Path
from typing import List, Dict, Optional
from huggingface_hub import hf_hub_download, list_repo_files

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

    def select_optimal_quant(self, model_id: str, hardware_report) -> str:
        total_ram = hardware_report.total_ram if hardware_report else 16384
        mid = model_id.upper()
        if any(x in mid for x in ["70B", "405B", "KIMI"]):
            return "IQ2_XS" if total_ram <= 16384 else "IQ3_M"
        return "IQ4_XS" if total_ram <= 8192 else "Q4_K_M"

    def pull(self, model_id: str, hardware_report=None, manual_quant: Optional[str] = None) -> str:
        preferred_quant = manual_quant.upper() if manual_quant else self.select_optimal_quant(model_id, hardware_report)
        fallbacks = [preferred_quant, "IQ4_XS", "Q4_K_M", "Q4_0"]
        
        try:
            files = list_repo_files(repo_id=model_id)
        except Exception as e: raise Exception(f"HF Error: {e}")

        gguf_files = [f for f in files if f.endswith(".gguf")]
        target_file = None
        for q in fallbacks:
            target_file = next((f for f in gguf_files if q.lower() in f.lower()), None)
            if target_file: break

        if not target_file: raise Exception(f"No valid GGUF found for {model_id}")

        file_path = hf_hub_download(repo_id=model_id, filename=target_file, 
                                     local_dir=str(self.base_path / model_id.replace("/", "--")),
                                     local_dir_use_symlinks=False)

        model_name = model_id.split("/")[-1]
        self.registry[model_name] = {
            "path": str(file_path), "quant": preferred_quant,
            "size": os.path.getsize(file_path) // (1024 * 1024)
        }
        self._save_registry()
        return str(file_path)

    def get_model_path(self, model_name: str) -> Optional[str]:
        return self.registry.get(model_name, {}).get("path")

    def list_local_models(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.registry.items()]
