#!/usr/bin/env python3
"""
カメラプレビュー（OpenCV版）
リアルタイムでカメラ映像を表示

使い方:
  python3 scripts/camera_preview.py

注意:
  - ディスプレイが必要です（SSH経由の場合はX11転送が必要）
  - 'q'キーで終了
"""

import cv2
import numpy as np
from picamera2 import Picamera2
import time

def main():
    print("=" * 60)
    print("カメラプレビュー起動中...")
    print("=" * 60)

    # カメラ初期化
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()

    print("✅ カメラ起動完了")
    print("   'q'キーで終了")
    print("=" * 60)

    # FPS計測用
    fps_counter = 0
    fps_start_time = time.time()
    fps = 0

    try:
        while True:
            # フレーム取得
            frame = picam2.capture_array()

            # FPS計測
            fps_counter += 1
            if fps_counter >= 30:
                fps = fps_counter / (time.time() - fps_start_time)
                fps_counter = 0
                fps_start_time = time.time()

            # 情報をオーバーレイ
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, 470),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # BGRに変換（OpenCVはBGRフォーマット）
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # 表示
            cv2.imshow('Camera Preview - Robot PK', frame_bgr)

            # 'q'キーで終了
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n停止中...")
    except Exception as e:
        print(f"エラー: {e}")
    finally:
        picam2.stop()
        picam2.close()
        cv2.destroyAllWindows()
        print("カメラプレビューを終了しました")

if __name__ == "__main__":
    main()
