#!/usr/bin/env python3
"""
Hand Landmark モデルの入力・出力形式調査
"""

import numpy as np
from pycoral.utils import edgetpu
from pycoral.adapters import common
import cv2

def inspect_hand_landmark_model(model_path):
    """Hand Landmarkモデルの詳細を調査"""
    print("=" * 70)
    print(f"Hand Landmark Model Inspection: {model_path}")
    print("=" * 70)

    # TPUインタープリタ初期化
    interpreter = edgetpu.make_interpreter(model_path)
    interpreter.allocate_tensors()

    # 入力テンソル情報
    input_details = interpreter.get_input_details()[0]
    print("\n📥 Input Tensor:")
    print(f"  name: {input_details['name']}")
    print(f"  shape: {input_details['shape']}")
    print(f"  dtype: {input_details['dtype']}")
    print(f"  quantization: {input_details['quantization']}")
    print(f"  quantization_parameters: {input_details.get('quantization_parameters', 'N/A')}")

    # 出力テンソル情報
    output_details = interpreter.get_output_details()
    print("\n📤 Output Tensors:")
    for i, detail in enumerate(output_details):
        print(f"  [{i}] name: {detail['name']}")
        print(f"      shape: {detail['shape']}")
        print(f"      dtype: {detail['dtype']}")
        print(f"      quantization: {detail['quantization']}")

    # テスト推論 - UINT8入力
    print("\n🧪 Test 1: UINT8 input (0-255)")
    input_size = common.input_size(interpreter)
    print(f"   Input size: {input_size}")

    # ダミー画像生成（中間グレー）
    dummy_input = np.full((input_size[1], input_size[0], 3), 128, dtype=np.uint8)

    common.set_input(interpreter, dummy_input)
    interpreter.invoke()

    # 出力取得
    for i, detail in enumerate(output_details):
        output_data = interpreter.get_tensor(detail['index'])
        print(f"  Output [{i}]: {output_data.flatten()[:5]} ...")

    # テスト推論 - 実際の手画像風
    print("\n🧪 Test 2: Simulated hand image (brighter)")
    # 明るい領域を持つ画像（手のひらをシミュレート）
    hand_sim = np.random.randint(150, 200, (input_size[1], input_size[0], 3), dtype=np.uint8)

    common.set_input(interpreter, hand_sim)
    interpreter.invoke()

    # 出力取得
    print("  Hand flag and confidence:")
    for i in range(min(2, len(output_details))):
        output_data = interpreter.get_tensor(output_details[i]['index'])
        print(f"    Output [{i}]: {output_data.flatten()[0]:.6f}")

    landmarks_tensor = interpreter.get_tensor(output_details[2]['index'])
    landmarks_flat = landmarks_tensor.flatten()
    print(f"  Landmarks (first 9 values): {landmarks_flat[:9]}")

    print("\n" + "=" * 70)
    print("💡 入力形式の推測:")
    print("=" * 70)
    if input_details['dtype'] == np.uint8:
        scale = input_details['quantization'][0]
        zero_point = input_details['quantization'][1]
        if scale == 0 and zero_point == 0:
            print("  - 量子化パラメータなし → 0-255のUINT8をそのまま入力")
        else:
            print(f"  - 量子化スケール: {scale}")
            print(f"  - ゼロポイント: {zero_point}")
            print(f"  - 実際の値 = (uint8_value - {zero_point}) * {scale}")
    print("=" * 70)


if __name__ == '__main__':
    import sys

    model_path = 'models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite'

    if len(sys.argv) > 1:
        model_path = sys.argv[1]

    try:
        inspect_hand_landmark_model(model_path)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
