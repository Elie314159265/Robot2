#!/bin/bash
# Download ML Models
# Downloads COCO model and labels for ball detection

echo "==========================================="
echo "Robot PK - Download Models"
echo "==========================================="

# Create models directory
mkdir -p models

cd models

# Download COCO model
echo "Downloading SSD MobileNet v2 COCO model..."
wget -q --show-progress \
    https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite \
    -O ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite

# Download COCO labels
echo "Downloading COCO labels..."
wget -q --show-progress \
    https://github.com/google-coral/test_data/raw/master/coco_labels.txt \
    -O coco_labels.txt

# Verify downloads
echo ""
echo "Downloaded files:"
ls -lh ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite coco_labels.txt

echo ""
echo "Model download complete!"
echo "Models are ready for inference."

cd ..
