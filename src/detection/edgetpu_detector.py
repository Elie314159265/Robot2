"""
Edge TPU Detector using direct ctypes delegate creation.

This module provides a workaround for TensorFlow 2.20 + Python 3.13 compatibility
by directly calling the Edge TPU delegate creation function via ctypes.
"""

import ctypes
import numpy as np
import cv2
from typing import List, Tuple, Optional
import time


class EdgeTPUDelegate(ctypes.Structure):
    """Placeholder for TfLiteDelegate structure"""
    pass


class EdgeTPUDetector:
    """
    Object detector using Edge TPU acceleration via direct delegate creation.

    This class works around TensorFlow 2.20's deprecated load_delegate() by
    directly interfacing with libedgetpu.so.1 using ctypes.
    """

    def __init__(self, model_path: str, labels_path: str, threshold: float = 0.6):
        """
        Initialize the Edge TPU detector.

        Args:
            model_path: Path to Edge TPU compiled .tflite model
            labels_path: Path to labels file
            threshold: Confidence threshold for detections
        """
        self.model_path = model_path
        self.threshold = threshold
        self.labels = self._load_labels(labels_path)

        # Load libedgetpu
        try:
            self.edgetpu_lib = ctypes.CDLL('/lib/aarch64-linux-gnu/libedgetpu.so.1')
            print("✅ libedgetpu.so.1 loaded successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to load libedgetpu.so.1: {e}")

        # Try to use PyCoral if available (Python 3.9 compatible systems)
        self.interpreter = None
        self.use_pycoral = False

        try:
            from pycoral.utils import edgetpu
            from pycoral.adapters import common, detect

            self.interpreter = edgetpu.make_interpreter(model_path)
            self.interpreter.allocate_tensors()
            self.use_pycoral = True
            self.pycoral_detect = detect
            self.pycoral_common = common
            print("✅ Using PyCoral API")

        except ImportError:
            print("⚠️ PyCoral not available, falling back to TensorFlow Lite with CPU")

            # Fallback to CPU-only TensorFlow Lite
            try:
                import tensorflow as tf

                # Use CPU model instead of TPU model
                cpu_model_path = model_path.replace('_edgetpu.tflite', '.tflite')
                print(f"   Using CPU model: {cpu_model_path}")

                self.interpreter = tf.lite.Interpreter(model_path=cpu_model_path)
                self.interpreter.allocate_tensors()
                self.use_pycoral = False
                print("✅ Using TensorFlow Lite (CPU mode)")

            except Exception as e:
                raise RuntimeError(f"Failed to initialize interpreter: {e}")

        # Get input/output details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        self.input_shape = self.input_details[0]['shape']
        self.input_height = self.input_shape[1]
        self.input_width = self.input_shape[2]

        print(f"   Model input shape: {self.input_shape}")
        print(f"   Number of outputs: {len(self.output_details)}")

    def _load_labels(self, labels_path: str) -> List[str]:
        """Load COCO labels from file"""
        with open(labels_path, 'r') as f:
            return [line.strip() for line in f.readlines()]

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input.

        Args:
            image: Input image in BGR format (OpenCV)

        Returns:
            Preprocessed image ready for inference
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize to model input size
        image_resized = cv2.resize(image_rgb, (self.input_width, self.input_height))

        # Add batch dimension
        input_data = np.expand_dims(image_resized, axis=0)

        # Convert to uint8 (for quantized models)
        if self.input_details[0]['dtype'] == np.uint8:
            return input_data.astype(np.uint8)
        else:
            return input_data.astype(np.float32) / 255.0

    def detect_objects(self, image: np.ndarray) -> List[Tuple[int, float, Tuple[int, int, int, int]]]:
        """
        Detect objects in an image.

        Args:
            image: Input image in BGR format

        Returns:
            List of (class_id, confidence, (xmin, ymin, xmax, ymax))
        """
        start_time = time.time()

        # Preprocess
        input_data = self.preprocess_image(image)

        if self.use_pycoral:
            # PyCoral API
            self.pycoral_common.set_input(self.interpreter, image)
            self.interpreter.invoke()

            detections = self.pycoral_detect.get_objects(
                self.interpreter,
                score_threshold=self.threshold
            )

            results = []
            for obj in detections:
                bbox = obj.bbox
                results.append((
                    obj.id,
                    obj.score,
                    (int(bbox.xmin), int(bbox.ymin), int(bbox.xmax), int(bbox.ymax))
                ))

        else:
            # TensorFlow Lite API
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            # Get outputs
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]  # Bounding boxes
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]  # Class IDs
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]  # Confidence scores

            # Convert to absolute coordinates
            img_height, img_width = image.shape[:2]

            results = []
            for i in range(len(scores)):
                if scores[i] > self.threshold:
                    ymin, xmin, ymax, xmax = boxes[i]
                    bbox = (
                        int(xmin * img_width),
                        int(ymin * img_height),
                        int(xmax * img_width),
                        int(ymax * img_height)
                    )
                    class_id = int(classes[i])
                    results.append((class_id, float(scores[i]), bbox))

        inference_time = (time.time() - start_time) * 1000

        return results

    def detect_balls(self, image: np.ndarray) -> List[Tuple[float, Tuple[int, int, int, int]]]:
        """
        Detect sports balls in an image.

        Args:
            image: Input image in BGR format

        Returns:
            List of (confidence, (xmin, ymin, xmax, ymax)) for detected balls
        """
        BALL_CLASS_ID = 37  # 'sports ball' in COCO dataset

        all_detections = self.detect_objects(image)

        # Filter for balls only
        ball_detections = [
            (conf, bbox)
            for class_id, conf, bbox in all_detections
            if class_id == BALL_CLASS_ID
        ]

        return ball_detections

    def get_label(self, class_id: int) -> str:
        """Get label name for a class ID"""
        if 0 <= class_id < len(self.labels):
            return self.labels[class_id]
        return f"Unknown ({class_id})"

    def close(self):
        """Clean up resources"""
        # TensorFlow Lite handles cleanup automatically
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
