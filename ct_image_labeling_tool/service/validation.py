import cv2
import json
import numpy as np
import os
import pydicom
from tkinter import Tk, filedialog
import base64

def load_dicom_or_image(file_path):
    """
    Load DICOM or standard image file.
    """
    if file_path.endswith(".dcm"):
        ds = pydicom.dcmread(file_path)
        img = ds.pixel_array
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        print(f"Loaded DICOM file: {file_path}")
        print(f"DICOM Image Size: {img.shape[:2]}")
    else:
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        print(f"Loaded Image file: {file_path}")
        print(f"Image Size: {img.shape[:2]}")
    return img

def resize_image(image, window_width, window_height):
    """
    Resize image to fit within the specified window size while maintaining aspect ratio.
    """
    img_height, img_width = image.shape[:2]
    aspect_ratio = img_width / img_height

    if img_width > window_width or img_height > window_height:
        if window_width / window_height > aspect_ratio:
            # Fit to window height
            new_height = window_height
            new_width = int(window_height * aspect_ratio)
        else:
            # Fit to window width
            new_width = window_width
            new_height = int(window_width / aspect_ratio)
        return cv2.resize(image, (new_width, new_height))
    else:
        # If the image is smaller than the window, keep original size
        return image

def validate_json_annotations(json_path):
    """
    Validate JSON annotations by displaying them on the corresponding DICOM/image file.
    """
    # Load JSON file
    with open(json_path, "r") as json_file:
        data = json.load(json_file)

    annotations = data.get("annotations", [])
    base_dir = os.path.dirname(json_path)
    file_list = data.get("file_path", [])
    if not file_list:
        print("No file_path found in JSON.")
        return
    image_path = os.path.join(base_dir, file_list[0])

    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return

    # Load the original image
    original_image = load_dicom_or_image(image_path)
    print(f"Original Image Size: {original_image.shape[:2]}")

    # Debug: Print annotation details
    print(f"Annotations count: {len(annotations)}")
    for i, annotation in enumerate(annotations):
        print(f"\nAnnotation {i + 1}:")
        print(f"  Name: {annotation['name']}")
        print(f"  Shape: {annotation['shape']}")
        if annotation['shape'] == 'ellipse':
            if 'center' in annotation:
                print(f"  Center: {annotation['center']}")
                print(f"  Axes: {annotation['axes']}")
                print(f"  Angle: {annotation['angle']}")
            else:
                print(f"  Points: {annotation['points']}")
        else:
            print(f"  Points: {annotation['points']}")
        print(f"  Color: {annotation['color']}")
        if 'mask' in annotation:
            print(f"  Mask: Exists")
        else:
            print(f"  Mask: Not available")

    # Create a resizable window
    window_name = "Validation: Annotated Image with Masks"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1200, 1200)

    annotated_image = original_image.copy()
    for annotation in annotations:
        shape = annotation["shape"]
        color = tuple(annotation["color"])
        if shape == "closed_curve":
            # Draw closed_curve annotation using points
            points = annotation["points"]
            cv2.polylines(annotated_image, [np.array(points, dtype=np.int32)], isClosed=True, color=color, thickness=1)
        elif shape == "ellipse":
            # For ellipse, check if new structure exists (center, axes, angle)
            if "center" in annotation and "axes" in annotation and "angle" in annotation:
                center = tuple(map(int, annotation["center"]))
                axes = tuple(map(int, annotation["axes"]))
                angle = annotation["angle"]
                cv2.ellipse(annotated_image, center, axes, angle, 0, 360, color, thickness=1)
            else:
                # 구 방식: use points
                points = annotation["points"]
                center = ((points[0][0] + points[1][0]) // 2, (points[0][1] + points[1][1]) // 2)
                axes = (abs(points[1][0] - points[0][0]) // 2, abs(points[1][1] - points[0][1]) // 2)
                cv2.ellipse(annotated_image, center, axes, 0, 0, 360, color, thickness=1)
        else:
            print(f"Skipping unsupported shape: {shape}")

        # If mask exists, decode and overlay it
        if "mask" in annotation:
            print("Decoding mask...")
            mask_data = base64.b64decode(annotation["mask"])
            mask_array = np.frombuffer(mask_data, np.uint8)
            mask_image = cv2.imdecode(mask_array, cv2.IMREAD_GRAYSCALE)
            if mask_image is not None:
                # 만약 mask 이미지의 크기가 원본 이미지와 다르다면 재조정
                if mask_image.shape != original_image.shape[:2]:
                    mask_image = cv2.resize(mask_image, (original_image.shape[1], original_image.shape[0]))
                print(f"Decoded Mask Shape: {mask_image.shape}")

                # Create a colored mask using the annotation color
                mask_colored = np.zeros_like(original_image)
                mask_colored[:, :, :] = color  # Fill mask with the annotation color

                # Apply the mask (scale intensity by mask_image)
                for c in range(3):  # RGB channels
                    mask_colored[:, :, c] = mask_colored[:, :, c] * (mask_image / 255.0)

                # Overlay the mask onto the original image
                annotated_image = cv2.addWeighted(annotated_image, 1.0, mask_colored, 0.3, 0)
            else:
                print("Failed to decode mask.")

    window_width, window_height = 800, 600
    resized_image = resize_image(annotated_image, window_width, window_height)
    cv2.imshow(window_name, resized_image)
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    json_path = filedialog.askopenfilename(
        title="Select JSON File",
        filetypes=[("JSON Files", "*.json")]
    )
    if json_path:
        print(f"Selected JSON file: {json_path}")
        validate_json_annotations(json_path)
    else:
        print("No JSON file selected.")
