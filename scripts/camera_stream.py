#!/usr/bin/env python3
"""
カメラストリーミングサーバー
ブラウザでリアルタイム映像を確認できます

使い方:
  python3 scripts/camera_stream.py
  ブラウザで http://<RaspberryPiのIPアドレス>:8000 にアクセス
"""

import io
import time
import logging
from threading import Condition
from http.server import BaseHTTPRequestHandler, HTTPServer
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

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
<title>Raspberry Pi Camera Stream</title>
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
img {
    max-width: 100%;
    border: 2px solid #4CAF50;
    border-radius: 8px;
}
.info {
    margin-top: 20px;
    padding: 10px;
    background-color: #2a2a2a;
    border-radius: 5px;
    display: inline-block;
}
</style>
</head>
<body>
<h1>RaspberryPi Camera Module3</h1>
<img src="stream.mjpg" />
<div class="info">
    <p><strong>解像度:</strong> 640x480</p>
    <p><strong>フォーマット:</strong> MJPEG</p>
    <p><strong>センサー:</strong> IMX708 (Camera Module 3)</p>
</div>
</body>
</html>
"""


class StreamingServer(HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    # カメラ初期化
    logger.info("カメラを初期化中...")
    picam2 = Picamera2()

    # ビデオ設定
    video_config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(video_config)

    # ストリーミング出力
    output = StreamingOutput()
    encoder = JpegEncoder(q=85)

    # カメラ開始
    logger.info("カメラストリーミングを開始...")
    picam2.start_recording(encoder, FileOutput(output))

    try:
        # サーバー起動
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        logger.info("=" * 60)
        logger.info("カメラストリーミングサーバー起動！")
        logger.info("=" * 60)
        logger.info("ブラウザで以下のURLにアクセスしてください:")
        logger.info("  http://<RaspberryPiのIPアドレス>:8000")
        logger.info("  または")
        logger.info("  http://localhost:8000 (ローカルの場合)")
        logger.info("=" * 60)
        logger.info("終了するには Ctrl+C を押してください")
        logger.info("=" * 60)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n停止中...")
    finally:
        picam2.stop_recording()
        picam2.close()
        logger.info("カメラストリーミングを終了しました")
