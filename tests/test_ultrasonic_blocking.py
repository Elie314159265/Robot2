#!/usr/bin/env python3
"""
超音波センサーボールブロッキングテスト

超音波センサーで物体を検出し、左右どちら側に現れたかによって足を上げてブロックします。
- 左側センサー検知 → 右後脚(7番) + 右前脚(3番)を5秒間上げる
- 右側センサー検知 → 左後脚(5番) + 左前脚(1番)を5秒間上げる

配線:
  左側センサー(HC-SR04): Trig=D8, Echo=D9
  右側センサー(HC-SR04): Trig=D10, Echo=D11

使い方:
  python3 tests/test_ultrasonic_blocking.py
"""

import sys
import os
import time
import logging
from threading import Thread, Lock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import components
from src.arduino.pk_serial_controller import PKSerialController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# グローバル変数
blocking_state = "idle"  # idle, blocking_left, blocking_right
total_blocks = 0
block_lock = Lock()  # ブロック動作の排他制御


def block_ball_worker(serial_controller, side):
    """
    ボールブロック動作を別スレッドで実行

    Args:
        serial_controller: PKSerialController instance
        side: 'left' or 'right'
    """
    global blocking_state, total_blocks

    with block_lock:  # ブロック動作の排他制御
        blocking_state = f"blocking_{side}"
        logger.info(f"🛡️  ボールブロック開始: {side}側")

        if side == 'left':
            serial_controller.block_ball_left()
        else:
            serial_controller.block_ball_right()

        total_blocks += 1
        blocking_state = "idle"
        logger.info(f"✅ ブロック完了 (累計: {total_blocks}回)")


def monitor_ultrasonic_sensors(serial_controller):
    """
    超音波センサーを監視してボールブロック

    Args:
        serial_controller: PKSerialController instance
    """
    global blocking_state

    logger.info("超音波センサー監視開始")

    # ブロッククールダウン（連続ブロックを防ぐ）
    last_block_time = 0
    block_cooldown = 6.0  # 6秒間は再度ブロックしない

    # 検出閾値（cm）
    DETECTION_THRESHOLD = 30.0  # 30cm以内で検出

    sample_count = 0

    while True:
        current_time = time.time()

        # 左右のセンサーを交互に読み取り
        distance_left = serial_controller.read_distance('L')
        time.sleep(0.1)  # センサー間隔を開ける
        distance_right = serial_controller.read_distance('R')

        sample_count += 1

        # 10回に1回ログ出力
        if sample_count % 10 == 0:
            logger.info(f"距離: 左={distance_left:.1f}cm, 右={distance_right:.1f}cm")

        # ブロック判定
        if blocking_state == "idle" and (current_time - last_block_time) > block_cooldown:
            # 左側センサーが物体検知
            if distance_left is not None and 0 < distance_left < DETECTION_THRESHOLD:
                logger.info(f"⚽ 物体検出: 左側 (距離={distance_left:.1f}cm)")
                last_block_time = current_time
                # 別スレッドでブロック実行（メインループをブロックしない）
                block_thread = Thread(target=block_ball_worker, args=(serial_controller, 'left'))
                block_thread.daemon = True
                block_thread.start()

            # 右側センサーが物体検知
            elif distance_right is not None and 0 < distance_right < DETECTION_THRESHOLD:
                logger.info(f"⚽ 物体検出: 右側 (距離={distance_right:.1f}cm)")
                last_block_time = current_time
                # 別スレッドでブロック実行（メインループをブロックしない）
                block_thread = Thread(target=block_ball_worker, args=(serial_controller, 'right'))
                block_thread.daemon = True
                block_thread.start()

        time.sleep(0.2)  # 200msごとにチェック（約5Hz）


if __name__ == '__main__':
    print("=" * 70)
    print("🛡️  超音波センサーボールブロッキングテスト - Goalkeeper Robot")
    print("=" * 70)

    # Arduinoシリアル通信初期化
    logger.info("📡 Arduinoに接続中...")
    serial_controller = PKSerialController(port="/dev/ttyACM0", baudrate=9600)

    if not serial_controller.connect():
        logger.error("❌ Arduinoへの接続に失敗しました。Arduino接続が必要です。")
        sys.exit(1)
    else:
        logger.info("✅ Arduino接続完了")

    try:
        logger.info("=" * 70)
        logger.info("🌐 超音波センサー監視開始")
        logger.info("=" * 70)
        logger.info("機能:")
        logger.info("  - 超音波センサーで物体を検出")
        logger.info("  - 左側検出 → 右後脚(7番) + 右前脚(3番)を5秒間上げる")
        logger.info("  - 右側検出 → 左後脚(5番) + 左前脚(1番)を5秒間上げる")
        logger.info("  - 検出閾値: 30cm以内")
        logger.info("=" * 70)
        logger.info("終了するには Ctrl+C を押してください")
        logger.info("=" * 70)

        # 超音波センサー監視開始
        monitor_ultrasonic_sensors(serial_controller)

    except KeyboardInterrupt:
        logger.info("\n🛑 停止中...")
    finally:
        serial_controller.disconnect()
        logger.info("✅ システムを終了しました")
