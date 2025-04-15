import subprocess
import sys
import os
import cv2
import numpy as np

from tkinter import messagebox

from view.left_frame import LeftFrame
from utils.annotation_io import save_annotations_to_json
from utils.validation import validate_annotation_masks


class LeftFrameController:
    def __init__(self, master, root):
        self.master = master
        self.view = LeftFrame(root)
        self.setup_ui_event()

    def setup_ui_event(self):
        self.view.validation_btn.config(command=self.run_validation)
        self.view.save_json_btn.config(command=self.save_labels_to_json)
        self.view.ellipse_btn.config(command=lambda: self.set_drawing_mode("ellipse"))
        self.view.normal_btn.config(command=lambda: self.set_drawing_mode("normal"))
        self.view.closed_curve_btn.config(command=lambda: self.set_drawing_mode("closed_curve"))
        self.view.brightness_slider.config(command=self.update_adjusted_image)
        self.view.sharpness_slider.config(command=self.update_adjusted_image)
        self.view.reset_btn.config(command=self.reset_adjustments)

    def run_validation(self):
        if not self.master.current_file_path:
            print("[ERROR] No file loaded.")
            return

        json_path = os.path.splitext(self.master.current_file_path)[0] + ".json"
        validate_annotation_masks(json_path)

        self.master.is_drawing = False
        self.master.start_point = None
        self.master.points = []
        self.master.drawing_mode = None
        print("Annotation mode reset.")

    def save_labels_to_json(self):
        if not self.master.current_file_path:
            print("No file is currently loaded.")
            return

        json_path = save_annotations_to_json(
            file_path=self.master.current_file_path,
            annotations=self.master.annotations,
            original_size=self.master.original_image_size
        )

        if json_path:
            print(f"Annotations and masks saved to {json_path}")
            messagebox.showinfo("Save Complete", f"Annotations have been successfully saved to:\n{json_path}")
            self.master.delete_file_from_listbox()
            for file in self.master.file_list:
                file_name = os.path.basename(file)
                json_file_path = os.path.splitext(file)[0] + ".json"
                display_name = f"{file_name} ✅" if os.path.exists(json_file_path) else file_name
                self.master.utils.add_file_into_listbox(display_name)
        else:
            print("[ERROR] Failed to save annotations.")

    def set_slider_value(self, value={"brightness": 50, "sharpness": 0}):
        self.view.brightness_slider.set(value["brightness"])
        self.view.sharpness_slider.set(value["sharpness"])

    def set_drawing_mode(self, mode):
        self.master.drawing_mode = mode
        self.master.points = []
        self.master.is_drawing = False

        self.view.closed_curve_btn.config(relief="raised", bg="SystemButtonFace")
        self.view.ellipse_btn.config(relief="raised", bg="SystemButtonFace")
        self.view.normal_btn.config(relief="raised", bg="SystemButtonFace")

        if mode == "closed_curve":
            self.view.closed_curve_btn.config(relief="sunken", bg="lightblue")
        elif mode == "ellipse":
            self.view.ellipse_btn.config(relief="sunken", bg="lightblue")
        elif mode == "normal":
            self.view.normal_btn.config(relief="sunken", bg="lightblue")

        if mode == "normal":
            self.master.normal_mod_mode = None
            self.master.normal_mod_vertex = None
            self.master.normal_mod_start_mouse = None
            self.master.normal_mod_start_params = None

        print(f"Drawing mode set to: {mode}")

    def update_adjusted_image(self, _=None):
        self.master.update_display(apply_adjustments=True, redraw_annotations=True)

    def adjust_brightness_and_sharpness(self, image):
        brightness = self.view.brightness_slider.get()
        sharpness = self.view.sharpness_slider.get()

        if brightness != 50:
            brightness_scale = (brightness - 50) * 2.55
            image = cv2.convertScaleAbs(image, alpha=1, beta=int(brightness_scale))
        if sharpness > 0:
            kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]]) * sharpness
            high_pass = cv2.filter2D(image, -1, kernel)
            image = cv2.addWeighted(image, 1, high_pass, 1, 0)
        return image

    def reset_adjustments(self):
        self.view.brightness_slider.set(50)
        self.view.sharpness_slider.set(0)
        self.update_adjusted_image()

    def get_filter_slider_value(self):
        brightness = self.view.brightness_slider.get()
        sharpness = self.view.sharpness_slider.get()
        return {"brightness": brightness, "sharpness": sharpness}