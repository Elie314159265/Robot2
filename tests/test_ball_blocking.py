#!/usr/bin/env python3
"""
ボールブロッキングテスト - カメラ + TPU検出 + ボールブロック機能

ボールを検出し、画面の左右どちら側に現れたかによって足を上げてブロックします。
- 画面左側にボール → 右後脚(7番) + 右前脚(3番)を5秒間上げる
- 画面右側にボール → 左後脚(5番) + 左前脚(1番)を5秒間上げる

使い方:
  python3 tests/test_ball_blocking.py
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

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import components
from src.camera import CameraController
from src.arduino.pk_serial_controller import PKSerialController
from src.tracking.pid_controller import PIDController
from src.tracking.tracker import BallTracker

# PyCoral インポート
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

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
interpreter = None
labels = []
detection_enabled = True
fps_counter = 0
fps_start_time = time.time()
current_fps = 0
total_detections = 0
ball_detections = 0
avg_inference_time = 0
current_servo_pan = 90
current_servo_tilt = 90
tracking_state = "idle"
blocking_state = "idle"  # idle, blocking_left, blocking_right
total_blocks = 0
block_lock = Lock()  # ブロック動作の排他制御


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
                        output.condition.wait(timeout=5.0)  # 5秒タイムアウト
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
            stats = {
                'fps': current_fps,
                'total_detections': total_detections,
                'ball_detections': ball_detections,
                'inference_time': avg_inference_time,
                'servo_pan': current_servo_pan,
                'servo_tilt': current_servo_tilt,
                'tracking_state': tracking_state,
                'blocking_state': blocking_state,
                'total_blocks': total_blocks
            }
            import json
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
<title>Ball Blocking Test</title>
<style>
body {
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #ffffff;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    text-align: center;
}
h1 {
    background: linear-gradient(90deg, #FF6B6B, #FFA07A);
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
.container {
    max-width: 900px;
    margin: 0 auto;
}
img {
    max-width: 100%;
    border: 3px solid #FF6B6B;
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
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}
.stat-item {
    padding: 10px;
    background: rgba(255, 107, 107, 0.2);
    border-radius: 5px;
    border-left: 3px solid #FF6B6B;
}
.stat-value {
    font-size: 1.8em;
    font-weight: bold;
    color: #FF6B6B;
}
.ball-detected {
    color: #FFD700;
    font-weight: bold;
}
.blocking-badge {
    display: inline-block;
    padding: 5px 15px;
    border-radius: 20px;
    font-weight: bold;
    margin: 5px;
}
.blocking-idle {
    background: #666;
}
.blocking-left {
    background: linear-gradient(90deg, #4CAF50, #8BC34A);
}
.blocking-right {
    background: linear-gradient(90deg, #2196F3, #03A9F4);
}
</style>
</head>
<body>
<div class="container">
<h1>Ball Blocking Test</h1>
<div class="subtitle">Goalkeeper Robot - Ball Detection & Blocking</div>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>システム構成:</strong></p>
    <p>RaspberryPi Camera Module 3 → Google Coral TPU → Arduino → サーボモータ</p>
    <p><strong>動作:</strong> ボールが左側に現れたら右足(7番+3番)、右側なら左足(5番+1番)を5秒間上げる</p>

    <div class="stats">
        <div class="stat-item">
            <div>FPS</div>
            <div class="stat-value" id="fps">--</div>
        </div>
        <div class="stat-item">
            <div>推論時間</div>
            <div class="stat-value" id="inference">--</div>
        </div>
        <div class="stat-item ball-detected">
            <div>ボール検出</div>
            <div class="stat-value" id="balls">0</div>
        </div>
        <div class="stat-item">
            <div>ブロック回数</div>
            <div class="stat-value" id="blocks">0</div>
        </div>
        <div class="stat-item">
            <div>追跡状態</div>
            <div class="stat-value" id="state">idle</div>
        </div>
        <div class="stat-item">
            <div>ブロック状態</div>
            <div class="stat-value" id="block_state">idle</div>
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
            document.getElementById('inference').textContent = data.inference_time.toFixed(1) + 'ms';
            document.getElementById('balls').textContent = data.ball_detections;
            document.getElementById('blocks').textContent = data.total_blocks;
            document.getElementById('state').textContent = data.tracking_state;
            document.getElementById('block_state').textContent = data.blocking_state;
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


def update_detection_stats(detections):
    """検出統計を更新"""
    global total_detections, ball_detections

    total_detections += len(detections)
    for det in detections:
        if det.id == 36 or det.id == 73:  # sports ball (36) or mouse (73)
            ball_detections += 1


def find_ball_detection(detections, frame_width=640, frame_height=480):
    """
    検出結果からボールを抽出

    Args:
        detections: PyCoral検出結果のリスト
        frame_width: フレーム幅
        frame_height: フレーム高さ

    Returns:
        ボールの中心座標dict {'center_x': x, 'center_y': y} or None
    """
    for det in detections:
        if det.id == 36 or det.id == 73:  # sports ball (36) or mouse (73)
            bbox = det.bbox

            # TPUモデルは300x300の座標を返すので、フレームサイズにスケーリング
            input_size = common.input_size(interpreter)  # (300, 300)
            model_w, model_h = input_size[1], input_size[0]

            scale_x = frame_width / model_w
            scale_y = frame_height / model_h

            center_x = ((bbox.xmin + bbox.xmax) / 2) * scale_x
            center_y = ((bbox.ymin + bbox.ymax) / 2) * scale_y

            return {'center_x': center_x, 'center_y': center_y, 'score': det.score}
    return None


def draw_detections(frame, detections):
    """
    フレームに検出結果を描画（PyCoral形式）

    Args:
        frame: 入力フレーム (RGB)
        detections: PyCoral検出結果のリスト

    Returns:
        描画済みフレーム
    """
    h, w = frame.shape[:2]

    # モデルの入力サイズを取得（BBoxはこのサイズに対する座標）
    input_size = common.input_size(interpreter)  # (height, width)
    model_h, model_w = input_size[0], input_size[1]

    # スケーリング係数を計算
    scale_x = w / model_w
    scale_y = h / model_h

    for det in detections:
        # PyCoral BBox形式: det.bbox (BBox object with xmin, ymin, xmax, ymax)
        bbox = det.bbox
        score = det.score
        class_id = det.id

        # BBoxをモデルサイズから元の画像サイズにスケーリング
        xmin = int(bbox.xmin * scale_x)
        ymin = int(bbox.ymin * scale_y)
        xmax = int(bbox.xmax * scale_x)
        ymax = int(bbox.ymax * scale_y)

        # ボール（class 36）またはMouse（class 73）は赤、その他は緑
        if class_id == 36 or class_id == 73:
            color = (255, 0, 0)  # 赤 (RGB)
            label = f"Ball {score:.2f}"
            thickness = 3

            # ボールの中心にクロスヘアを描画
            center_x = (xmin + xmax) // 2
            center_y = (ymin + ymax) // 2
            cv2.drawMarker(frame, (center_x, center_y), (255, 255, 0),
                          cv2.MARKER_CROSS, 20, 2)
        else:
            color = (0, 255, 0)  # 緑
            label_name = labels[class_id] if class_id < len(labels) else f"ID:{class_id}"
            label = f"{label_name} {score:.2f}"
            thickness = 2

        # バウンディングボックスを描画
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, thickness)

        # ラベル背景を描画
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        label_ymin = max(ymin, label_size[1] + 10)
        cv2.rectangle(frame, (xmin, label_ymin - label_size[1] - 10),
                     (xmin + label_size[0], label_ymin), color, -1)
        cv2.putText(frame, label, (xmin, label_ymin - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # 画面中央に分割線を描画
    center_x = w // 2
    cv2.line(frame, (center_x, 0), (center_x, h), (0, 255, 255), 2)
    cv2.putText(frame, "LEFT", (center_x - 120, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(frame, "RIGHT", (center_x + 30, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    return frame


def resize_with_cv2(image_rgb, target_size):
    """
    cv2.resize + INTER_LINEAR で高速リサイズ

    Args:
        image_rgb: RGB numpy array (H x W x 3)
        target_size: (width, height) タプル

    Returns:
        リサイズされたRGB numpy array
    """
    # cv2.resizeは(width, height)の順序
    return cv2.resize(image_rgb, target_size, interpolation=cv2.INTER_LINEAR)


def block_ball_worker(serial_controller, side):
    """
    ボールブロック動作を別スレッドで実行

    Args:
        serial_controller: SerialController instance
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


