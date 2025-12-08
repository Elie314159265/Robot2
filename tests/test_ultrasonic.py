#!/usr/bin/env python3
"""
超音波センサ高速データ取得テストプログラム（最適化版）
RaspberryPiからArduino経由で超音波センサの値を高速取得

最適化ポイント:
- リアルタイム測定頻度計測（実測Hz表示）
- データロス検出（シーケンス番号チェック）
- 統計情報のリアルタイム更新
- CSVファイル保存オプション
"""

import sys
import time
import serial
import serial.tools.list_ports
from collections import deque
from datetime import datetime

def find_arduino_port():
    """Arduinoのシリアルポートを自動検出"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Arduino Uno は通常 ACM0 として認識される
        if 'ACM' in port.device or 'USB' in port.device:
            return port.device
    return None

class UltrasonicDataLogger:
    """超音波センサデータの高速ロギングクラス"""

    def __init__(self, save_to_file=False):
        self.save_to_file = save_to_file
        self.file_handle = None
        self.distances = []
        self.timestamps = []
        self.valid_count = 0
        self.error_count = 0
        self.last_sequence = None
        self.lost_packets = 0
        self.measurement_times = deque(maxlen=10)  # 最新10測定のタイムスタンプ

    def start_logging(self):
        """ログファイルを開始"""
        if self.save_to_file:
            filename = f"ultrasonic_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.file_handle = open(filename, 'w')
            self.file_handle.write("timestamp,distance_cm,arduino_time_ms,sequence\n")
            print(f"Logging to file: {filename}")

    def stop_logging(self):
        """ログファイルを閉じる"""
        if self.file_handle:
            self.file_handle.close()
            print(f"Log file saved")

    def parse_data(self, line):
        """
        データをパース（新フォーマット対応）
        Format: D:<distance>,T:<time>,N:<seq>
        """
        try:
            parts = line.split(',')
            data = {}
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    data[key] = value

            if 'D' in data:
                distance = float(data['D'])
                arduino_time = int(data.get('T', 0))
                sequence = int(data.get('N', 0))

                return distance, arduino_time, sequence
        except (ValueError, IndexError):
            pass

        return None, None, None

    def log_measurement(self, distance, arduino_time, sequence):
        """測定データを記録"""
        current_time = time.time()
        self.measurement_times.append(current_time)

        # シーケンス番号チェック（データロス検出）
        if self.last_sequence is not None and sequence != self.last_sequence + 1:
            lost = sequence - self.last_sequence - 1
            self.lost_packets += lost
            print(f"  WARNING: Lost {lost} packet(s) (seq {self.last_sequence+1} to {sequence-1})")

        self.last_sequence = sequence

        # 有効データチェック
        if distance > 0 and 2.0 <= distance <= 400.0:
            self.valid_count += 1
            self.distances.append(distance)
            self.timestamps.append(current_time)

            # ファイルに保存
            if self.file_handle:
                self.file_handle.write(f"{current_time:.3f},{distance:.2f},{arduino_time},{sequence}\n")
        else:
            self.error_count += 1

    def get_measurement_rate(self):
        """実測の測定頻度を計算（Hz）"""
        if len(self.measurement_times) < 2:
            return 0.0

        time_diff = self.measurement_times[-1] - self.measurement_times[0]
        if time_diff == 0:
            return 0.0

        return (len(self.measurement_times) - 1) / time_diff

    def print_statistics(self):
        """統計情報を表示"""
        print("\n" + "="*60)
        print("Test Summary:")
        print(f"Valid readings:    {self.valid_count}")
        print(f"Error readings:    {self.error_count}")
        print(f"Lost packets:      {self.lost_packets}")
        print(f"Success rate:      {self.valid_count/(self.valid_count+self.error_count)*100:.1f}%")

        if self.distances:
            print(f"\nDistance Statistics:")
            print(f"  Min:  {min(self.distances):.2f} cm")
            print(f"  Max:  {max(self.distances):.2f} cm")
            print(f"  Avg:  {sum(self.distances)/len(self.distances):.2f} cm")
            print(f"  StdDev: {self._calc_stddev():.2f} cm")

        rate = self.get_measurement_rate()
        if rate > 0:
            print(f"\nMeasurement Rate:  {rate:.2f} Hz")

    def _calc_stddev(self):
        """標準偏差を計算"""
        if len(self.distances) < 2:
            return 0.0
        mean = sum(self.distances) / len(self.distances)
        variance = sum((x - mean) ** 2 for x in self.distances) / len(self.distances)
        return variance ** 0.5


def test_ultrasonic_sensor(port='/dev/ttyACM0', baudrate=115200, duration=30, save_to_file=False):
    """
    超音波センサの高速テスト

    Args:
        port: シリアルポート
        baudrate: ボーレート
        duration: テスト時間（秒）
        save_to_file: CSVファイルに保存するか
    """
    print("=== High-Speed Ultrasonic Sensor Test ===")
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Test duration: {duration} seconds")
    print(f"Save to file: {save_to_file}")
    print()

    logger = UltrasonicDataLogger(save_to_file=save_to_file)

    try:
        # シリアルポート接続
        ser = serial.Serial(port, baudrate, timeout=0.1)
        time.sleep(2)  # Arduino起動待ち

        # 初期メッセージをスキップ
        print("Waiting for Arduino initialization...")
        for _ in range(10):
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"  {line}")

        print("\nReading sensor data...")
        print("(Press Ctrl+C to stop)")
        print()

        logger.start_logging()
        start_time = time.time()
        last_display_time = start_time

        while (time.time() - start_time) < duration:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()

                    # データ行のみ処理
                    if line.startswith("D:"):
                        distance, arduino_time, sequence = logger.parse_data(line)

                        if distance is not None:
                            logger.log_measurement(distance, arduino_time, sequence)

                            # リアルタイム表示（1秒ごと）
                            current_time = time.time()
                            if current_time - last_display_time >= 1.0:
                                rate = logger.get_measurement_rate()
                                print(f"[{logger.valid_count:4d}] Distance: {distance:6.2f} cm | "
                                      f"Rate: {rate:5.2f} Hz | "
                                      f"Errors: {logger.error_count} | "
                                      f"Lost: {logger.lost_packets}")
                                last_display_time = current_time

                except UnicodeDecodeError:
                    pass

        logger.stop_logging()
        logger.print_statistics()
        ser.close()

    except serial.SerialException as e:
        print(f"Error: Could not open serial port {port}")
        print(f"Details: {e}")
        print("\nAvailable ports:")
        for port in serial.tools.list_ports.comports():
            print(f"  - {port.device}: {port.description}")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        logger.stop_logging()
        logger.print_statistics()
        if 'ser' in locals() and ser.is_open:
            ser.close()
        sys.exit(0)


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description='High-speed ultrasonic sensor test')
    parser.add_argument('--port', type=str, help='Serial port (auto-detect if not specified)')
    parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds (default: 30)')
    parser.add_argument('--save', action='store_true', help='Save data to CSV file')

    args = parser.parse_args()

    # Arduinoポートを自動検出または指定
    port = args.port if args.port else find_arduino_port()

    if port is None:
        print("Error: Arduino not found")
        print("\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  - {p.device}: {p.description}")
        sys.exit(1)

    print(f"Found Arduino at: {port}")
    print()

    # テスト実行
    test_ultrasonic_sensor(port=port, duration=args.duration, save_to_file=args.save)


if __name__ == "__main__":
    main()
