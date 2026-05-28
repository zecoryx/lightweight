import sys
import os
from unittest.mock import MagicMock

# Loyiha root katalogini path-ga qo'shish
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli.inference import InferenceEngine
from cli.strategy import Strategy, StrategyEngine
from cli.hardware import HardwareReport, GPUInfo
from cli.memory import MemoryManager
from cli.metadata import ModelMetadata
from cli.models.manager import ModelManager
from cli.runtime_policy import apply_metadata, choose_backend, next_recovery_strategy

def test_inference_engine_threading():
    print("Testing InferenceEngine Thread Capping...")
    strategy = Strategy(
        n_gpu_layers=0,
        use_expert_offloading=False,
        use_mlock=False,
        kv_cache_type="f16",
        recommended_quant="Q4_K_M",
        vram_used_estimate=0,
        ram_used_estimate=1000
    )
    
    # 1B model uchun threadlar soni 4 dan oshmasligi kerak
    engine = InferenceEngine("model_1B.gguf", strategy)
    print(f"  Threads for 1B model: {engine.n_threads} (expected <= 4)")
    assert engine.n_threads <= 4
    
    # Katta model uchun threadlar soni ko'proq bo'lishi mumkin
    engine_large = InferenceEngine("model_70B.gguf", strategy)
    print(f"  Threads for 70B model: {engine_large.n_threads}")
    
    print("✓ Thread capping test passed.")

def test_memory_manager_real():
    print("Testing Real MemoryManager...")
    mm = MemoryManager()
    usage = mm.get_current_usage()
    print(f"  Current RSS: {usage['rss']:.2f} MB")
    assert usage['rss'] > 0
    
    # Compact funksiyasini tekshirish
    mm.compact()
    print("  Compact called successfully.")
    print("✓ Memory manager test passed.")

def test_strategy_runtime_profiles():
    print("Testing Strategy runtime profiles...")
    report = HardwareReport(
        total_ram=16384,
        available_ram=10000,
        gpus=[GPUInfo(name="RTX Test", total_vram=6144, free_vram=5000, index=0)],
        disk_free=100000,
        has_cuda=True,
        timestamp=0,
    )
    engine = StrategyEngine(report)
    cool = engine.determine_strategy(9000, model_name="test-14b", thermal_mode="cool")
    performance = engine.determine_strategy(9000, model_name="test-14b", thermal_mode="performance")

    assert cool.thermal_mode == "cool"
    assert performance.thermal_mode == "performance"
    assert cool.n_batch <= performance.n_batch
    assert cool.n_ubatch <= performance.n_ubatch
    assert cool.n_threads_batch <= performance.n_threads_batch
    assert cool.n_gpu_layers <= performance.n_gpu_layers
    assert cool.flash_attn is True
    assert cool.offload_kqv is True
    print("✓ Strategy runtime profile test passed.")

def test_runtime_policy_core():
    print("Testing runtime policy core...")
    strategy = Strategy(n_gpu_layers=80, n_ctx=8192, flash_attn=True, kv_cache_type="f16", n_batch=512)
    metadata = ModelMetadata(path="x.gguf", n_ctx_train=4096, n_layer=32, is_moe=True)
    updated = apply_metadata(strategy, metadata)

    assert updated.n_ctx == 4096
    assert updated.n_gpu_layers == 32
    assert updated.use_expert_offloading is True
    assert updated.moe_offload == "first-n"
    assert updated.active_set_policy == "moe-experts+kv"
    assert choose_backend("auto", has_server=True, cache_reuse=256, parallel=1) == "llama-server"
    assert choose_backend("auto", has_server=False, cache_reuse=256, parallel=1) == "python"
    recovered = next_recovery_strategy(strategy, 0)
    assert recovered.flash_attn is False
    print("✓ Runtime policy core test passed.")

def test_model_alias_resolution():
    print("Testing model alias resolution...")
    manager = ModelManager(base_path="/tmp/lightweight-test-models")

    assert manager.resolve_id("deepseek r1 32b") == "unsloth/DeepSeek-R1-Distill-Qwen-32B-GGUF"
    assert manager.resolve_id("deepseek-r1:14b") == "unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF"
    assert manager.resolve_id("qwen2.5 32b") == "bartowski/Qwen2.5-32B-Instruct-GGUF"
    suggestions = manager.suggest_models("deepseek r1 32b")
    assert "deepseek-r1:32b" in suggestions
    print("✓ Model alias resolution test passed.")

def test_squeeze_profile_registry():
    print("Testing squeeze profile registry...")
    manager = ModelManager(base_path="/tmp/lightweight-test-models")
    manager.registry["local-test"] = {"path": "/tmp/local-test.gguf", "size": 1, "repo": "local/test"}
    profile = {
        "profile": "balanced",
        "quant": "Q4_K_M",
        "ctx": 4096,
        "verdict": "READY",
        "active_set": "kv-cache",
    }
    assert manager.save_squeeze_profile("local-test", profile) is True
    assert manager.get_squeeze_profile("local-test")["profile"] == "balanced"
    assert manager.set_active_squeeze_profile("local-test", "balanced") is True
    assert manager.save_squeeze_verification("local-test", {"ok": True, "chunks_per_second": 10.0}) is True
    assert manager.save_squeeze_benchmark("local-test", {"ok": True, "chunks_per_second": 12.0}) is True
    assert manager.get_squeeze_profile("local-test")["verification"]["ok"] is True
    assert manager.get_squeeze_profile("local-test")["benchmark"]["chunks_per_second"] == 12.0
    listed = manager.list_squeeze_profiles("local-test")
    assert listed["active"] == "balanced"
    assert "balanced" in listed["profiles"]
    print("✓ Squeeze profile registry test passed.")

def test_api_lock_logic():
    print("Testing API Lock and Engine Cache logic...")
    try:
        from cli.api import EngineCache
    except ModuleNotFoundError as exc:
        if exc.name == "fastapi":
            print("  Skipped: fastapi is not installed in this environment.")
            return
        raise
    
    cache = EngineCache(capacity=1)
    mock_engine1 = MagicMock()
    mock_engine2 = MagicMock()
    
    cache.put("model1", mock_engine1)
    cache.put("model2", mock_engine2)
    
    # Capacity 1 bo'lgani uchun model1 o'chirilgan bo'lishi kerak
    assert cache.get("model1") is None
    assert cache.get("model2") is not None
    print("  Engine cache eviction works.")
    print("✓ API logic test passed.")

if __name__ == "__main__":
    try:
        test_inference_engine_threading()
        test_memory_manager_real()
        test_strategy_runtime_profiles()
        test_runtime_policy_core()
        test_model_alias_resolution()
        test_squeeze_profile_registry()
        test_api_lock_logic()
        print("\nALL TESTS PASSED SUCCESSFULLY! 🚀")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
