import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from typing import Dict, Any

try:
    from strategy import Strategy
    from inference import InferenceEngine
except ImportError:
    from cli.strategy import Strategy
    from cli.inference import InferenceEngine


def _worker() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--strategy-json", required=True)
    args = parser.parse_args()

    try:
        payload = json.loads(args.strategy_json)
        strategy = Strategy(**payload)
        engine = InferenceEngine(args.model_path, strategy)
        started = time.perf_counter()
        engine.load()
        elapsed = time.perf_counter() - started
        print(json.dumps({"ok": True, "elapsed": elapsed}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


def _run_probe_once(model_path: str, strategy: Strategy, timeout: int) -> Dict[str, Any]:
    if getattr(sys, "frozen", False):
        return {"ok": False, "error": "GPU probe is unavailable inside the packaged executable", "returncode": 1}
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.runtime_probe",
            "--model-path",
            model_path,
            "--strategy-json",
            json.dumps(asdict(strategy)),
        ],
        cwd=str(_repo_root()),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output = (result.stdout or result.stderr or "").strip().splitlines()
    try:
        payload = json.loads(output[-1]) if output else {}
    except Exception:
        payload = {"ok": False, "error": result.stderr or result.stdout or "probe failed"}
    payload["returncode"] = result.returncode
    return payload


def _repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def probe_gpu_layers(
    model_path: str,
    base_strategy: Strategy,
    max_layers: int,
    timeout: int = 120,
) -> Dict[str, Any]:
    low = 0
    high = max(0, max_layers)
    best = 0
    attempts = []

    while low <= high:
        mid = (low + high) // 2
        strategy = Strategy(**asdict(base_strategy))
        strategy.n_gpu_layers = mid
        result = _run_probe_once(model_path, strategy, timeout=timeout)
        attempts.append({"layers": mid, **result})

        if result.get("ok") and result.get("returncode") == 0:
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    return {
        "ok": True,
        "best_n_gpu_layers": best,
        "attempts": attempts,
    }


if __name__ == "__main__":
    raise SystemExit(_worker())
