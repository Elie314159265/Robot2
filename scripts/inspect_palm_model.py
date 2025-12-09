#!/usr/bin/env python3
"""
Palm Detection モデルの出力形式調査スクリプト

手のひら検出モデルの入力・出力テンソル情報を詳細に出力します。
"""

import numpy as np
import tflite_runtime.interpreter as tflite
import cv2

def inspect_palm_model(model_path):
    """Palm Detectionモデルの詳細を調査"""
    print("=" * 70)
    print(f"Palm Detection Model Inspection: {model_path}")
    print("=" * 70)

    # インタープリタ初期化
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    # 入力テンソル情報
    input_details = interpreter.get_input_details()
    print("\n📥 Input Tensors:")
    for i, detail in enumerate(input_details):
        print(f"  [{i}] name: {detail['name']}")
        print(f"      shape: {detail['shape']}")
        print(f"      dtype: {detail['dtype']}")
        print(f"      quantization: {detail['quantization']}")

    # 出力テンソル情報
    output_details = interpreter.get_output_details()
    print("\n📤 Output Tensors:")
    for i, detail in enumerate(output_details):
        print(f"  [{i}] name: {detail['name']}")
        print(f"      shape: {detail['shape']}")
        print(f"      dtype: {detail['dtype']}")
        print(f"      quantization: {detail['quantization']}")

    # ダミー入力でテスト推論
    print("\n🧪 Test Inference with Dummy Input:")
    input_shape = input_details[0]['shape']
    print(f"   Creating dummy image: {input_shape}")

    # ダミー画像生成（黒画像）
    input_dtype = input_details[0]['dtype']
    if input_dtype == np.float32:
        # Float32モデルの場合は0-1の範囲に正規化
        dummy_input = np.zeros(input_shape, dtype=np.float32)
    else:
        dummy_input = np.zeros(input_shape, dtype=np.uint8)

    print(f"   Input dtype: {input_dtype}")

    # 推論実行
    interpreter.set_tensor(input_details[0]['index'], dummy_input)
    interpreter.invoke()

    # 出力テンソル取得
    print("\n📊 Output Tensor Contents:")
    for i, detail in enumerate(output_details):
        output_data = interpreter.get_tensor(detail['index'])
        print(f"  [{i}] {detail['name']}:")
        print(f"      shape: {output_data.shape}")
        print(f"      dtype: {output_data.dtype}")
        print(f"      min: {output_data.min()}, max: {output_data.max()}")
        print(f"      sample values: {output_data.flatten()[:10]}")

    print("\n" + "=" * 70)
    print("💡 Interpretation Guide:")
    print("=" * 70)
    print("典型的なPalm Detectionモデルの出力:")
    print("  - Bounding boxes: (1, N, 4) - N個の検出結果、各4値 [ymin, xmin, ymax, xmax]")
    print("  - Scores: (1, N) - 各検出結果の信頼度スコア")
    print("  - Classes: (1, N) - クラスID（手のひらは通常0）")
    print("  - Num detections: (1,) - 有効な検出数")
    print("\n  OR SSDスタイル:")
    print("  - detection_boxes: (1, 10, 4) - バウンディングボックス")
    print("  - detection_classes: (1, 10) - クラスID")
    print("  - detection_scores: (1, 10) - スコア")
    print("  - num_detections: (1,) - 検出数")
    print("\n  OR MediaPipeスタイル:")
    print("  - regressors: (1, 2944, 18) - アンカーボックスの調整値")
    print("  - classificators: (1, 2944, 1) - 各アンカーの手のひらスコア")
    print("  ※この場合、Non-Maximum Suppression (NMS)が必要")
    print("=" * 70)


if __name__ == '__main__':
    import sys

    model_path = 'models/palm_detection_builtin_256_integer_quant.tflite'

    if len(sys.argv) > 1:
        model_path = sys.argv[1]

    try:
        inspect_palm_model(model_path)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
