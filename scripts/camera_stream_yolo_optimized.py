#!/usr/bin/env python3
"""
最適化版 YOLO形式TPUボール検出 カメラストリーミング
NumPy vectorizationでYOLO後処理を高速化

使い方:
  python3 scripts/camera_stream_yolo_optimized.py
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

# Import CameraController
from src.camera import CameraController

# PyCoral インポート
from pycoral.utils import edgetpu
from pycoral.adapters import common

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
interpreter = None
labels = []
detection_enabled = True
fps_counter = 0
fps_start_time = time.time()
current_fps = 0
total_detections = 0
ball_detections = 0
avg_inference_time = 0


def postprocess_yolo_output_optimized(output_data, input_shape, conf_threshold=0.5, iou_threshold=0.45):
    """
    最適化版YOLO形式の出力を後処理（NumPy vectorization使用）

    Args:
        output_data: モデルの出力テンソル [1, 5, 8400] 形式
        input_shape: 入力画像のサイズ (height, width)
        conf_threshold: 信頼度閾値
        iou_threshold: NMS用のIoU閾値

    Returns:
        検出結果のリスト
    """
    # [1, 5, 8400] -> [8400, 5]
    predictions = output_data[0].transpose()

    h, w = input_shape

    # ベクトル化: 信頼度フィルタリング
    confidences = predictions[:, 4]
    mask = confidences >= conf_threshold

    if not mask.any():
        return []

    # フィルタリング後の予測のみ処理
    filtered_preds = predictions[mask]

    # ベクトル化: バウンディングボックス変換
    x_centers = filtered_preds[:, 0]
    y_centers = filtered_preds[:, 1]
    widths = filtered_preds[:, 2]
    heights = filtered_preds[:, 3]
    scores = filtered_preds[:, 4]

    # 正規化座標に変換
    xmins = (x_centers - widths / 2) / w
    ymins = (y_centers - heights / 2) / h
    xmaxs = (x_centers + widths / 2) / w
    ymaxs = (y_centers + heights / 2) / h

    # クリッピング
    xmins = np.clip(xmins, 0, 1)
    ymins = np.clip(ymins, 0, 1)
    xmaxs = np.clip(xmaxs, 0, 1)
    ymaxs = np.clip(ymaxs, 0, 1)

    # NMS用に実座標に変換
    boxes_for_nms = np.stack([
        xmins * w,
        ymins * h,
        xmaxs * w,
        ymaxs * h
    ], axis=1)

    # NMS
    indices = cv2.dnn.NMSBoxes(
        boxes_for_nms.tolist(),
        scores.tolist(),
        conf_threshold,
        iou_threshold
    )

    detections = []
    if len(indices) > 0:
        for i in indices.flatten():
            detections.append({
                'class': 0,
                'score': float(scores[i]),
                'bbox': [float(xmins[i]), float(ymins[i]), float(xmaxs[i]), float(ymaxs[i])]
            })

    return detections


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
<title>⚽ Optimized YOLO Ball Detection</title>
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
    background: linear-gradient(90deg, #FF6B6B, #FF8E53);
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
.tpu-badge {
    display: inline-block;
    background: linear-gradient(90deg, #FF6B6B, #FF8E53);
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    font-weight: bold;
    margin: 10px 0;
}
.optimized-badge {
    display: inline-block;
    background: linear-gradient(90deg, #00d2ff, #3a7bd5);
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
<h1>⚽ Optimized YOLO Ball Detection</h1>
<div class="subtitle">🚀 NumPy Vectorization最適化版</div>
<div class="tpu-badge">✨ Powered by Google Coral Edge TPU</div>
<div class="optimized-badge">⚡ Performance Optimized</div>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>📷 カメラ:</strong> RaspberryPi Camera Module 3</p>
    <p><strong>🎯 解像度:</strong> 640x480</p>
    <p><strong>🧠 モデル:</strong> Custom YOLO (640x640 TPU)</p>
    <p><strong>⚡ 最適化:</strong> NumPy Vectorization</p>

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
    <div class="legend-item"><span class="box-ball"></span> サッカーボール</div>
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
    ball_detections += len(detections)


def draw_detections(frame, detections):
    """フレームに検出結果を描画"""
    h, w = frame.shape[:2]

    for det in detections:
        bbox = det['bbox']
        score = det['score']

        xmin = int(bbox[0] * w)
        ymin = int(bbox[1] * h)
        xmax = int(bbox[2] * w)
        ymax = int(bbox[3] * h)

        color = (255, 0, 0)
        label = f"Ball {score:.2f}"
        thickness = 3

        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, thickness)

        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        label_ymin = max(ymin, label_size[1] + 10)
        cv2.rectangle(frame, (xmin, label_ymin - label_size[1] - 10),
                     (xmin + label_size[0], label_ymin), color, -1)
        cv2.putText(frame, label, (xmin, label_ymin - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return frame


def process_frames(camera):
    """フレームを処理し、TPUで検出してストリーミング"""
    global fps_counter, fps_start_time, current_fps, avg_inference_time

    logger.info("フレーム処理ループ開始")

    frame_count = 0
    last_detections = []
    inference_times = []

    # 入力情報取得
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]
    input_shape = input_details['shape'][1:3]

    input_scale = input_details['quantization'][0]
    input_zero_point = input_details['quantization'][1]
    output_scale = output_details['quantization'][0]
    output_zero_point = output_details['quantization'][1]

    while True:
        frame = camera.capture_frame()
        if frame is None:
            continue

        frame_count += 1
        if detection_enabled and interpreter:
            inference_start = time.time()

            # リサイズ
            resized = cv2.resize(frame, (input_shape[1], input_shape[0]))

            # 量子化
            input_data = (resized.astype(np.float32) / input_scale + input_zero_point).astype(np.int8)
            input_data = np.expand_dims(input_data, axis=0)

            # TPU推論
            interpreter.set_tensor(input_details['index'], input_data)
            interpreter.invoke()

            # 結果取得と逆量子化
            output_data = interpreter.get_tensor(output_details['index'])
            output_data = (output_data.astype(np.float32) - output_zero_point) * output_scale

            # 最適化版YOLO後処理
            last_detections = postprocess_yolo_output_optimized(
                output_data,
                input_shape=(input_shape[0], input_shape[1]),
                conf_threshold=0.5,
                iou_threshold=0.45
            )

            inference_time = (time.time() - inference_start) * 1000
            inference_times.append(inference_time)

            update_detection_stats(last_detections)

            if len(inference_times) > 30:
                inference_times.pop(0)
            avg_inference_time = np.mean(inference_times)

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

        with output.condition:
            output.frame = jpeg.tobytes()
            output.condition.notify_all()


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 最適化版 YOLO TPU ボール検出")
    print("=" * 70)

    model_path = "models/best_full_integer_quant_edgetpu.tflite"
    labels_path = "models/labels.txt"

    logger.info(f"📦 TPUモデル読み込み: {model_path}")

    try:
        interpreter = edgetpu.make_interpreter(model_path)
        interpreter.allocate_tensors()
        logger.info("✅ Edge TPU モデル読み込み完了")
    except Exception as e:
        logger.error(f"❌ TPUモデルの読み込み失敗: {e}")
        sys.exit(1)

    if os.path.exists(labels_path):
        with open(labels_path, 'r') as f:
            labels = [line.strip() for line in f.readlines()]
        logger.info(f"✅ {len(labels)} ラベル読み込み完了")
    else:
        labels = ["ball"]

    logger.info("📷 カメラを初期化中...")
    camera = CameraController(resolution=(640, 480), framerate=30, debug=False)

    if not camera.initialize():
        logger.error("❌ カメラの初期化に失敗")
        sys.exit(1)

    if not camera.start():
        logger.error("❌ カメラの起動に失敗")
        camera.cleanup()
        sys.exit(1)

    time.sleep(2)
    logger.info("✅ カメラ初期化完了")

    processing_thread = Thread(target=process_frames, args=(camera,), daemon=True)
    processing_thread.start()

    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        logger.info("=" * 70)
        logger.info("🌐 最適化版 YOLO TPU ボール検出ストリーミングサーバー起動！")
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
