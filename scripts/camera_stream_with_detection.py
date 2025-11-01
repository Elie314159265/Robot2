#!/usr/bin/env python3
"""
カメラストリーミング + ボール検出
リアルタイムでボールを検出し、バウンディングボックスを表示

使い方:
  python3 scripts/camera_stream_with_detection.py
  ブラウザで http://<RaspberryPiのIPアドレス>:8000 にアクセス
"""

import io
import sys
import os
import time
import logging
from threading import Condition
from http.server import BaseHTTPRequestHandler, HTTPServer
from picamera2 import Picamera2
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
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
            # 統計情報をJSON形式で返す
            stats = {
                'fps': current_fps,
                'total_detections': total_detections,
                'ball_detections': ball_detections
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
<title>Ball Detection - Camera Stream</title>
<style>
body {
    margin: 0;
    padding: 20px;
    background-color: #1a1a1a;
    color: #ffffff;
    font-family: Arial, sans-serif;
    text-align: center;
}
h1 {
    color: #4CAF50;
}
.container {
    max-width: 800px;
    margin: 0 auto;
}
img {
    max-width: 100%;
    border: 2px solid #4CAF50;
    border-radius: 8px;
}
.info {
    margin-top: 20px;
    padding: 15px;
    background-color: #2a2a2a;
    border-radius: 5px;
    display: inline-block;
    text-align: left;
}
.stats {
    margin-top: 10px;
    padding: 10px;
    background-color: #333;
    border-radius: 5px;
}
.ball-detected {
    color: #FFD700;
    font-weight: bold;
    font-size: 1.2em;
}
.legend {
    margin-top: 15px;
    padding: 10px;
    background-color: #2a2a2a;
    border-radius: 5px;
    text-align: left;
}
.legend-item {
    margin: 5px 0;
}
.box-ball {
    display: inline-block;
    width: 20px;
    height: 20px;
    background-color: rgba(255, 0, 0, 0.8);
    border: 2px solid red;
    margin-right: 5px;
}
.box-other {
    display: inline-block;
    width: 20px;
    height: 20px;
    background-color: rgba(0, 255, 0, 0.3);
    border: 2px solid lime;
    margin-right: 5px;
}
</style>
</head>
<body>
<div class="container">
<h1>⚽ Ball Detection - Live Camera</h1>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>解像度:</strong> 640x480</p>
    <p><strong>フォーマット:</strong> MJPEG</p>
    <p><strong>検出モデル:</strong> SSD MobileNet v2 COCO</p>
    <p><strong>ターゲット:</strong> Sports Ball (Class 37)</p>
    <div class="stats">
        <p>FPS: <span id="fps">--</span></p>
        <p>総検出数: <span id="total">0</span></p>
        <p class="ball-detected">⚽ ボール検出: <span id="balls">0</span></p>
    </div>
</div>
<div class="legend">
    <p><strong>凡例:</strong></p>
    <div class="legend-item"><span class="box-ball"></span> スポーツボール（赤色）</div>
    <div class="legend-item"><span class="box-other"></span> その他のオブジェクト（緑色）</div>
</div>
</div>

<script>
// 統計情報を定期的に更新
setInterval(function() {
    fetch('/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('fps').textContent = data.fps.toFixed(1);
            document.getElementById('total').textContent = data.total_detections;
            document.getElementById('balls').textContent = data.ball_detections;
        })
        .catch(err => console.error('Stats update failed:', err));
}, 1000);
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
        if det['class_id'] == 37:
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


def process_frames(picam2):
    """
    フレームを処理し、検出結果を描画してストリーミング
    """
    global fps_counter, fps_start_time, current_fps

    logger.info("フレーム処理ループ開始")

    frame_count = 0
    last_detections = []

    while True:
        # フレーム取得
        frame = picam2.capture_array()

        # 検出実行（3フレームに1回で高速化）
        frame_count += 1
        if detection_enabled and detector and frame_count % 3 == 0:
            last_detections = detector.detect_objects(frame, threshold=0.6)
            # 統計更新
            update_detection_stats(last_detections)

        # 最後の検出結果を描画
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

        # BGRに変換してJPEGエンコード
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        _, jpeg = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])

        # ストリーミング出力に書き込み
        with output.condition:
            output.frame = jpeg.tobytes()
            output.condition.notify_all()


if __name__ == '__main__':
    print("=" * 60)
    print("カメラストリーミング + ボール検出サーバー")
    print("=" * 60)

    # 検出器初期化（TPU版モデルを使用）
    model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
    logger.info(f"検出モデル読み込み: {model_path}")
    logger.info("Edge TPU加速を有効化します...")

    detector = TFLiteEdgeTPU(model_path, use_edgetpu=True)
    if not detector.load_model():
        logger.error("モデルの読み込みに失敗しました")
        sys.exit(1)

    logger.info("✅ 検出モデル読み込み完了")
    logger.info(f"   入力サイズ: {detector.get_input_size()}")
    logger.info("   ターゲット: Sports Ball (COCO class 37)")

    # カメラ初期化
    logger.info("カメラを初期化中...")
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)  # カメラウォームアップ

    logger.info("✅ カメラ初期化完了")

    # バックグラウンドでフレーム処理開始
    import threading
    processing_thread = threading.Thread(target=process_frames, args=(picam2,), daemon=True)
    processing_thread.start()

    try:
        # サーバー起動
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        logger.info("=" * 60)
        logger.info("ボール検出ストリーミングサーバー起動！")
        logger.info("=" * 60)
        logger.info("ブラウザで以下のURLにアクセスしてください:")
        logger.info("  http://192.168.0.11:8000")
        logger.info("=" * 60)
        logger.info("終了するには Ctrl+C を押してください")
        logger.info("=" * 60)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n停止中...")
    finally:
        picam2.stop()
        picam2.close()
        logger.info("カメラストリーミングを終了しました")