def process_frames(camera, tracker, serial_controller):
    """
    フレームを処理し、TPUで検出してボールブロック
    """
    global fps_counter, fps_start_time, current_fps, avg_inference_time
    global current_servo_pan, current_servo_tilt, tracking_state

    logger.info("フレーム処理ループ開始")

    frame_count = 0
    last_detections = []
    inference_times = []
    frame_width = 640
    frame_height = 480

    # ブロッククールダウン（連続ブロックを防ぐ）
    last_block_time = 0
    block_cooldown = 6.0  # 6秒間は再度ブロックしない

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

        # TPU検出実行（毎フレーム）
        frame_count += 1
        ball_detection = None

        if detection_enabled and interpreter:
            inference_start = time.time()

            # 画像リサイズ（640x480 → 300x300）
            input_size = common.input_size(interpreter)  # (300, 300)

            # cv2.resize + INTER_LINEAR で高速リサイズ
            resized = resize_with_cv2(frame, (input_size[1], input_size[0]))  # (width, height)

            # uint8型確保
            if resized.dtype != np.uint8:
                resized = resized.astype(np.uint8)

            # TPU推論
            common.set_input(interpreter, resized)
            interpreter.invoke()

            # 検出結果取得（しきい値30%）
            last_detections = detect.get_objects(interpreter, score_threshold=0.3)

            inference_time = (time.time() - inference_start) * 1000
            inference_times.append(inference_time)

            # 統計更新
            update_detection_stats(last_detections)

            # ボールを検出
            ball_detection = find_ball_detection(last_detections)

            # 推論時間の移動平均（最新30フレーム）
            if len(inference_times) > 30:
                inference_times.pop(0)
            avg_inference_time = np.mean(inference_times)

        # トラッカーを更新（追跡のみ、サーボは動かさない）
        pan_angle, tilt_angle = tracker.update(ball_detection)
        current_servo_pan = pan_angle
        current_servo_tilt = tilt_angle
        tracking_state = tracker.state

        # ボールブロック判定
        current_time = time.time()
        if ball_detection and blocking_state == "idle" and (current_time - last_block_time) > block_cooldown:
            ball_x = ball_detection['center_x']
            center_x = frame_width / 2

            # ボールが左側に現れた場合
            if ball_x < center_x:
                logger.info(f"⚽ ボール検出: 左側 (x={ball_x:.1f})")
                last_block_time = current_time
                # 別スレッドでブロック実行（メインループをブロックしない）
                block_thread = Thread(target=block_ball_worker, args=(serial_controller, 'left'))
                block_thread.daemon = True
                block_thread.start()

            # ボールが右側に現れた場合
            else:
                logger.info(f"⚽ ボール検出: 右側 (x={ball_x:.1f})")
                last_block_time = current_time
                # 別スレッドでブロック実行（メインループをブロックしない）
                block_thread = Thread(target=block_ball_worker, args=(serial_controller, 'right'))
                block_thread.daemon = True
                block_thread.start()

        # 検出結果を描画
        if last_detections:
            frame = draw_detections(frame, last_detections)

        # FPS計算
        fps_counter += 1
        if fps_counter >= 30:
            current_fps = fps_counter / (time.time() - fps_start_time)
            fps_counter = 0
            fps_start_time = time.time()

        # FPS表示
        cv2.putText(frame, f"FPS: {current_fps:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Inference: {avg_inference_time:.1f}ms", (10, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"State: {tracking_state}", (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"Block: {blocking_state}", (10, 135),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

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
    print("🛡️  ボールブロッキングテスト - Goalkeeper Robot")
    print("=" * 70)

    # TPUモデル初期化
    model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
    labels_path = "models/coco_labels.txt"

    logger.info(f"📦 TPUモデル読み込み: {model_path}")

    try:
        interpreter = edgetpu.make_interpreter(model_path)
        interpreter.allocate_tensors()
        logger.info("✅ Edge TPU モデル読み込み完了")
    except Exception as e:
        logger.error(f"❌ TPUモデルの読み込み失敗: {e}")
        sys.exit(1)

    # ラベル読み込み
    logger.info(f"📝 ラベル読み込み: {labels_path}")
    with open(labels_path, 'r') as f:
        labels = [line.strip() for line in f.readlines()]
    logger.info(f"✅ {len(labels)} ラベル読み込み完了")

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

    # PID制御器初期化（追跡用、サーボは動かさない）
    logger.info("🎛️  PID制御器を初期化中...")
    pid_pan = PIDController(kp=2.0, ki=0.15, kd=0.3, servo_min=-25, servo_max=25)
    logger.info("✅ PID制御器初期化完了")

    # トラッカー初期化（1軸：水平方向のみ）
    logger.info("🎯 ボールトラッカーを初期化中...")
    tracker = BallTracker(pid_pan, frame_width=640, frame_height=480)
    logger.info("✅ ボールトラッカー初期化完了")

    # Arduinoシリアル通信初期化
    logger.info("📡 Arduinoに接続中...")
    serial_controller = PKSerialController(port="/dev/ttyACM0", baudrate=9600)

    if not serial_controller.connect():
        logger.error("❌ Arduinoへの接続に失敗しました。Arduino接続が必要です。")
        camera.stop()
        camera.cleanup()
        sys.exit(1)
    else:
        logger.info("✅ Arduino接続完了")

    # バックグラウンドでフレーム処理開始
    processing_thread = Thread(
        target=process_frames,
        args=(camera, tracker, serial_controller),
        daemon=True
    )
    processing_thread.start()

    try:
        # サーバー起動
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        logger.info("=" * 70)
        logger.info("🌐 ボールブロッキングストリーミングサーバー起動！")
        logger.info("=" * 70)
        logger.info("ブラウザで以下のURLにアクセスしてください:")
        logger.info("  http://<RaspberryPiのIPアドレス>:8000")
        logger.info("=" * 70)
        logger.info("機能:")
        logger.info("  - カメラでボールを検出")
        logger.info("  - 左側検出 → 右後脚(7番) + 右前脚(3番)を5秒間上げる")
        logger.info("  - 右側検出 → 左後脚(5番) + 左前脚(1番)を5秒間上げる")
        logger.info("=" * 70)
        logger.info("終了するには Ctrl+C を押してください")
        logger.info("=" * 70)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n🛑 停止中...")
    finally:
        camera.stop()
        camera.cleanup()
        serial_controller.disconnect()
        logger.info("✅ システムを終了しました")
