"""
PK Serial Controller - PK課題専用のArduinoシリアル通信

arduino/pk_controller/pk_controller.inoと通信するためのコントローラー
walk_program_refactored_20260109.inoのPWM値に準拠
"""

from typing import Optional
import serial
import logging
import time

logger = logging.getLogger(__name__)


# PWM値定義（walk_program_refactored_20260109.ino準拠）
class PKServoConfig:
    """PK用サーボ設定"""
    # サーボチャンネル
    FL_HIP = 0
    FL_KNEE = 1
    FR_HIP = 2
    FR_KNEE = 3
    BL_HIP = 8
    BL_KNEE = 5
    BR_HIP = 6
    BR_KNEE = 7

    # 左前脚 (FL)
    FL_KNEE_DOWN = 300    # ch1: デフォルト300

    # 右前脚 (FR)
    FR_KNEE_DOWN = 150    # ch3: デフォルト150

    # 左後脚 (BL) - ボールブロック用
    BL_KNEE_UP = 150
    BL_KNEE_DOWN = 400    # ch5: デフォルト400

    # 右後脚 (BR) - ボールブロック用
    BR_KNEE_UP = 380
    BR_KNEE_DOWN = 150    # ch7: デフォルト150


class PKSerialController:
    """
    PK課題専用のシリアル通信コントローラー

    arduino/pk_controller/pk_controller.inoと通信
    """

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 9600,
        timeout: float = 1.0
    ):
        """
        初期化

        Args:
            port: シリアルポート
            baudrate: ボーレート
            timeout: タイムアウト（秒）
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.is_connected = False
        self.config = PKServoConfig()

    def connect(self) -> bool:
        """
        Arduinoに接続

        Returns:
            成功時True
        """
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Arduinoリセット待機

            # バッファクリア
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # 起動メッセージ読み捨て
            if self.serial.in_waiting > 0:
                startup_msg = self.serial.readline().decode().strip()
                logger.debug(f"Arduino startup: {startup_msg}")

            self.is_connected = True
            logger.info(f"PK Controller connected on {self.port}")
            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """切断"""
        if self.serial:
            self.serial.close()
            self.is_connected = False
            logger.info("PK Controller disconnected")

    def initialize_legs(self) -> bool:
        """
        全脚を初期位置に設定

        Returns:
            成功時True
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        try:
            self.serial.write(b"I\n")
            response = self.serial.readline().decode().strip()
            return response == "OK"
        except Exception as e:
            logger.error(f"Initialize failed: {e}")
            return False

    def read_distance(self, side: str = "L") -> Optional[float]:
        """
        超音波距離センサー読み取り

        Args:
            side: 'L'（左）または 'R'（右）

        Returns:
            距離（cm）、エラー時None
        """
        if not self.is_connected:
            logger.error("Not connected")
            return None

        if side not in ["L", "R"]:
            logger.error(f"Invalid side: {side}")
            return None

        try:
            command = f"D{side}\n"
            self.serial.write(command.encode())

            response = self.serial.readline().decode().strip()

            if response.startswith("D") and len(response) == 6:
                distance_mm = int(response[1:])
                distance_cm = distance_mm / 10.0
                logger.debug(f"Distance ({side}): {distance_cm:.1f} cm")
                return distance_cm
            else:
                logger.error(f"Invalid response: {response}")
                return None

        except Exception as e:
            logger.error(f"Read distance failed: {e}")
            return None

    def block_ball_left(self) -> bool:
        """
        ボールブロック（左側）

        ボールが画面左側に現れた場合、右後脚(BR ch7) + 右前脚(FR ch3)を上げてブロック
        BR ch7: 150 (DOWN) → 380 (UP) → 150 (DOWN)
        FR ch3: 150 (DOWN) → 380 (UP) → 150 (DOWN)

        Returns:
            成功時True
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        try:
            self.serial.write(b"BL\n")
            # 5秒間ブロック動作があるため、タイムアウトを長めに
            self.serial.timeout = 10.0
            response = self.serial.readline().decode().strip()
            self.serial.timeout = self.timeout

            if response == "OK":
                logger.info(f"Ball blocked LEFT (BR ch7 + FR ch3)")
                return True
            else:
                logger.error(f"Block left failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Block left failed: {e}")
            return False

    def block_ball_right(self) -> bool:
        """
        ボールブロック（右側）

        ボールが画面右側に現れた場合、左後脚(BL ch5) + 左前脚(FL ch1)を上げてブロック
        BL ch5: 400 (DOWN) → 150 (UP) → 400 (DOWN)
        FL ch1: 300 (DOWN) → 100 (UP) → 300 (DOWN)

        Returns:
            成功時True
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        try:
            self.serial.write(b"BR\n")
            # 5秒間ブロック動作があるため、タイムアウトを長めに
            self.serial.timeout = 10.0
            response = self.serial.readline().decode().strip()
            self.serial.timeout = self.timeout

            if response == "OK":
                logger.info(f"Ball blocked RIGHT (BL ch5 + FL ch1)")
                return True
            else:
                logger.error(f"Block right failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Block right failed: {e}")
            return False

    def set_servo_pwm(self, servo_id: int, pwm_value: int) -> bool:
        """
        サーボPWM値を直接設定

        Args:
            servo_id: サーボID (0-15)
            pwm_value: PWM値 (100-600)

        Returns:
            成功時True
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        if servo_id < 0 or servo_id > 15:
            logger.error(f"Invalid servo ID: {servo_id}")
            return False

        if pwm_value < 100 or pwm_value > 600:
            logger.error(f"Invalid PWM value: {pwm_value}")
            return False

        try:
            command = f"S{servo_id:02d}{pwm_value:03d}\n"
            self.serial.write(command.encode())

            response = self.serial.readline().decode().strip()

            if response == "OK":
                logger.debug(f"Servo {servo_id} set to PWM {pwm_value}")
                return True
            else:
                logger.error(f"Set servo failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Set servo failed: {e}")
            return False

    def cleanup(self) -> None:
        """クリーンアップ"""
        self.disconnect()

    def __enter__(self):
        """コンテキストマネージャー開始"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了"""
        self.cleanup()
