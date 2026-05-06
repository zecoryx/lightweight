import sys
import os
from unittest.mock import MagicMock, patch

# Loyiha root katalogini path-ga qo'shish
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lightweight.inference import InferenceEngine
from lightweight.strategy import Strategy
from lightweight.memory import MemoryManager

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

def test_api_lock_logic():
    print("Testing API Lock and Engine Cache logic...")
    from lightweight.api import EngineCache
    
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
        test_api_lock_logic()
        print("\nALL TESTS PASSED SUCCESSFULLY! 🚀")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
