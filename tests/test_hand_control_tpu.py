#!/usr/bin/env python3
"""
手指検出・サーボ制御テスト (TPU版)

Google Coral TPUとhand_landmark_newモデルを使用して人の手と指の角度を検出し、
サーボモータの角度にマッピングして制御します。

サーボ割り当て:
- 左手: 親指(0番), 人差し指(2番), 中指(4番), 薬指(6番)
- 右手: 親指(1番), 人差し指(3番), 中指(5番), 薬指(7番)

使い方:
  python3 tests/test_hand_control_tpu.py
  ブラウザで http://<RaspberryPiのIPアドレス>:8000 にアクセス
"""

import io
import sys
import os
import time
import logging
from threading import Condition, Thread, Lock
from http.server import BaseHTTPRequestHandler, HTTPServer
import cv2
import numpy as np
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import components
from src.camera import CameraController
from src.arduino.serial_controller import SerialController
from src.hand_control import HandDetectorTPU, FingerMapper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ストリーミング出力クラス
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self.frame_count = 0

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.frame_count += 1
            if self.frame_count % 30 == 0:
                logger.info(f"ストリーム出力: {self.frame_count} フレーム送信完了")
            self.condition.notify_all()


# グローバル変数
output = StreamingOutput()
hand_detector = None
finger_mapper = None
serial_controller = None
fps_counter = 0
fps_start_time = time.time()
current_fps = 0
total_detections = 0
left_hand_detections = 0
right_hand_detections = 0
avg_detection_time = 0
current_servo_states = {}  # {channel: angle}
servo_lock = Lock()


# HTTPリクエストハンドラ
class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            logger.info(f"📹 ストリーミングクライアント接続: {self.client_address}")
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                frame_sent = 0
                while True:
                    with output.condition:
                        if output.frame is None:
                            logger.warning("⚠️  フレームが利用不可、待機中...")
                        output.condition.wait(timeout=5.0)
                        frame = output.frame

                    if frame is None:
                        logger.warning("⚠️  タイムアウト後もフレームがNone")
                        continue

                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')

                    frame_sent += 1
                    if frame_sent == 1:
                        logger.info(f"✅ 最初のフレームをクライアントに送信")
            except Exception as e:
                logger.warning(f'Removed streaming client {self.client_address}: {str(e)}')
        elif self.path == '/stats':
            # 統計情報をJSON形式で返す
            with servo_lock:
                servo_states_copy = current_servo_states.copy()

            stats = {
                'fps': current_fps,
                'total_detections': total_detections,
                'left_hand_detections': left_hand_detections,
                'right_hand_detections': right_hand_detections,
                'detection_time': avg_detection_time,
                'servo_states': servo_states_copy
            }
            content = json.dumps(stats).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)
            self.end_headers()

    def log_message(self, format, *args):
        # アクセスログを抑制
        return


