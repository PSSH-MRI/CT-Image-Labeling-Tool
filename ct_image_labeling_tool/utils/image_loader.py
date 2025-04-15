import os
import cv2

def load_image(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".dcm":
        try:
            import pydicom
            dicom_data = pydicom.dcmread(file_path)
            img_array = dicom_data.pixel_array
            img_norm = ((img_array - img_array.min()) / (img_array.ptp()) * 255).astype('uint8')
            return cv2.cvtColor(img_norm, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            print(f"[ERROR] Failed to read DICOM: {e}")
            return None
    else:
        try:
            return cv2.imread(file_path)
        except Exception as e:
            print(f"[ERROR] Failed to read image: {e}")
            return None
