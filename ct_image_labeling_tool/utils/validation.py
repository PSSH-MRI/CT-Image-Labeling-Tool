import os
import json
import base64
import numpy as np
import cv2

def validate_annotation_masks(json_path):
    if not os.path.exists(json_path):
        print(f"[ERROR] File not found: {json_path}")
        return

    with open(json_path, "r") as file:
        data = json.load(file)

    annotations = data.get("annotations", [])
    failed = 0
    total = len(annotations)

    for ann in annotations:
        try:
            shape = ann.get("shape")
            color = ann.get("color", [255, 255, 255])
            orig_size = ann.get("orig_size", [512, 512])
            mask_data = base64.b64decode(ann.get("mask", ""))
            mask = cv2.imdecode(np.frombuffer(mask_data, np.uint8), cv2.IMREAD_GRAYSCALE)

            if mask is None:
                print(f"[WARNING] Failed to decode mask for: {ann.get('name')}")
                failed += 1
        except Exception as e:
            print(f"[ERROR] Failed to validate annotation: {e}")
            failed += 1

    print(f"Validation complete: {total - failed} passed, {failed} failed")