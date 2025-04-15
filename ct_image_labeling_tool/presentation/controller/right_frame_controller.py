import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os

import cv2
import numpy as np
import pydicom

from presentation.view.right_frame import RightFrame


class RightFrameController:
    def __init__(self, master, root):
        self.master = master
        self.file_settings = {}  # Per-file slider settings
        
        self.view = RightFrame(root)
        self.setup_ui_event()


    def setup_ui_event(self):
        self.view.annotation_listbox.bind("<Double-Button-1>", self.edit_annotation_name)
        self.view.file_listbox.bind("<<ListboxSelect>>", self.display_selected_image)
        self.view.load_files_btn.config(command=self.load_files)


    @property
    def get_file_listbox(self):
        return self.view.file_listbox


    @property
    def get_file_list_curselection(self):
        return self.view.file_listbox.curselection()


    def get_listbox_size(self, type):
        """
        Get listbox size from view.

        Args:
            type (str): {"annotation" or "file"}

        Returns:
            int: The size of the selected type's listbox
        """
        if type == "annotation":
            return self.view.annotation_listbox.size()
        elif type == "file":
            return self.view.file_listbox.size()
        else:
            print("The type is invalid. It can only be annotation or file. Please check your value again.")
            return 0
        


    def get_annotation_from_listbox(self, index):
        return self.view.annotation_listbox.get(index)


    def add_annotation_into_listbox(self, annotation_text, index=tk.END):
        self.view.annotation_listbox.insert(index, annotation_text)


    def add_file_into_listbox(self, content, at=tk.END):
        self.view.file_listbox.insert(at, content)


    def delete_selected_file_from_listbox(self, first=None):
        """
        Delete annotation form listbox

        Args:
            index (int): {index} if index == None delete all
        """
        if first == None:
            self.view.file_listbox.delete(0, tk.END)
        else:
            self.view.file_listbox.delete(first)


    def delete_selected_annotation_from_listbox(self, first=None):
        """
        Delete annotation form listbox

        Args:
            index (int): {index} if index == None delete all
        """
        if first == None:
            self.view.annotation_listbox.delete(0, tk.END)
        else:
            self.view.annotation_listbox.delete(first)


    def load_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.dcm"), ("All files", "*.*")])
        if file_paths:
            unsaved = {file: data for file, data in self.master.annotations_per_file.items() if data and not os.path.exists(os.path.splitext(file)[0] + ".json")}
            if unsaved:
                response = messagebox.askyesno("Warning", "There are unsaved annotations for some files. Do you want to discard them?")
                if response:
                    for file in unsaved.keys():
                        del self.master.annotations_per_file[file]
                    self.master.annotations.clear()
                    self.master.current_file_path = None
                    self.master.current_image = None
                    self.master.clear_image_panel()

                    self.delete_selected_file_from_listbox()
                    print("[INFO] Unsaved annotations discarded.")
                else:
                    print("[INFO] File load cancelled.")
                    return
            self.master.annotations_per_file.clear()
            self.master.annotations.clear()
            self.master.current_file_path = None
            self.master.current_image = None
            self.master.clear_image_panel()

            self.delete_selected_annotation_from_listbox()
            self.master.file_list = list(file_paths)
            self.delete_selected_file_from_listbox()

            for file in self.master.file_list:
                file_name = os.path.basename(file)
                json_file_path = os.path.splitext(file)[0] + ".json"
                if os.path.exists(json_file_path):
                    display_name = f"{file_name} ✅"
                    self.load_annotations_from_json(json_file_path)
                    self.master.annotations_per_file[file] = self.master.annotations.copy()
                else:
                    display_name = file_name
                self.add_file_into_listbox(display_name)

            if self.master.file_list:
                self.master.current_file_path = self.master.file_list[0]
                self.master.current_image = self.load_image(self.master.file_list[0])
                self.adjusted_image = self.master.current_image.copy()
                if self.master.current_file_path in self.file_settings:
                    settings = self.file_settings[self.master.current_file_path]
                    self.master.set_slider_value({"brightness":settings["brightness"], "sharpness":settings["sharpness"]})
                else:
                    self.master.set_slider_value()
                    pass
                self.master.update_display()
            else:
                self.master.current_file_path = None
                self.master.current_image = None
                self.master.annotations.clear()
                self.master.clear_image_panel()

                self.delete_selected_annotation_from_listbox()
                print("No files loaded.")


    def add_files_via_drag_and_drop(self, new_files):
        for file in new_files:
            if file not in self.master.file_list:
                self.master.file_list.append(file)
                file_name = os.path.basename(file)
                json_file_path = os.path.splitext(file)[0] + ".json"
                display_name = f"{file_name} ✅" if os.path.exists(json_file_path) else file_name
                self.add_file_into_listbox(display_name)
        print(f"Files added via drag-and-drop: {new_files}")
        
        if self.master.file_list and self.master.current_image is None:
            self.master.current_file_path = self.master.file_list[0]
            self.master.current_image = self.load_image(self.master.current_file_path)
            self.master.adjusted_image = self.master.current_image.copy()
            json_file_path = os.path.splitext(self.master.current_file_path)[0] + ".json"
            if os.path.exists(json_file_path):
                print(f"[INFO] JSON file found for {self.master.current_file_path}")
                self.load_annotations_from_json(json_file_path)
            else:
                self.master.annotations.clear()
            self.delete_selected_annotation_from_listbox()
            for name in self.master.annotations.keys():
                self.view.annotation_listbox.insert(tk.END, name)
            self.master.update_display(apply_adjustments=False, redraw_annotations=True)


    def edit_annotation_name(self, event):
        selection = self.view.annotation_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        old_name = self.view.annotation_listbox.get(index)
        new_name = simpledialog.askstring("Rename Annotation", "Enter new annotation name:", initialvalue=old_name)
        if new_name and new_name.strip():
            new_name = new_name.strip()
            if new_name in self.master.annotations:
                messagebox.showerror("Error", "Annotation with this name already exists.")
                return
            self.master.annotations[new_name] = self.master.annotations.pop(old_name)
            self.delete_selected_annotation_from_listbox(index)
            self.view.annotation_listbox.insert(index, new_name)
            print(f"Annotation renamed from {old_name} to {new_name}")


    def display_selected_image(self, event):
        selection = self.view.file_listbox.curselection()
        if selection:
            file_path = self.master.file_list[selection[0]]
            if self.master.current_file_path:
                self.file_settings[self.master.current_file_path] = self.master.get_filter_slider_value()
                self.master.annotations_per_file[self.master.current_file_path] = self.master.annotations.copy()
            self.master.current_file_path = file_path
            self.master.current_image = self.load_image(file_path)
            if self.master.current_image is None:
                print(f"Error: Failed to load {file_path}")
                return
            json_file_path = os.path.splitext(file_path)[0] + ".json"
            if os.path.exists(json_file_path):
                print(f"[INFO] JSON file found: {json_file_path}")
                try:
                    self.load_annotations_from_json(json_file_path)
                    self.master.annotations_per_file[file_path] = self.master.annotations.copy()
                except Exception as e:
                    print(f"[ERROR] Failed to load annotations from JSON: {e}")
            else:
                print(f"[INFO] No JSON file found for {file_path}")
                if file_path in self.master.annotations_per_file:
                    self.master.annotations = self.master.annotations_per_file[file_path].copy()
                    print(f"[INFO] Restored annotations from memory for {file_path}")
                else:
                    self.master.annotations.clear()
            self.delete_selected_annotation_from_listbox()
            for name in self.master.annotations.keys():
                self.view.annotation_listbox.insert(tk.END, name)
            if file_path in self.file_settings:
                settings = self.file_settings[file_path]
                self.master.set_slider_value({"brightness":settings["brightness"], "sharpness":settings["sharpness"]})
            else:
                self.master.set_slider_value()
            self.master.adjusted_image = self.master.current_image.copy()
            self.master.update_display(apply_adjustments=False, redraw_annotations=True)
        else:
            print("No file selected from the listbox.")


    def load_image(self, file_path):
        self.master.current_file_path = file_path
        if file_path.endswith(".dcm"):
            ds = pydicom.dcmread(file_path)
            img = ds.pixel_array
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        self.master.original_image_size = (img.shape[1], img.shape[0])
        return img


    def load_annotations_from_json(self, json_file):
        try:
            with open(json_file, "r") as file:
                data = json.load(file)
                print(f"[INFO] Loaded JSON data from: {json_file}")
            self.master.annotations.clear()
            for annotation in data.get("annotations", []):
                name = annotation["name"]
                shape = annotation["shape"]
                color = tuple(annotation["color"])
                mask = annotation.get("mask")
                orig_size = annotation.get("orig_size", self.master.original_image_size)
                if shape == "ellipse":
                    if "center" in annotation and "axes" in annotation and "angle" in annotation:
                        shape_data = {
                            "shape": "ellipse",
                            "center": annotation["center"],
                            "axes": annotation["axes"],
                            "angle": annotation["angle"],
                            "mask": mask,
                            "image_size": orig_size
                        }
                    else:
                        points = annotation["points"]
                        shape_data = {
                            "shape": "ellipse",
                            "points": points,
                            "mask": mask,
                            "image_size": orig_size
                        }
                else:
                    points = annotation["points"]
                    shape_data = {
                        "shape": shape,
                        "points": points,
                        "mask": mask,
                        "image_size": orig_size
                    }
                if name not in self.master.annotations:
                    self.master.annotations[name] = {"color": color, "shapes": []}
                    self.view.annotation_listbox.insert(tk.END, name)
                self.master.annotations[name]["shapes"].append(shape_data)
            print("[INFO] Annotations loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load JSON annotations: {e}")