import os
import json
import tkinter as tk
from tkinter import filedialog

from view.right_frame import RightFrame
from utils.annotation_io import load_annotations_from_json
from utils.image_loader import load_image

class RightFrameController:
    def __init__(self, master, root):
        self.master = master
        self.view = RightFrame(root)
        self.setup_ui_event()

    def setup_ui_event(self):
        self.view.file_listbox.bind("<<ListboxSelect>>", self.display_selected_image)
        self.view.load_files_btn.config(command=self.load_annotations_via_dialog)

    def add_files_via_drag_and_drop(self, file_paths):
        for path in file_paths:
            if path not in self.master.file_list and path.lower().endswith(('.jpg', '.jpeg', '.png', '.dcm')):
                self.master.file_list.append(path)
                self.master.utils.add_file_into_listbox(os.path.basename(path))
        if not self.master.current_file_path and self.master.file_list:
            self.display_selected_image()

    def delete_selected_file_from_listbox(self):
        selected = self.view.file_listbox.curselection()
        if selected:
            idx = selected[0]
            del self.master.file_list[idx]
            self.view.file_listbox.delete(idx)

    def get_file_listbox(self):
        return self.view.file_listbox

    def get_file_list_curselection(self, list_type):
        return self.view.file_listbox.curselection()[0]

    def add_annotation_into_listbox(self, text):
        self.view.annotation_listbox.insert(tk.END, text)

    def get_annotation_from_listbox(self, index):
        return self.view.annotation_listbox.get(index)

    def delete_selected_annotation_from_listbox(self, index):
        self.view.annotation_listbox.delete(index)

    def get_listbox_size(self, list_type):
        if list_type == "annotation":
            return self.view.annotation_listbox.size()
        return self.view.file_listbox.size()

    def load_annotations_from_json(self, json_file):
        if not os.path.exists(json_file):
            print(f"[WARNING] JSON file not found: {json_file}")
            return

        annotations = load_annotations_from_json(json_file)
        self.master.annotations = annotations

        for name in annotations:
            self.master.utils.add_annotation_into_listbox(name)

        print(f"Annotations loaded from {json_file}")

    def load_annotations_via_dialog(self):
        json_file = filedialog.askopenfilename(
            title="Select Annotation JSON",
            filetypes=[("JSON Files", "*.json")]
        )
        if json_file:
            self.load_annotations_from_json(json_file)
            self.display_selected_image()

    def display_selected_image(self, event=None):
        selection = self.view.file_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        file_path = self.master.file_list[index]
        self.master.current_file_path = file_path

        image = load_image(file_path)
        if image is not None:
            self.master.current_image = image
            self.master.original_image_size = (image.shape[1], image.shape[0])
            self.master.utils.set_slider_value()
            self.master.annotations = {}
            self.view.annotation_listbox.delete(0, tk.END)

            json_path = os.path.splitext(file_path)[0] + ".json"
            self.load_annotations_from_json(json_path)
            self.master.update_display()