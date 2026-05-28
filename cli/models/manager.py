import os
import json
import re
import shutil
import queue
import threading
from pathlib import Path
from typing import Callable, List, Dict, Optional, Any, TypeVar

try:
    from huggingface_hub import HfApi, hf_hub_download, list_repo_files, model_info
except ModuleNotFoundError:
    HfApi = None
    hf_hub_download = None
    list_repo_files = None
    model_info = None

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "20")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")

T = TypeVar("T")
HF_METADATA_TIMEOUT = int(os.environ.get("LIGHTWEIGHT_HF_METADATA_TIMEOUT", "30"))
HF_DOWNLOAD_TIMEOUT = int(os.environ.get("LIGHTWEIGHT_HF_DOWNLOAD_TIMEOUT", "600"))

def _require_hf():
    if HfApi is None or hf_hub_download is None or list_repo_files is None or model_info is None:
        raise RuntimeError("huggingface_hub is required for remote model search/download. Install project dependencies first.")

# 🚀 Model Aliases
MODEL_MAP = {
    "llama:8b": "bartowski/Meta-Llama-3-8B-Instruct-GGUF",
    "llama3.1:8b": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
    "llama3.1:70b": "mradermacher/Meta-Llama-3.1-70B-Instruct-i1-GGUF",
    "llama3.2:1b": "unsloth/Llama-3.2-1B-Instruct-GGUF",
    "llama3.2:3b": "unsloth/Llama-3.2-3B-Instruct-GGUF",
    "llama3:8b": "bartowski/Meta-Llama-3-8B-Instruct-GGUF",
    "llama3:70b": "mradermacher/Meta-Llama-3.1-70B-Instruct-i1-GGUF",
    "qwen:0.5": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "qwen0.5b": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "qwen:0.5b": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "qwen1.5b": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "qwen:1.5b": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "qwen3b": "Qwen/Qwen2.5-3B-Instruct-GGUF",
    "qwen:3b": "Qwen/Qwen2.5-3B-Instruct-GGUF",
    "qwen7b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
    "qwen:7b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
    "qwen14b": "Qwen/Qwen2.5-14B-Instruct-GGUF",
    "qwen:14b": "Qwen/Qwen2.5-14B-Instruct-GGUF",
    "qwen32b": "bartowski/Qwen2.5-32B-Instruct-GGUF",
    "qwen:32b": "bartowski/Qwen2.5-32B-Instruct-GGUF",
    "qwen2.50.5b": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "qwen2.5:0.5b": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "qwen2.51.5b": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "qwen2.5:1.5b": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "qwen2.53b": "Qwen/Qwen2.5-3B-Instruct-GGUF",
    "qwen2.5:3b": "Qwen/Qwen2.5-3B-Instruct-GGUF",
    "qwen2.57b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
    "qwen2.5:7b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
    "qwen2.514b": "Qwen/Qwen2.5-14B-Instruct-GGUF",
    "qwen2.5:14b": "Qwen/Qwen2.5-14B-Instruct-GGUF",
    "qwen2.532b": "bartowski/Qwen2.5-32B-Instruct-GGUF",
    "qwen2.5:32b": "bartowski/Qwen2.5-32B-Instruct-GGUF",
    "deepseek:r1": "unsloth/DeepSeek-R1-Distill-Llama-8B-GGUF",
    "deepseek-r1:1.5b": "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
    "deepseek-r1:8b": "unsloth/DeepSeek-R1-Distill-Llama-8B-GGUF",
    "deepseek-r1:14b": "unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF",
    "deepseek-r1:32b": "unsloth/DeepSeek-R1-Distill-Qwen-32B-GGUF",
    "deepseek-r1:70b": "unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF",
    "deepseek:v3": "unsloth/DeepSeek-V3-GGUF",
    "mistral:7b": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    "phi3.5": "bartowski/Phi-3.5-mini-instruct-GGUF",
    "phi:3.5": "bartowski/Phi-3.5-mini-instruct-GGUF",
    "smollm2": "unsloth/SmolLM2-1.7B-Instruct-GGUF"
}

