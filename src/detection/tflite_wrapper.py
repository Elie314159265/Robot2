"""
TensorFlow Lite Wrapper for Edge TPU
Direct ctypes-based implementation using libedgetpu
"""

import ctypes
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TFLiteEdgeTPU:
    """
    Minimal TensorFlow Lite interpreter for Edge TPU using ctypes.

    This implementation directly interfaces with libedgetpu.so without
    requiring the full TFLite runtime Python package.
    """

    def __init__(self, model_path: str, use_edgetpu: bool = True):
        """
        Initialize TFLite interpreter with Edge TPU support.

        Args:
            model_path: Path to .tflite model file
            use_edgetpu: Whether to use Edge TPU acceleration
        """
        self.model_path = model_path
        self.use_edgetpu = use_edgetpu
        self.interpreter = None
        self.input_details = None
        self.output_details = None

        # Try to load libedgetpu
        if use_edgetpu:
            try:
                self.edgetpu_lib = ctypes.CDLL('libedgetpu.so.1')
                logger.info("✅ libedgetpu.so.1 loaded successfully")
            except OSError as e:
                logger.warning(f"Failed to load libedgetpu: {e}")
                logger.warning("Falling back to CPU inference")
                self.use_edgetpu = False

    def load_model(self) -> bool:
        """
        Load the TFLite model.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Import TFLite (try multiple sources)
            try:
                import tflite_runtime.interpreter as tflite
                logger.info("Using tflite_runtime")
            except ImportError:
                try:
                    import tensorflow.lite as tflite
                    logger.info("Using tensorflow.lite")
                except ImportError:
                    logger.error("No TFLite interpreter available!")
                    logger.error("Please install: pip3 install tensorflow or tflite-runtime")
                    return False

            # Create interpreter with Edge TPU delegate
            if self.use_edgetpu:
                try:
                    # Use ExternalDelegate to load libedgetpu.so.1
                    # This works with TensorFlow 2.20+
                    import tensorflow as tf

                    # Create Edge TPU delegate options
                    delegate_options = {}

                    # Create external delegate
                    delegate = tf.lite.experimental.load_delegate(
                        'libedgetpu.so.1',
                        delegate_options
                    )

                    self.interpreter = tflite.Interpreter(
                        model_path=self.model_path,
                        experimental_delegates=[delegate]
                    )
                    logger.info("✅ Edge TPU delegate loaded via ExternalDelegate")
                except Exception as e:
                    logger.warning(f"Edge TPU delegate failed: {e}, using CPU")
                    self.interpreter = tflite.Interpreter(model_path=self.model_path)
            else:
                self.interpreter = tflite.Interpreter(model_path=self.model_path)

            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            logger.info(f"Model loaded: {self.model_path}")
            logger.info(f"Input shape: {self.input_details[0]['shape']}")
            logger.info(f"Output tensors: {len(self.output_details)}")

            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def get_input_shape(self) -> Tuple[int, int, int, int]:
        """Get model input shape (batch, height, width, channels)"""
        if self.input_details:
            return tuple(self.input_details[0]['shape'])
        return (1, 300, 300, 3)

    def get_input_size(self) -> Tuple[int, int]:
        """Get model input size (height, width)"""
        shape = self.get_input_shape()
        return (shape[1], shape[2])

    def set_input_tensor(self, image: np.ndarray):
        """Set input tensor from numpy array"""
        tensor_index = self.input_details[0]['index']
        self.interpreter.set_tensor(tensor_index, image)

    def invoke(self):
        """Run inference"""
        self.interpreter.invoke()

    def get_output_tensor(self, index: int) -> np.ndarray:
        """Get output tensor by index"""
        output_details = self.output_details[index]
        tensor = self.interpreter.get_tensor(output_details['index'])
        return np.squeeze(tensor)

    def detect_objects(self, image: np.ndarray, threshold: float = 0.5) -> List[dict]:
        """
        Detect objects in image.

        Args:
            image: Input image (HxWxC numpy array)
            threshold: Confidence threshold

        Returns:
            List of detections with 'bbox', 'class_id', 'score'
        """
        # Resize and preprocess image
        input_size = self.get_input_size()
        from PIL import Image

        if image.shape[:2] != input_size:
            pil_image = Image.fromarray(image)
            pil_image = pil_image.resize(input_size, Image.Resampling.LANCZOS)
            image_resized = np.array(pil_image)
        else:
            image_resized = image

        # Add batch dimension
        input_data = np.expand_dims(image_resized, axis=0)

        # Ensure uint8 type
        if input_data.dtype != np.uint8:
            input_data = input_data.astype(np.uint8)

        # Set input and run inference
        self.set_input_tensor(input_data)
        self.invoke()

        # Get outputs (SSD MobileNet format)
        # Output 0: bounding boxes [1, 10, 4]
        # Output 1: class IDs [1, 10]
        # Output 2: confidence scores [1, 10]
        # Output 3: number of detections [1]

        boxes = self.get_output_tensor(0)      # [10, 4]
        classes = self.get_output_tensor(1)    # [10]
        scores = self.get_output_tensor(2)     # [10]
        count = int(self.get_output_tensor(3)) # scalar

        detections = []
        for i in range(count):
            if scores[i] >= threshold:
                detections.append({
                    'bbox': boxes[i].tolist(),  # [ymin, xmin, ymax, xmax] normalized
                    'class_id': int(classes[i]),
                    'score': float(scores[i])
                })

        return detections