# HTMLページ
PAGE = """\
<html>
<head>
<meta charset="utf-8">
<title>Hand Control Test (TPU)</title>
<style>
body {
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    text-align: center;
}
h1 {
    background: linear-gradient(90deg, #FFD700, #FFA500);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5em;
    margin-bottom: 10px;
}
.subtitle {
    color: #FFD700;
    font-size: 1.2em;
    margin-bottom: 20px;
}
.tpu-badge {
    background: linear-gradient(90deg, #00C9FF, #92FE9D);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.5em;
    font-weight: bold;
    margin-bottom: 20px;
}
.container {
    max-width: 1100px;
    margin: 0 auto;
}
img {
    max-width: 100%;
    border: 3px solid #FFD700;
    border-radius: 12px;
    box-shadow: 0 8px 16px rgba(0,0,0,0.4);
}
.info {
    margin-top: 20px;
    padding: 20px;
    background: rgba(42, 42, 42, 0.8);
    border-radius: 10px;
    display: inline-block;
    text-align: left;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}
.stats {
    margin-top: 15px;
    padding: 15px;
    background: rgba(51, 51, 51, 0.9);
    border-radius: 8px;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
}
.stat-item {
    padding: 10px;
    background: rgba(255, 215, 0, 0.2);
    border-radius: 5px;
    border-left: 3px solid #FFD700;
}
.stat-value {
    font-size: 1.8em;
    font-weight: bold;
    color: #FFD700;
}
.servo-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-top: 20px;
}
.hand-section {
    background: rgba(51, 51, 51, 0.9);
    padding: 15px;
    border-radius: 8px;
}
.hand-section h3 {
    color: #FFD700;
    margin-top: 0;
}
.finger-item {
    display: flex;
    justify-content: space-between;
    padding: 8px;
    margin: 5px 0;
    background: rgba(102, 126, 234, 0.3);
    border-radius: 5px;
}
.finger-name {
    font-weight: bold;
}
.finger-angle {
    color: #FFD700;
    font-family: monospace;
}
</style>
</head>
<body>
<div class="container">
<h1>Hand Control Test</h1>
<div class="tpu-badge">⚡ Google Coral TPU Edition ⚡</div>
<div class="subtitle">Hand Gesture Recognition → Servo Control</div>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>システム構成:</strong></p>
    <p>RaspberryPi Camera → Google Coral TPU (hand_landmark_new) → PCA9685 Servo Driver</p>
    <p><strong>サーボ割り当て:</strong></p>
    <p>左手: 親指(0), 人差し指(2), 中指(4), 薬指(6)</p>
    <p>右手: 親指(1), 人差し指(3), 中指(5), 薬指(7)</p>

    <div class="stats">
        <div class="stat-item">
            <div>FPS</div>
            <div class="stat-value" id="fps">--</div>
        </div>
        <div class="stat-item">
            <div>検出時間</div>
            <div class="stat-value" id="detection">--</div>
        </div>
        <div class="stat-item">
            <div>総検出回数</div>
            <div class="stat-value" id="total">0</div>
        </div>
        <div class="stat-item">
            <div>左手検出</div>
            <div class="stat-value" id="left">0</div>
        </div>
        <div class="stat-item">
            <div>右手検出</div>
            <div class="stat-value" id="right">0</div>
        </div>
    </div>

    <div class="servo-grid">
        <div class="hand-section">
            <h3>左手</h3>
            <div class="finger-item">
                <span class="finger-name">親指 (Ch 0)</span>
                <span class="finger-angle" id="left_thumb">--°</span>
            </div>
            <div class="finger-item">
                <span class="finger-name">人差し指 (Ch 2)</span>
                <span class="finger-angle" id="left_index">--°</span>
            </div>
            <div class="finger-item">
                <span class="finger-name">中指 (Ch 4)</span>
                <span class="finger-angle" id="left_middle">--°</span>
            </div>
            <div class="finger-item">
                <span class="finger-name">薬指 (Ch 6)</span>
                <span class="finger-angle" id="left_ring">--°</span>
            </div>
        </div>

        <div class="hand-section">
            <h3>右手</h3>
            <div class="finger-item">
                <span class="finger-name">親指 (Ch 1)</span>
                <span class="finger-angle" id="right_thumb">--°</span>
            </div>
            <div class="finger-item">
                <span class="finger-name">人差し指 (Ch 3)</span>
                <span class="finger-angle" id="right_index">--°</span>
            </div>
            <div class="finger-item">
                <span class="finger-name">中指 (Ch 5)</span>
                <span class="finger-angle" id="right_middle">--°</span>
            </div>
            <div class="finger-item">
                <span class="finger-name">薬指 (Ch 7)</span>
                <span class="finger-angle" id="right_ring">--°</span>
            </div>
        </div>
    </div>
</div>
</div>

<script>
// 統計情報を定期的に更新
setInterval(function() {
    fetch('/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('fps').textContent = data.fps.toFixed(1);
            document.getElementById('detection').textContent = data.detection_time.toFixed(1) + 'ms';
            document.getElementById('total').textContent = data.total_detections;
            document.getElementById('left').textContent = data.left_hand_detections;
            document.getElementById('right').textContent = data.right_hand_detections;

            // サーボ状態を更新
            const servos = data.servo_states;
            document.getElementById('left_thumb').textContent = servos[0] !== undefined ? servos[0] + '°' : '--°';
            document.getElementById('left_index').textContent = servos[2] !== undefined ? servos[2] + '°' : '--°';
            document.getElementById('left_middle').textContent = servos[4] !== undefined ? servos[4] + '°' : '--°';
            document.getElementById('left_ring').textContent = servos[6] !== undefined ? servos[6] + '°' : '--°';
            document.getElementById('right_thumb').textContent = servos[1] !== undefined ? servos[1] + '°' : '--°';
            document.getElementById('right_index').textContent = servos[3] !== undefined ? servos[3] + '°' : '--°';
            document.getElementById('right_middle').textContent = servos[5] !== undefined ? servos[5] + '°' : '--°';
            document.getElementById('right_ring').textContent = servos[7] !== undefined ? servos[7] + '°' : '--°';
        })
        .catch(err => console.error('Stats update failed:', err));
}, 500);  // 0.5秒ごとに更新
</script>
</body>
</html>
"""


