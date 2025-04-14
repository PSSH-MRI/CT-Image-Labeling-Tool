import subprocess
import sys
import os
import cv2
import numpy as np
import base64
import json

import tkinter as tk
from tkinter import messagebox

from presentation.view.left_frame import LeftFrame

class LeftFrameController:
    def __init__(self, master, root):
        self.master = master
        self.view = LeftFrame(root)
        self.setup_ui_event()


    def setup_ui_event(self):
        # Utility buttons
        self.view.validation_btn.config(command=self.run_validation)
        self.view.save_json_btn.config(command=self.save_labels_to_json)

        # Mode selection buttons
        self.view.ellipse_btn.config(command=lambda: self.set_drawing_mode("ellipse"))
        self.view.normal_btn.config(command=lambda: self.set_drawing_mode("normal"))
        self.view.closed_curve_btn.config(command=lambda: self.set_drawing_mode("closed_curve"))

        # Image filtering controls
        self.view.brightness_slider.config(command=self.update_adjusted_image)
        self.view.sharpness_slider.config(command=self.update_adjusted_image)
        self.view.reset_btn.config(command=self.reset_adjustments)


    def run_validation(self):
        try:
            script_path = self.resource_path("validation.py")
            subprocess.run([sys.executable, script_path], check=True)
            print("Validation completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Validation script failed: {e}")
        finally:
            self.master.is_drawing = False
            self.master.start_point = None
            self.master.points = []
            self.master.drawing_mode = None
            print("Annotation mode reset.")


    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


    def save_labels_to_json(self):
        if not self.master.current_file_path:
            print("No file is currently loaded.")
            return
        
        json_file = os.path.splitext(self.master.current_file_path)[0] + ".json"

        if os.path.exists(json_file):
            response = messagebox.askyesno("Overwrite Confirmation",
                                           f"A file named '{os.path.basename(json_file)}' already exists. Do you want to overwrite it?")
            if not response:
                print("Save operation cancelled.")
                return
            
        self.master.annotations_per_file[self.master.current_file_path] = self.master.annotations.copy()
        label_data = {"file_path": [os.path.basename(self.master.current_file_path)], "annotations": []}
        orig_w, orig_h = self.master.original_image_size

        for name, data in self.master.annotations.items():
            for shape_data in data["shapes"]:
                if shape_data["shape"] == "ellipse" and "center" in shape_data:
                    if "mask" not in shape_data:
                        mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                        cv2.ellipse(mask, tuple(map(int, shape_data["center"])),
                                    tuple(map(int, shape_data["axes"])), shape_data["angle"], 0, 360, 255, -1)
                        _, buffer = cv2.imencode(".png", mask)
                        shape_data["mask"] = base64.b64encode(buffer).decode("utf-8")
                    annotation_entry = {
                        "name": name,
                        "shape": "ellipse",
                        "center": shape_data["center"],
                        "axes": shape_data["axes"],
                        "angle": shape_data["angle"],
                        "color": data["color"],
                        "mask": shape_data["mask"],
                        "orig_size": shape_data["image_size"]
                    }
                else:
                    ann_size = shape_data["image_size"]
                    scale_x = orig_w / ann_size[0]
                    scale_y = orig_h / ann_size[1]
                    
                    if "points" in shape_data:
                        converted_points = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in shape_data["points"]]
                    else:
                        converted_points = []

                    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                    if shape_data["shape"] in ["polygon", "closed_curve"]:
                        cv2.fillPoly(mask, [np.array(converted_points, dtype=np.int32)], color=255)
                    else:
                        pts = shape_data.get("points", [])
                        if pts:
                            center_tmp = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
                            axes_tmp = (abs(pts[1][0] - pts[0][0]) / 2, abs(pts[1][1] - pts[0][1]) / 2)
                            cv2.ellipse(mask, tuple(map(int, center_tmp)), tuple(map(int, axes_tmp)), 0, 0, 360, 255, -1)
                    _, buffer = cv2.imencode(".png", mask)
                    mask_base64_resized = base64.b64encode(buffer).decode("utf-8")
                    annotation_entry = {
                        "name": name,
                        "shape": shape_data["shape"],
                        "points": converted_points,
                        "color": data["color"],
                        "mask": mask_base64_resized,
                        "orig_size": shape_data["image_size"]
                    }
                label_data["annotations"].append(annotation_entry)

        with open(json_file, "w") as json_obj:
            json.dump(label_data, json_obj, indent=4)

        print(f"Annotations and masks saved to {json_file}")
        messagebox.showinfo("Save Complete", f"Annotations have been successfully saved to:\n{json_file}")
        
        self.master.delete_file_from_listbox()

        for file in self.master.file_list:
            file_name = os.path.basename(file)
            json_file_path = os.path.splitext(file)[0] + ".json"
            display_name = f"{file_name} ✅" if os.path.exists(json_file_path) else file_name
            self.master.add_file_into_listbox(display_name)


    def set_slider_value(self, value={"brightness":50, "sharpness":0}):
        self.view.brightness_slider.set(value["brightness"])
        self.view.sharpness_slider.set(value["sharpness"])


    def set_drawing_mode(self, mode):
        """
        Set the current drawing mode and update UI button states accordingly.

        Parameters:
            mode (str): The drawing mode to activate. 
                        Valid options are "closed_curve", "ellipse", and "normal".

        Behavior:
            - Resets drawing state and temporary points.
            - Highlights the selected mode button in the UI.
            - If mode is "normal", resets parameters related to object modification.
        """
        
        # Update drawing mode and reset drawing state
        self.master.drawing_mode = mode
        self.master.points = []
        self.master.is_drawing = False

        # Reset all mode buttons to default (raised) state
        self.view.closed_curve_btn.config(relief="raised", bg="SystemButtonFace")
        self.view.ellipse_btn.config(relief="raised", bg="SystemButtonFace")
        self.view.normal_btn.config(relief="raised", bg="SystemButtonFace")


        # Highlight the selected mode button
        if mode == "closed_curve":
            self.view.closed_curve_btn.config(relief="sunken", bg="lightblue")
        elif mode == "ellipse":
            self.view.ellipse_btn.config(relief="sunken", bg="lightblue")
        elif mode == "normal":
            self.view.normal_btn.config(relief="sunken", bg="lightblue")

        # Reset normal mode parameters when switching to normal mode
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

        return {"brightness" : brightness, "sharpness": sharpness}