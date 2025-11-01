#!/usr/bin/env python3
"""
Edge TPU基本動作確認テスト
Python 3.9 + PyCoral環境で実行
"""

import sys
import time
import numpy as np

def test_pycoral_import():
    """PyCoralライブラリのインポートテスト"""
    print("=" * 60)
    print("Test 1: PyCoral Import Test")
    print("=" * 60)

    try:
        from pycoral.utils import edgetpu
        from pycoral.utils import dataset
        from pycoral.adapters import common
        from pycoral.adapters import detect
        print("✅ PyCoral imported successfully")
        return True
    except ImportError as e:
        print(f"❌ PyCoral import failed: {e}")
        return False

def test_tpu_detection():
    """Edge TPUデバイスの検出テスト"""
    print("\n" + "=" * 60)
    print("Test 2: Edge TPU Detection")
    print("=" * 60)

    try:
        from pycoral.utils import edgetpu
        devices = edgetpu.list_edge_tpus()

        if devices:
            print(f"✅ Found {len(devices)} Edge TPU device(s):")
            for i, device in enumerate(devices):
                print(f"   [{i}] {device}")
            return True
        else:
            print("⚠️ No Edge TPU devices found")
            print("   Make sure the Coral USB Accelerator is connected")
            return False
    except Exception as e:
        print(f"❌ Error detecting Edge TPU: {e}")
        return False

def test_tpu_model_loading():
    """TPUモデルのロードテスト"""
    print("\n" + "=" * 60)
    print("Test 3: TPU Model Loading")
    print("=" * 60)

    model_path = 'models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'

    try:
        from pycoral.utils import edgetpu

        print(f"Loading model: {model_path}")
        start_time = time.time()
        interpreter = edgetpu.make_interpreter(model_path)
        interpreter.allocate_tensors()
        load_time = time.time() - start_time

        print(f"✅ Model loaded successfully in {load_time*1000:.2f}ms")

        # 入出力テンソル情報を表示
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        print(f"\nModel Information:")
        print(f"  Input tensor: {input_details[0]['shape']}")
        print(f"  Output tensors: {len(output_details)}")

        return interpreter
    except FileNotFoundError:
        print(f"❌ Model file not found: {model_path}")
        print("   Please download the model first:")
        print("   cd models && wget https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite")
        return None
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None

def test_tpu_inference_speed():
    """TPU推論速度テスト"""
    print("\n" + "=" * 60)
    print("Test 4: TPU Inference Speed")
    print("=" * 60)

    model_path = 'models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'

    try:
        from pycoral.utils import edgetpu

        interpreter = edgetpu.make_interpreter(model_path)
        interpreter.allocate_tensors()

        # 入力テンソルのサイズを取得
        input_details = interpreter.get_input_details()
        input_shape = input_details[0]['shape']

        print(f"Input shape: {input_shape}")
        print(f"Running inference test (10 iterations)...")

        # ダミーデータで推論速度を測定
        dummy_input = np.zeros(input_shape, dtype=np.uint8)

        # ウォームアップ
        interpreter.set_tensor(input_details[0]['index'], dummy_input)
        interpreter.invoke()

        # 実測定
        times = []
        for i in range(10):
            start = time.time()
            interpreter.set_tensor(input_details[0]['index'], dummy_input)
            interpreter.invoke()
            elapsed = time.time() - start
            times.append(elapsed * 1000)  # ms

        avg_time = np.mean(times)
        min_time = np.min(times)
        max_time = np.max(times)

        print(f"\n✅ Inference Speed Test Results:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min:     {min_time:.2f}ms")
        print(f"   Max:     {max_time:.2f}ms")
        print(f"   Expected FPS: {1000/avg_time:.1f}")

        if avg_time < 20:
            print(f"   ✅ PASS: Inference time < 20ms (target met)")
        else:
            print(f"   ⚠️ WARNING: Inference time > 20ms (target not met)")

        return True
    except Exception as e:
        print(f"❌ Error during inference test: {e}")
        return False

def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print("Edge TPU Basic Functionality Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print("=" * 60)

    # テスト実行
    results = {
        "PyCoral Import": test_pycoral_import(),
        "TPU Detection": test_tpu_detection(),
    }

    # モデルテストは前のテストが成功した場合のみ実行
    if results["PyCoral Import"] and results["TPU Detection"]:
        interpreter = test_tpu_model_loading()
        results["Model Loading"] = (interpreter is not None)

        if results["Model Loading"]:
            results["Inference Speed"] = test_tpu_inference_speed()

    # 結果サマリー
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Edge TPU is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the output above.")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
