"""
download_model.py
Run this ONCE (with internet access) before using the pipeline.
Downloads MediaPipe's FaceLandmarker model (~5-10MB) needed by
modules/face_utils.py.
"""

import os
import urllib.request

MODELS = {
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/face_landmarker.task"
    ),
    "blaze_face_short_range.tflite": (
        "https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
    ),
    "efficientdet_lite0.tflite": (
        "https://storage.googleapis.com/mediapipe-models/object_detector/"
        "efficientdet_lite0/float16/1/efficientdet_lite0.tflite"
    ),
}
MODEL_DIR = "models"


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    for model_name, url in MODELS.items():
        path = os.path.join(MODEL_DIR, model_name)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"Model already exists at {path}, skipping download.")
            continue
        print(f"Downloading {model_name} from {url} ...")
        urllib.request.urlretrieve(url, path)
        print(f"Done. Saved to {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