FIT_MODES = {
    "quality": {
        "quants": ["Q6_K", "Q5_K_M", "Q4_K_M", "IQ4_XS", "IQ3_M", "IQ2_XS"],
        "ctx": 8192,
        "quality_risk": "low",
        "intent": "preserve quality first; may require more RAM/VRAM",
    },
    "balanced": {
        "quants": ["Q4_K_M", "Q5_K_M", "IQ4_XS", "IQ3_M", "IQ2_XS"],
        "ctx": 4096,
        "quality_risk": "medium-low",
        "intent": "balance quality, memory, speed, and thermals",
    },
    "fit": {
        "quants": ["IQ4_XS", "Q4_K_M", "IQ3_M", "IQ2_XS"],
        "ctx": 2048,
        "quality_risk": "medium",
        "intent": "fit this exact model on constrained hardware",
    },
    "extreme": {
        "quants": ["IQ2_XS", "IQ3_M", "IQ4_XS", "Q4_0", "Q4_K_M"],
        "ctx": 1024,
        "quality_risk": "high",
        "intent": "last-resort exact-model mode; expect slower/lower quality",
    },
}

QUANT_SIZE_MULTIPLIER = {
    "Q8_0": 1.10,
    "Q6_K": 0.85,
    "Q5_K_M": 0.75,
    "Q4_K_M": 0.70,
    "Q4_0": 0.65,
    "IQ4_XS": 0.62,
    "IQ3_M": 0.50,
    "IQ2_XS": 0.40,
}

def _normalize_model_id(model_id: str) -> str:
    return (
        model_id.strip()
        .lower()
        .replace(" ", "")
        .replace("_", "-")
    )

def _alias_variants(alias: str) -> set[str]:
    normalized = _normalize_model_id(alias)
    return {
        normalized,
        normalized.replace(":", ""),
        normalized.replace("-", ""),
        normalized.replace(":", "").replace("-", ""),
    }

def _extract_params_from_text(text: str) -> Optional[float]:
    lowered = text.lower()
    known_totals = [
        ("deepseek-v3", 671.0),
        ("deepseek-v2", 236.0),
        ("deepseek-r1", 671.0) if "distill" not in lowered else ("", 0.0),
        ("kimi-k2", 1000.0),
        ("mixtral-8x22b", 141.0),
        ("mixtral-8x7b", 46.7),
        ("grok-1", 314.0),
    ]
    for marker, params in known_totals:
        if marker and marker in lowered:
            return params
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*b(?![a-z])", text.lower())
    if match:
        return float(match.group(1))
    return None

