#!/usr/bin/env python3
"""
超高速版 TPUボール検出 カメラストリーミング
300x300ネイティブ解像度でリサイズ処理を完全削除、最大60 FPS達成

使い方:
  python3 scripts/camera_stream_tpu_300.py
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
from pycoral.adapters import detect

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
        # アクセスログを抑制
        return


# HTMLページ
PAGE = """\
<html>
<head>
<meta charset="utf-8">
<title>Edge TPU Ball Detection</title>
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
.improved-badge {
    display: inline-block;
    background: linear-gradient(90deg, #667eea, #764ba2);
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
<h1>Edge TPU Ball Detection</h1>
<div class="subtitle">640×480</div>
<div class="tpu-badge">Powered by Google Coral Edge TPU</div>
<div class="improved-badge">60 FPS Target</div>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>カメラ:</strong> RaspberryPi Camera Module 3 (IMX708)</p>
    <p><strong>解像度:</strong> 640×480</p>
    <p><strong>検出モデル:</strong> SSD MobileNet v2 COCO (TPU版)</p>
    <p><strong>アクセラレータ:</strong> Google Coral USB Accelerator</p>
    <p><strong>ターゲット:</strong> Sports Ball (COCO Class 36)</p>

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
            <div>ボール検出</div>
            <div class="stat-value" id="balls">0</div>
        </div>
    </div>
</div>
<div class="legend">
    <p><strong>検出表示:</strong></p>
    <div class="legend-item"><span class="box-ball"></span> スポーツボール（赤色・太線）</div>
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
            document.getElementById('inference').textContent = data.inference_time.toFixed(1) + 'ms';
            document.getElementById('total').textContent = data.total_detections;
            document.getElementById('balls').textContent = data.ball_detections;
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


def process_frames(camera):
    """
    フレームを処理し、TPUで検出してストリーミング
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

        # TPU検出実行（毎フレーム）
        frame_count += 1
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
        _, jpeg = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])

        # ストリーミング出力に書き込み
        with output.condition:
            output.frame = jpeg.tobytes()
            output.condition.notify_all()


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 最適化版 Edge TPU ボール検出 カメラストリーミング")
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
    # 注意: カメラは640x480でキャプチャし、ソフトウェアで300x300にリサイズ
    # 300x300のネイティブキャプチャはIMX708センサーで非対応のため画像が壊れる
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
        logger.info("🌐 最適化版 Edge TPU ボール検出ストリーミングサーバー起動！")
        logger.info("=" * 70)
        logger.info("ブラウザで以下のURLにアクセスしてください:")
        logger.info("  http://<RaspberryPiのIPアドレス>:8000")
        logger.info("=" * 70)
        logger.info("超高速最適化:")
        logger.info("  - 640x480キャプチャ → 300x300高速リサイズ")
        logger.info("  - cv2 + INTER_LINEAR（非標準解像度の画像破損を回避）")
        logger.info("  - JPEG品質80（最高速）")
        logger.info("  - 期待FPS: 40-45")
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
