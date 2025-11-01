#!/usr/bin/env python3
"""
Simple script to check if Raspberry Pi Camera Module 3 is connected and working
"""

import sys

# Add libcamera path for RaspberryPi
sys.path.insert(0, '/usr/lib/aarch64-linux-gnu/python3.12/site-packages')

try:
    from picamera2 import Picamera2

    print("=" * 60)
    print("Raspberry Pi Camera Module 3 接続確認")
    print("=" * 60)

    # Check available cameras
    cameras = Picamera2.global_camera_info()

    if len(cameras) == 0:
        print("\n❌ カメラが検出されませんでした")
        print("\n確認事項:")
        print("  1. Camera Module 3が物理的に接続されているか")
        print("  2. カメラリボンケーブルが両端でしっかり挿入されているか")
        print("  3. ケーブルの向きが正しいか（青い面の向き）")
        print("  4. Raspberry Piを再起動してみる")
        print("\n再起動コマンド: sudo reboot")
        sys.exit(1)

    print(f"\n✅ {len(cameras)}台のカメラが検出されました\n")

    for i, cam_info in enumerate(cameras):
        print(f"カメラ {i}:")
        for key, value in cam_info.items():
            print(f"  {key}: {value}")
        print()

    # Try to initialize camera
    print("カメラの初期化を試行中...")
    try:
        picam = Picamera2()
        config = picam.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        picam.configure(config)

        print("✅ カメラの設定が完了しました")
        print(f"   解像度: 640x480")
        print(f"   フォーマット: RGB888")

        # Get camera properties
        print("\nカメラプロパティ:")
        props = picam.camera_properties
        for key, value in props.items():
            print(f"  {key}: {value}")

        picam.close()

        print("\n" + "=" * 60)
        print("✅ カメラは正常に動作しています！")
        print("=" * 60)
        print("\n次のステップ:")
        print("  python3 tests/test_camera.py")

    except Exception as e:
        print(f"\n❌ カメラ初期化エラー: {e}")
        sys.exit(1)

except ImportError as e:
    print(f"❌ picamera2ライブラリがインストールされていません")
    print(f"   インストール: sudo apt install -y python3-picamera2")
    sys.exit(1)
except Exception as e:
    print(f"❌ エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
