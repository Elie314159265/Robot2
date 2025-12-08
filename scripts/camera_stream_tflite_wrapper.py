#!/usr/bin/env python3
"""
TFLiteEdgeTPUラッパー版 カメラストリーミング
元のCPU版と同じ方法（PIL + LANCZOS補間 + TFLiteラッパー）を使用

使い方:
  python3 scripts/camera_stream_tflite_wrapper.py
  ブラウザで http://<RaspberryPiのIPアドレス>:8000 にアクセス
"""

import io
import sys
import os
import time
import logging
from threading import Condition, Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import CameraController and TFLiteEdgeTPU wrapper
from src.camera import CameraController
from src.detection.tflite_wrapper import TFLiteEdgeTPU

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ストリーミング出力クラス
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


# グローバル変数
output = StreamingOutput()
detector = None
detection_enabled = True
fps_counter = 0
fps_start_time = time.time()
current_fps = 0
total_detections = 0
ball_detections = 0
avg_inference_time = 0


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
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logger.warning(f'Removed streaming client {self.client_address}: {str(e)}')
        elif self.path == '/stats':
            stats = {
                'fps': current_fps,
                'total_detections': total_detections,
                'ball_detections': ball_detections,
                'inference_time': avg_inference_time
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
        return


# HTMLページ
PAGE = """\
<html>
<head>
<meta charset="utf-8">
<title>⚽ TFLite Wrapper Ball Detection</title>
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
    background: linear-gradient(90deg, #4CAF50, #8BC34A);
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
    border: 3px solid #4CAF50;
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
    background: rgba(76, 175, 80, 0.2);
    border-radius: 5px;
    border-left: 3px solid #4CAF50;
}
.stat-value {
    font-size: 1.8em;
    font-weight: bold;
    color: #4CAF50;
}
.ball-detected {
    color: #FFD700;
    font-weight: bold;
}
.legend {
    margin-top: 20px;
    padding: 15px;
    background: rgba(42, 42, 42, 0.8);
    border-radius: 8px;
    text-align: left;
}
.legend-item {
    margin: 8px 0;
    display: flex;
    align-items: center;
}
.box-ball {
    width: 24px;
    height: 24px;
    background-color: rgba(255, 0, 0, 0.8);
    border: 2px solid red;
    margin-right: 10px;
    border-radius: 3px;
}
.box-other {
    width: 24px;
    height: 24px;
    background-color: rgba(0, 255, 0, 0.3);
    border: 2px solid lime;
    margin-right: 10px;
    border-radius: 3px;
}
.tpu-badge {
    display: inline-block;
    background: linear-gradient(90deg, #4CAF50, #8BC34A);
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    font-weight: bold;
    margin: 10px 0;
}
.wrapper-badge {
    display: inline-block;
    background: linear-gradient(90deg, #f093fb, #f5576c);
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    font-weight: bold;
    margin: 10px 5px;
}
</style>
</head>
<body>
<div class="container">
<h1>⚽ TFLite Wrapper Ball Detection</h1>
<div class="subtitle">🚀 元のスクリプトと同じ方法（PIL + LANCZOS）</div>
<div class="tpu-badge">✨ Powered by Google Coral Edge TPU</div>
<div class="wrapper-badge">🔧 TFLite Wrapper Version</div>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>📷 カメラ:</strong> RaspberryPi Camera Module 3</p>
    <p><strong>🎯 解像度:</strong> 640x480 @ 30fps</p>
    <p><strong>🧠 モデル:</strong> SSD MobileNet v2 COCO (TPU版)</p>
    <p><strong>🔧 実装:</strong> TFLiteEdgeTPUラッパー</p>
    <p><strong>⚡ リサイズ:</strong> PIL + LANCZOS高品質補間</p>
    <p><strong>🎪 ターゲット:</strong> Sports Ball (COCO Class 37)</p>

    <div class="stats">
        <div class="stat-item">
            <div>FPS</div>
            <div class="stat-value" id="fps">--</div>
        </div>
        <div class="stat-item">
            <div>推論時間</div>
            <div class="stat-value" id="inference">--</div>
        </div>
        <div class="stat-item">
            <div>総検出数</div>
            <div class="stat-value" id="total">0</div>
        </div>
        <div class="stat-item ball-detected">
            <div>⚽ ボール検出</div>
            <div class="stat-value" id="balls">0</div>
        </div>
    </div>
</div>
<div class="legend">
    <p><strong>🎨 検出表示:</strong></p>
    <div class="legend-item"><span class="box-ball"></span> スポーツボール（赤色・太線）</div>
    <div class="legend-item"><span class="box-other"></span> その他のオブジェクト（緑色）</div>
</div>
</div>

<script>
setInterval(function() {
    fetch('/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('fps').textContent = data.fps.toFixed(1);
            document.getElementById('inference').textContent = data.inference_time.toFixed(1) + 'ms';
            document.getElementById('total').textContent = data.total_detections;
            document.getElementById('balls').textContent = data.ball_detections;
        })
        .catch(err => console.error('Stats update failed:', err));
}, 500);
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
        if det['class_id'] == 37:  # sports ball
            ball_detections += 1


def draw_detections(frame, detections):
    """
    フレームに検出結果を描画

    Args:
        frame: 入力フレーム (RGB)
        detections: 検出結果のリスト

    Returns:
        描画済みフレーム
    """
    h, w = frame.shape[:2]

    for det in detections:
        class_id = det['class_id']
        score = det['score']
        bbox = det['bbox']  # [ymin, xmin, ymax, xmax] normalized

        # 座標を画像サイズに変換
        ymin = int(bbox[0] * h)
        xmin = int(bbox[1] * w)
        ymax = int(bbox[2] * h)
        xmax = int(bbox[3] * w)

        # ボール（class 37）は赤、その他は緑
        if class_id == 37:
            color = (255, 0, 0)  # 赤 (RGB)
            label = f"Ball {score:.2f}"
            thickness = 3
        else:
            color = (0, 255, 0)  # 緑
            label = f"ID:{class_id} {score:.2f}"
            thickness = 2

        # バウンディングボックスを描画
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, thickness)

        # ラベルを描画
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_ymin = max(ymin, label_size[1] + 10)
        cv2.rectangle(frame, (xmin, label_ymin - label_size[1] - 10),
                     (xmin + label_size[0], label_ymin), color, -1)
        cv2.putText(frame, label, (xmin, label_ymin - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return frame


def process_frames(camera):
    """
    フレームを処理し、検出結果を描画してストリーミング
    """
    global fps_counter, fps_start_time, current_fps, avg_inference_time

    logger.info("フレーム処理ループ開始")

    frame_count = 0
    last_detections = []
    inference_times = []

    while True:
        # フレーム取得
        frame = camera.capture_frame()
        if frame is None:
            continue

        # 検出実行（毎フレーム）
        frame_count += 1
        if detection_enabled and detector:
            inference_start = time.time()

            # TFLiteEdgeTPUラッパーで検出（内部でPIL + LANCZOS補間を使用）
            last_detections = detector.detect_objects(frame, threshold=0.5)

            inference_time = (time.time() - inference_start) * 1000
            inference_times.append(inference_time)

            # 統計更新
            update_detection_stats(last_detections)

            # 推論時間の移動平均（最新30フレーム）
            if len(inference_times) > 30:
                inference_times.pop(0)
            avg_inference_time = np.mean(inference_times)

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

        # BGRに変換してJPEGエンコード
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        _, jpeg = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # ストリーミング出力に書き込み
        with output.condition:
            output.frame = jpeg.tobytes()
            output.condition.notify_all()


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 TFLiteEdgeTPUラッパー版 カメラストリーミング")
    print("=" * 70)

    # 検出器初期化（TPU版モデルを使用）
    model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
    logger.info(f"📦 検出モデル読み込み: {model_path}")
    logger.info("⚡ Edge TPU加速を有効化します...")

    detector = TFLiteEdgeTPU(model_path, use_edgetpu=True)
    if not detector.load_model():
        logger.error("❌ モデルの読み込みに失敗しました")
        sys.exit(1)

    logger.info("✅ 検出モデル読み込み完了")
    logger.info(f"   入力サイズ: {detector.get_input_size()}")
    logger.info("   ターゲット: Sports Ball (COCO class 37)")
    logger.info("   リサイズ: PIL + LANCZOS高品質補間")

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

    # バックグラウンドでフレーム処理開始
    processing_thread = Thread(target=process_frames, args=(camera,), daemon=True)
    processing_thread.start()

    try:
        # サーバー起動
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        logger.info("=" * 70)
        logger.info("🌐 ボール検出ストリーミングサーバー起動！")
        logger.info("=" * 70)
        logger.info("ブラウザで以下のURLにアクセスしてください:")
        logger.info("  http://<RaspberryPiのIPアドレス>:8000")
        logger.info("=" * 70)
        logger.info("終了するには Ctrl+C を押してください")
        logger.info("=" * 70)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n🛑 停止中...")
    finally:
        camera.stop()
        camera.cleanup()
        logger.info("✅ カメラストリーミングを終了しました")
