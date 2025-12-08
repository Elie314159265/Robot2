#!/usr/bin/env python3
"""
カスタム学習モデルのテストスクリプト
ファインチューニング後のモデルで検出精度を検証
"""

import sys
import time
import argparse
from pathlib import Path
from picamera2 import Picamera2
from pycoral.adapters import detect
from pycoral.utils.edgetpu import make_interpreter

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))


def load_labels(label_path):
    """ラベルファイルを読み込む"""
    with open(label_path, 'r') as f:
        return [line.strip() for line in f.readlines()]


def test_custom_model(model_path, label_path, threshold=0.5, num_frames=100):
    """
    カスタムモデルで検出テスト

    Args:
        model_path: Edge TPUモデルのパス
        label_path: ラベルファイルのパス
        threshold: 検出閾値
        num_frames: テストフレーム数
    """

    print("=== カスタムモデルテスト開始 ===")
    print(f"モデル: {model_path}")
    print(f"ラベル: {label_path}")
    print(f"検出閾値: {threshold}")
    print()

    # 1. ラベル読み込み
    labels = load_labels(label_path)
    print(f"クラス数: {len(labels)}")
    print(f"クラス名: {labels}")
    print()

    # 2. TPUインタプリタ初期化
    print("TPUモデル読み込み中...")
    interpreter = make_interpreter(model_path)
    interpreter.allocate_tensors()

    # 入力サイズ取得
    input_details = interpreter.get_input_details()
    input_shape = input_details[0]['shape']
    input_size = (input_shape[1], input_shape[2])  # (height, width)
    print(f"入力サイズ: {input_size}")
    print()

    # 3. カメラ初期化
    print("カメラ初期化中...")
    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        buffer_count=2
    )
    picam2.configure(config)
    picam2.start()

    # カメラのウォームアップ
    time.sleep(2)
    print("カメラ準備完了")
    print()

    # 4. 検出テスト
    print(f"=== {num_frames}フレームの検出テスト開始 ===")

    detections_count = 0
    total_fps = 0
    inference_times = []

    try:
        for i in range(num_frames):
            start_time = time.time()

            # フレーム取得
            frame = picam2.capture_array()

            # 推論実行
            inference_start = time.time()

            # リサイズして推論
            from PIL import Image
            import numpy as np

            pil_image = Image.fromarray(frame)
            pil_image = pil_image.resize(input_size, Image.LANCZOS)
            input_data = np.array(pil_image)

            # 推論
            interpreter.set_tensor(input_details[0]['index'], [input_data])
            interpreter.invoke()

            # 検出結果取得
            objects = detect.get_objects(interpreter, threshold)

            inference_time = (time.time() - inference_start) * 1000  # ms
            inference_times.append(inference_time)

            # FPS計算
            frame_time = time.time() - start_time
            fps = 1.0 / frame_time if frame_time > 0 else 0
            total_fps += fps

            # 検出結果表示
            if objects:
                detections_count += 1
                print(f"[{i+1}/{num_frames}] 検出: {len(objects)}個 | "
                      f"推論: {inference_time:.1f}ms | FPS: {fps:.1f}")

                for obj in objects:
                    label = labels[obj.id] if obj.id < len(labels) else f"Unknown({obj.id})"
                    bbox = obj.bbox
                    print(f"  - {label}: {obj.score:.2f} "
                          f"[{bbox.xmin}, {bbox.ymin}, {bbox.xmax}, {bbox.ymax}]")
            else:
                # 検出なしは10フレームごとに表示
                if (i + 1) % 10 == 0:
                    print(f"[{i+1}/{num_frames}] 検出なし | "
                          f"推論: {inference_time:.1f}ms | FPS: {fps:.1f}")

    except KeyboardInterrupt:
        print("\n中断されました")

    finally:
        picam2.stop()

    # 5. 統計表示
    print("\n=== テスト結果 ===")
    print(f"総フレーム数: {num_frames}")
    print(f"検出フレーム数: {detections_count}")
    print(f"検出率: {detections_count/num_frames*100:.1f}%")
    print(f"平均FPS: {total_fps/num_frames:.1f}")
    print(f"平均推論時間: {sum(inference_times)/len(inference_times):.1f}ms")
    print(f"最小推論時間: {min(inference_times):.1f}ms")
    print(f"最大推論時間: {max(inference_times):.1f}ms")

    # 成功基準チェック
    print("\n=== 成功基準チェック ===")
    detection_rate = detections_count / num_frames * 100
    avg_fps = total_fps / num_frames

    if detection_rate >= 80:
        print(f"✓ 検出率: {detection_rate:.1f}% (目標: 80%以上)")
    else:
        print(f"✗ 検出率: {detection_rate:.1f}% (目標: 80%以上) - 改善が必要")

    if avg_fps >= 30:
        print(f"✓ FPS: {avg_fps:.1f} (目標: 30以上)")
    else:
        print(f"△ FPS: {avg_fps:.1f} (目標: 30以上) - 許容範囲内")


def main():
    parser = argparse.ArgumentParser(description='カスタムモデルのテスト')
    parser.add_argument('--model', type=str,
                       default='models/best_int8_edgetpu.tflite',
                       help='Edge TPUモデルのパス')
    parser.add_argument('--labels', type=str,
                       default='models/labels.txt',
                       help='ラベルファイルのパス')
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='検出閾値 (0.0-1.0)')
    parser.add_argument('--frames', type=int, default=100,
                       help='テストフレーム数')

    args = parser.parse_args()

    # パス確認
    model_path = Path(args.model)
    label_path = Path(args.labels)

    if not model_path.exists():
        print(f"エラー: モデルが見つかりません: {model_path}")
        print("\nGoogle Colabで学習したモデルをmodels/に配置してください")
        sys.exit(1)

    if not label_path.exists():
        print(f"エラー: ラベルファイルが見つかりません: {label_path}")
        sys.exit(1)

    # テスト実行
    test_custom_model(
        str(model_path),
        str(label_path),
        args.threshold,
        args.frames
    )


if __name__ == "__main__":
    main()
