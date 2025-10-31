"""
Configuration management module
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class Config:
    """Configuration manager for robot system"""

    # Default configuration
    DEFAULTS = {
        "camera": {
            "resolution": [640, 480],
            "framerate": 30,
            "sensor_mode": 0,
        },
        "detection": {
            "model_path": "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite",
            "labels_path": "models/coco_labels.txt",
            "confidence_threshold": 0.5,
        },
        "tracking": {
            "pid_kp": 0.5,
            "pid_ki": 0.1,
            "pid_kd": 0.2,
            "servo_min_angle": -90,
            "servo_max_angle": 90,
        },
        "arduino": {
            "port": "/dev/ttyACM0",
            "baudrate": 9600,
            "timeout": 1.0,
        },
        "positioning": {
            "servo_range": 180,
            "distance_min": 10,
            "distance_max": 300,
        },
        "system": {
            "target_fps": 30,
            "inference_timeout": 20,
            "debug": False,
        }
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to YAML config file (optional)
        """
        self.config = self.DEFAULTS.copy()

        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)

    def load_from_file(self, config_file: str) -> None:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    self._deep_update(self.config, yaml_config)
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "camera.resolution")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.

        Args:
            key: Configuration key
            value: Value to set
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @staticmethod
    def _deep_update(base_dict: Dict, update_dict: Dict) -> None:
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                Config._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def to_dict(self) -> Dict:
        """Get configuration as dictionary"""
        return self.config.copy()