class StreamingServer(HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def update_servo_states(servo_commands: dict):
    """サーボ状態を更新"""
    global current_servo_states
    with servo_lock:
        for channel, angle in servo_commands.items():
            current_servo_states[channel] = angle


def process_frames(camera, detector, mapper, serial):
    """
    フレームを処理し、手を検出してサーボ制御
    """
    global fps_counter, fps_start_time, current_fps, avg_detection_time
    global total_detections, left_hand_detections, right_hand_detections

    logger.info("フレーム処理ループ開始")

    frame_count = 0
    detection_times = []

    while True:
        # フレーム取得
        frame = camera.capture_frame()
        if frame is None:
            if frame_count % 30 == 0:
                logger.warning("⚠️  フレーム取得失敗（None）")
            continue

        # 最初のフレーム取得成功をログ
        if frame_count == 0:
            logger.info(f"✅ 最初のフレーム取得成功: shape={frame.shape}, dtype={frame.dtype}")

        frame_count += 1

        # 手検出実行
        detection_start = time.time()
        hand_data = detector.detect(frame)
        detection_time = (time.time() - detection_start) * 1000
        detection_times.append(detection_time)

        # 検出時間の移動平均（最新30フレーム）
        if len(detection_times) > 30:
            detection_times.pop(0)
        avg_detection_time = np.mean(detection_times)

        # 検出統計を更新
        hands_detected = 0
        if hand_data['left_hand']:
            left_hand_detections += 1
            hands_detected += 1
        if hand_data['right_hand']:
            right_hand_detections += 1
            hands_detected += 1

        if hands_detected > 0:
            total_detections += 1

            # 指の角度をサーボ角度にマッピング
            servo_commands = mapper.map_hand_to_servos(hand_data)

            # サーボ状態を更新（表示用）
            update_servo_states(servo_commands)

            # Arduinoにサーボコマンドを送信
            if serial:
                for channel, angle in servo_commands.items():
                    serial.send_servo_command(channel, angle)

            # ログ出力（デバッグ用、30フレームに1回）
            if frame_count % 30 == 0:
                logger.info(f"手検出: L={hand_data['left_hand'] is not None}, "
                           f"R={hand_data['right_hand'] is not None}, "
                           f"サーボ更新: {len(servo_commands)}ch")

        # ランドマークを描画
        frame = detector.draw_landmarks(frame)

        # FPS計算
        fps_counter += 1
        if fps_counter >= 30:
            current_fps = fps_counter / (time.time() - fps_start_time)
            fps_counter = 0
            fps_start_time = time.time()

        # 情報を画面に表示
        cv2.putText(frame, f"FPS: {current_fps:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Detection: {avg_detection_time:.1f}ms (TPU)", (10, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # 手検出状態を表示
        status_text = "Hands: "
        if hand_data['left_hand']:
            status_text += "LEFT "
        if hand_data['right_hand']:
            status_text += "RIGHT"
        if not hand_data['left_hand'] and not hand_data['right_hand']:
            status_text += "NONE"

        cv2.putText(frame, status_text, (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # BGRに変換してJPEGエンコード
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        _, jpeg = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])

        # ストリーミング出力に書き込み
        jpeg_bytes = jpeg.tobytes()
        with output.condition:
            output.frame = jpeg_bytes
            output.condition.notify_all()

        # 最初のフレーム出力成功をログ
        if frame_count == 1:
            logger.info(f"✅ 最初のJPEGフレーム出力成功: {len(jpeg_bytes)} bytes")


if __name__ == '__main__':
    print("=" * 70)
    print("🖐️  手指検出・サーボ制御テスト (TPU版)")
    print("=" * 70)

    # HandDetectorTPU初期化
    logger.info("⚡ Google Coral TPU初期化中...")
    try:
        hand_detector = HandDetectorTPU(
            model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
            palm_model_path='models/palm_detection_builtin_256_integer_quant.tflite',
            max_num_hands=2,  # 両手検出
            min_detection_confidence=0.01,  # 閾値を大幅に下げて検出テスト
            min_palm_confidence=0.5
        )
        logger.info("✅ TPU初期化完了")
    except Exception as e:
        logger.error(f"❌ TPU初期化失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # FingerMapper初期化
    logger.info("🎛️  FingerMapper初期化中...")
    finger_mapper = FingerMapper(
        servo_min=0,
        servo_max=180,
        angle_min=0.0,
        angle_max=180.0,
        invert_mapping=False
    )
    logger.info("✅ FingerMapper初期化完了")

    # カメラ初期化
    logger.info("📷 カメラを初期化中...")
    camera = CameraController(resolution=(640, 480), framerate=30, debug=False)

    if not camera.initialize():
        logger.error("❌ カメラの初期化に失敗しました")
        sys.exit(1)

    if not camera.start():
        logger.error("❌ カメラの起動に失敗しました")
        camera.cleanup()
        sys.exit(1)

    time.sleep(2)  # カメラウォームアップ
    logger.info("✅ カメラ初期化完了")

    # Arduinoシリアル通信初期化（オプション）
    logger.info("📡 Arduinoに接続中...")
    serial_controller = SerialController(port="/dev/ttyACM0", baudrate=9600)

    if not serial_controller.connect():
        logger.warning("⚠️  Arduinoへの接続に失敗しました。サーボ制御なしで続行します。")
        serial_controller = None
    else:
        logger.info("✅ Arduino接続完了")

    # バックグラウンドでフレーム処理開始
    processing_thread = Thread(
        target=process_frames,
        args=(camera, hand_detector, finger_mapper, serial_controller),
        daemon=True
    )
    processing_thread.start()

    try:
        # サーバー起動
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        logger.info("=" * 70)
        logger.info("🌐 手指検出ストリーミングサーバー起動！(TPU版)")
        logger.info("=" * 70)
        logger.info("ブラウザで以下のURLにアクセスしてください:")
        logger.info("  http://<RaspberryPiのIPアドレス>:8000")
        logger.info("=" * 70)
        logger.info("機能:")
        logger.info("  - Google Coral TPUで高速手指検出")
        logger.info("  - 左手: 親指(0), 人差し指(2), 中指(4), 薬指(6)")
        logger.info("  - 右手: 親指(1), 人差し指(3), 中指(5), 薬指(7)")
        logger.info("=" * 70)
        logger.info("終了するには Ctrl+C を押してください")
        logger.info("=" * 70)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n🛑 停止中...")
    finally:
        camera.stop()
        camera.cleanup()
        if serial_controller:
            serial_controller.disconnect()
        hand_detector.cleanup()
        logger.info("✅ システムを終了しました")