def _call_with_timeout(label: str, func: Callable[[], T], timeout: int = HF_METADATA_TIMEOUT) -> T:
    result_queue: "queue.Queue[tuple[bool, Any]]" = queue.Queue(maxsize=1)

    def runner():
        try:
            result_queue.put((True, func()))
        except Exception as exc:
            result_queue.put((False, exc))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    try:
        ok, value = result_queue.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError(f"{label} timed out after {timeout}s. Check your internet connection or try again.") from exc
    if ok:
        return value
    raise value

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
        normalized = _normalize_model_id(model_id)
        if normalized in MODEL_MAP:
            return MODEL_MAP[normalized]
        for alias, repo in MODEL_MAP.items():
            if normalized in _alias_variants(alias):
                return repo
        return model_id.strip()

    def suggest_models(self, model_id: str, limit: int = 5) -> List[str]:
        normalized = _normalize_model_id(model_id)
        normalized_compact = normalized.replace(":", "").replace("-", "")
        local_matches = [
            alias for alias in MODEL_MAP
            if any(
                normalized in variant
                or variant in normalized
                or normalized_compact in variant
                or variant in normalized_compact
                for variant in _alias_variants(alias)
            )
        ]
        if local_matches:
            return local_matches[:limit]

        try:
            _require_hf()
            api = HfApi()
            results = api.list_models(search=model_id, limit=limit * 2)
            suggestions = []
            for item in results:
                repo_id = getattr(item, "modelId", "")
                if repo_id and "gguf" in repo_id.lower():
                    suggestions.append(repo_id)
                if len(suggestions) >= limit:
                    break
            return suggestions
        except Exception:
            return []

    def select_optimal_quant(self, model_id: str, hardware_report, mode: str = "balanced") -> str:
        if mode in FIT_MODES:
            preferred = FIT_MODES[mode]["quants"][0]
            if mode != "balanced":
                return preferred

        total_ram = hardware_report.total_ram if hardware_report else 16384
        mid = model_id.upper()
        if any(x in mid for x in ["70B", "405B", "KIMI", "V3"]):
            return "IQ2_XS" if total_ram <= 16384 else "IQ3_M"
        return "IQ4_XS" if total_ram <= 8192 else "Q4_K_M"

    def build_fit_plan(self, model_id: str, hardware_report=None, mode: str = "balanced") -> Dict[str, Any]:
        mode = mode.lower().strip()
        if mode not in FIT_MODES:
            raise ValueError(f"Unknown mode '{mode}'. Use one of: {', '.join(FIT_MODES)}")

        actual_repo = self.resolve_id(model_id)
        metadata = self.get_remote_metadata(actual_repo)
        params = float(metadata.get("params", 7.0))
        original_gb = params * 2.0
        quant = self.select_optimal_quant(actual_repo, hardware_report, mode=mode)
        estimated_gb = params * QUANT_SIZE_MULTIPLIER.get(quant, 0.70)
        ram_gb = (hardware_report.available_ram / 1024) if hardware_report else 0
        vram_gb = (sum(g.free_vram for g in hardware_report.gpus) / 1024) if hardware_report else 0
        usable_gb = max(0, ram_gb + max(0, vram_gb - 1.0))

        if estimated_gb <= usable_gb * 0.85:
            verdict = "READY"
        elif estimated_gb <= usable_gb:
            verdict = "TIGHT"
        elif estimated_gb <= max(usable_gb * 1.75, usable_gb + 4):
            verdict = "SLOW_MODE"
        else:
            verdict = "NOT_RECOMMENDED"

        is_moe = any(token in actual_repo.upper() for token in ["MOE", "MIXTRAL", "DEEPSEEK-V2", "DEEPSEEK-V3"])
        memory_tier = "VRAM/RAM"
        if estimated_gb > usable_gb:
            memory_tier = "RAM-first with SSD fallback warning"
        active_set = "kv-cache"
        if is_moe:
            active_set = "moe-hot-experts + kv-cache"
        return {
            "model_id": model_id,
            "repo": actual_repo,
            "mode": mode,
            "replacement": "none",
            "quant": quant,
            "ctx": FIT_MODES[mode]["ctx"],
            "quality_risk": FIT_MODES[mode]["quality_risk"],
            "intent": FIT_MODES[mode]["intent"],
            "params_b": params,
            "original_gb": original_gb,
            "estimated_gb": estimated_gb,
            "usable_gb": usable_gb,
            "verdict": verdict,
            "moe": is_moe,
            "active_set": active_set,
            "memory_tier": memory_tier,
            "core_optimizations": [
                "GGUF quant selection",
                "KV cache dtype planning",
                "llama-server native fit/offload when available",
                "prompt/prefix cache reuse",
                "MoE CPU/RAM expert placement" if is_moe else "dense GPU layer placement",
            ],
            "experimental_optimizations": [
                "PowerInfer-style hot/cold neurons",
                "LLM-in-a-Flash/ActiveFlow active-weight swapping",
                "LMCache/SGLang/TensorRT-LLM alternate KV backends",
            ],
            "notes": [
                "No smaller model is substituted automatically.",
                "If this is a dense model, all layers are still needed per token.",
                "If this is a MoE model, expert offload can help more than dense offload.",
                "SSD/NVMe paging is treated as a last-resort fallback, not the fast path.",
            ],
        }

    def get_remote_metadata(self, repo_id: str) -> Dict[str, Any]:
        params = _extract_params_from_text(repo_id)
        try:
            _require_hf()
            info = _call_with_timeout("Hugging Face model metadata", lambda: model_info(repo_id))
            if params is None:
                for tag in info.tags:
                    parsed = _extract_params_from_text(tag)
                    if parsed is not None:
                        params = parsed
                        break
            if params is None:
                params = 7.0
            return {"params": params, "id": repo_id}
        except Exception:
            return {"params": params or 7.0, "id": repo_id}

    def _get_remote_file_sizes(self, repo_id: str) -> Dict[str, int]:
        try:
            _require_hf()
            info = _call_with_timeout("Hugging Face file metadata", lambda: model_info(repo_id, files_metadata=True), timeout=15)
        except Exception:
            return {}
        sizes: Dict[str, int] = {}
        for sibling in getattr(info, "siblings", []) or []:
            name = getattr(sibling, "rfilename", None)
            size = getattr(sibling, "size", None)
            if name and isinstance(size, int):
                sizes[name] = size
        return sizes

    def _detect_shards(self, main_file: str, gguf_files: List[str]) -> List[str]:
        match = re.search(r"^(?P<prefix>.+)-00001-of-(?P<count>\d+)\.gguf$", main_file)
        if not match:
            return [main_file]

        prefix = match.group("prefix")
        expected_count = int(match.group("count"))
        target_files = [
            f for f in gguf_files
            if re.match(rf"^{re.escape(prefix)}-\d{{5}}-of-{expected_count:05d}\.gguf$", f)
        ]
        target_files = sorted(target_files)
        if len(target_files) != expected_count:
            raise Exception(
                f"Sharded model is incomplete: expected {expected_count} parts, found {len(target_files)}."
            )
        return target_files

    def _check_disk_space(self, target_files: List[str], file_sizes: Dict[str, int]):
        total_size = sum(file_sizes.get(filename, 0) for filename in target_files)
        if total_size <= 0:
            return
        free_bytes = shutil.disk_usage(str(self.base_path)).free
        required_bytes = int(total_size * 1.10)
        if free_bytes < required_bytes:
            required_mb = required_bytes // (1024 * 1024)
            free_mb = free_bytes // (1024 * 1024)
            raise Exception(f"Not enough disk space: need about {required_mb} MB, have {free_mb} MB.")

    def _select_main_file(self, gguf_files: List[str], quant: str, mode: str) -> Optional[str]:
        search_order = [quant]
        search_order.extend(q for q in FIT_MODES.get(mode, FIT_MODES["balanced"])["quants"] if q not in search_order)
        for candidate_quant in search_order:
            match = next((f for f in gguf_files if candidate_quant.lower() in f.lower()), None)
            if match:
                return match
        return None

    def pull(
        self,
        model_id: str,
        hardware_report=None,
        manual_quant: Optional[str] = None,
        mode: str = "balanced",
        plan: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> str:
        def emit(event: str, **payload):
            if progress_callback:
                progress_callback(event, **payload)

        actual_repo = self.resolve_id(model_id)
        plan = plan or self.build_fit_plan(model_id, hardware_report=hardware_report, mode=mode)
        preferred_quant = manual_quant.upper() if manual_quant else plan["quant"]
        
        try:
            _require_hf()
            emit("resolve_start", repo=actual_repo)
            if not progress_callback:
                print(f"Resolving files for {actual_repo}...", flush=True)
            files = _call_with_timeout("Hugging Face file list", lambda: list_repo_files(repo_id=actual_repo))
            emit("resolve_done", repo=actual_repo)
        except Exception as e:
            if "huggingface_hub is required" in str(e):
                raise
            suggestions = self.suggest_models(model_id)
            hint = ""
            if suggestions:
                hint = "\nTry one of these:\n  " + "\n  ".join(suggestions)
            else:
                hint = "\nUse a built-in alias like qwen:7b, qwen:32b, llama3.2:3b, or pass an exact Hugging Face GGUF repo ID like owner/repo-name."
            raise Exception(f"Model '{model_id}' was not found as an alias or Hugging Face repo ({actual_repo}).{hint}") from e

        gguf_files = [f for f in files if f.endswith(".gguf")]
        
        main_file = self._select_main_file(gguf_files, preferred_quant, mode)

        if not main_file:
            raise Exception(f"No GGUF file found in {actual_repo}. Use a GGUF repository or a built-in alias.")

        target_files = self._detect_shards(main_file, gguf_files)
        if len(target_files) > 1:
            emit("shards", count=len(target_files))
            if not progress_callback:
                print(f"[Info] Sharded model detected: {len(target_files)} parts.", flush=True)

        first_file_path = ""
        local_dir = self.base_path / actual_repo.replace("/", "--")
        emit("metadata_start", repo=actual_repo)
        file_sizes = self._get_remote_file_sizes(actual_repo)
        emit("metadata_done", repo=actual_repo)
        self._check_disk_space(target_files, file_sizes)
        emit("download_plan", total_files=len(target_files), total_bytes=sum(file_sizes.get(filename, 0) for filename in target_files))
        
        for i, filename in enumerate(sorted(target_files)):
            emit(
                "file_start",
                index=i + 1,
                total=len(target_files),
                filename=filename,
                bytes=file_sizes.get(filename, 0),
            )
            if not progress_callback:
                print(f"Downloading part {i+1}/{len(target_files)}: {filename}", flush=True)
            path = _call_with_timeout(
                f"Download {filename}",
                lambda filename=filename: hf_hub_download(repo_id=actual_repo, filename=filename, local_dir=str(local_dir)),
                timeout=HF_DOWNLOAD_TIMEOUT,
            )
            emit(
                "file_done",
                index=i + 1,
                total=len(target_files),
                filename=filename,
                path=path,
                bytes=os.path.getsize(path) if os.path.exists(path) else file_sizes.get(filename, 0),
            )
            if i == 0: first_file_path = path

        model_name = model_id.split("/")[-1]
        self.registry[model_name] = {
            "path": str(first_file_path), 
            "quant": preferred_quant,
            "mode": mode,
            "plan": plan,
            "size": sum(os.path.getsize(local_dir / f) for f in target_files if (local_dir / f).exists()) // (1024 * 1024),
            "repo": actual_repo,
            "is_sharded": len(target_files) > 1
        }
        self._save_registry()
        return str(first_file_path)

    def get_model_path(self, model_name: str) -> Optional[str]:
        return self.registry.get(model_name, {}).get("path")

    def save_squeeze_profile(self, model_name: str, profile: Dict[str, Any]) -> bool:
        match = model_name
        if match not in self.registry:
            lowered = model_name.lower()
            for name in self.registry:
                if lowered in name.lower():
                    match = name
                    break

        if match not in self.registry:
            return False

        current = self.registry[match].get("squeeze_profiles", {})
        current[profile.get("profile", "balanced")] = profile
        self.registry[match]["squeeze_profiles"] = current
        self.registry[match]["active_squeeze_profile"] = profile.get("profile", "balanced")
        self._save_registry()
        return True

    def get_squeeze_profile(self, model_name: str, profile: str = "active") -> Optional[Dict[str, Any]]:
        model = self.registry.get(model_name)
        if not model:
            lowered = model_name.lower()
            for _name, value in self.registry.items():
                if lowered in _name.lower():
                    model = value
                    break
        if not model:
            return None
        profiles = model.get("squeeze_profiles", {})
        if profile == "active":
            return profiles.get(model.get("active_squeeze_profile", "")) or profiles.get("balanced")
        return profiles.get(profile)

    def list_squeeze_profiles(self, model_name: str) -> Dict[str, Any]:
        model = self.registry.get(model_name)
        if not model:
            lowered = model_name.lower()
            for _name, value in self.registry.items():
                if lowered in _name.lower():
                    model = value
                    break
        if not model:
            return {}
        return {
            "active": model.get("active_squeeze_profile"),
            "profiles": model.get("squeeze_profiles", {}),
        }

    def set_active_squeeze_profile(self, model_name: str, profile: str) -> bool:
        model_key = model_name
        model = self.registry.get(model_key)
        if not model:
            lowered = model_name.lower()
            for name, value in self.registry.items():
                if lowered in name.lower():
                    model_key = name
                    model = value
                    break
        if not model:
            return False
        if profile not in model.get("squeeze_profiles", {}):
            return False
        model["active_squeeze_profile"] = profile
        self.registry[model_key] = model
        self._save_registry()
        return True

    def save_squeeze_verification(self, model_name: str, verification: Dict[str, Any], profile: str = "active") -> bool:
        model_key = model_name
        model = self.registry.get(model_key)
        if not model:
            lowered = model_name.lower()
            for name, value in self.registry.items():
                if lowered in name.lower():
                    model_key = name
                    model = value
                    break
        if not model:
            return False

        profiles = model.get("squeeze_profiles", {})
        profile_key = model.get("active_squeeze_profile", "balanced") if profile == "active" else profile
        if profile_key in profiles:
            profiles[profile_key]["verification"] = verification
            model["squeeze_profiles"] = profiles
        else:
            model["last_squeeze_verification"] = verification
        self.registry[model_key] = model
        try:
            self._save_registry()
            return True
        except OSError:
            return False

    def save_squeeze_benchmark(self, model_name: str, benchmark: Dict[str, Any], profile: str = "active") -> bool:
        model_key = model_name
        model = self.registry.get(model_key)
        if not model:
            lowered = model_name.lower()
            for name, value in self.registry.items():
                if lowered in name.lower():
                    model_key = name
                    model = value
                    break
        if not model:
            return False

        profiles = model.get("squeeze_profiles", {})
        profile_key = model.get("active_squeeze_profile", "balanced") if profile == "active" else profile
        if profile_key in profiles:
            profiles[profile_key]["benchmark"] = benchmark
            model["squeeze_profiles"] = profiles
        else:
            model["last_squeeze_benchmark"] = benchmark
        self.registry[model_key] = model
        try:
            self._save_registry()
            return True
        except OSError:
            return False

    def save_runtime_profile(self, model_name: str, profile: Dict[str, Any]) -> bool:
        match = model_name
        if match not in self.registry:
            lowered = model_name.lower()
            for name in self.registry:
                if lowered in name.lower():
                    match = name
                    break

        if match not in self.registry:
            return False

        current = self.registry[match].get("runtime_profiles", {})
        current[profile.get("thermal", "balanced")] = profile
        self.registry[match]["runtime_profiles"] = current
        self._save_registry()
        return True

    def get_runtime_profile(self, model_name: str, thermal: str = "balanced") -> Optional[Dict[str, Any]]:
        model = self.registry.get(model_name)
        if not model:
            lowered = model_name.lower()
            for name, value in self.registry.items():
                if lowered in name.lower():
                    model = value
                    break
        if not model:
            return None
        profiles = model.get("runtime_profiles", {})
        return profiles.get(thermal) or profiles.get("balanced")

    def list_local_models(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.registry.items()]

    def remove_model(self, model_name: str, delete_files: bool = True) -> bool:
        import shutil

        match = model_name
        if match not in self.registry:
            lowered = model_name.lower()
            for name in self.registry:
                if lowered in name.lower():
                    match = name
                    break

        model = self.registry.pop(match, None)
        if not model:
            return False

        if delete_files:
            repo = model.get("repo")
            if repo:
                local_dir = self.base_path / repo.replace("/", "--")
                if local_dir.exists() and local_dir.is_dir():
                    shutil.rmtree(local_dir)
            else:
                path = model.get("path")
                if path and Path(path).exists():
                    Path(path).unlink()

        self._save_registry()
        return True
