import base64
from PIL import Image, ImageTk
import cv2
import numpy as np
import tkinter as tk
from tkinterdnd2 import DND_FILES

from presentation.controller.left_frame_controller import LeftFrameController
from presentation.controller.right_frame_controller import RightFrameController
from presentation.controller.center_frame_controller import CenterFrameController
from presentation.annotation_save_popup import AnnotationSavePopup

class ImageLabelingApp:
    def __init__(self, root):
        self.root = root

        # File and image variables
        self.file_list = []  # Loaded file paths
        self.current_file_path = None
        self.current_image = None  # Original image
        self.adjusted_image = None  # Adjusted for brightness/sharpness
        self.tmp_image = None  # Temporary image for display
        self.original_image_size = None
        self.current_image_size = None

        # Annotations
        self.annotations = {}  # {name: {"color": (B, G, R), "shapes": [...]}}
        self.annotations_per_file = {}  # Annotations by file
        self.file_settings = {}  # Per-file slider settings
        self.drawing_mode = None  # "polygon", "ellipse", or "normal"
        self.points = []  # Temporary points when drawing
        self.selected_annotation = None
        self.selected_shape_index = None

        # Edit (normal) mode
        self.normal_mod_mode = None  # "move", "resize", "rotate"
        self.normal_mod_vertex = None  # "top", "bottom", etc.
        self.normal_mod_start_mouse = None
        self.normal_mod_start_params = None  # (center, axes, angle)

        # Drawing mode
        self.is_drawing = False
        self.start_point = None  # For ellipse drawing

        
        # Image update flag
        self.is_updating_image = False

        self.left_controller = LeftFrameController(self, root)
        self.right_controller = RightFrameController(self, root)
        self.center_controller = CenterFrameController(self, root)

        self.setup_shortcuts()
    

    def setup_shortcuts(self):
        # Enable drag and drop support
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.add_files_via_drag_and_drop)

        # Keyboard shortcuts for mode switching
        # n: normal, e: ellipse, c: closed curve, p: polygon
        self.root.bind("<Delete>", self.handle_delete_key)
        self.root.bind("<n>", lambda event: self.left_controller.set_drawing_mode("normal"))
        self.root.bind("<e>", lambda event: self.left_controller.set_drawing_mode("ellipse"))
        self.root.bind("<c>", lambda event: self.left_controller.set_drawing_mode("closed_curve"))


    def handle_delete_key(self, event):
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        widget_under = self.root.winfo_containing(x, y)
        if widget_under is None:
            return
        if self.is_descendant(widget_under, self.right_controller.get_file_listbox):
            self.delete_selected_file(event)
        elif self.is_descendant(widget_under, self.center_controller.get_image_panel):
            self.delete_selected_annotation(event)

    def is_descendant(self, widget, parent):
        while widget is not None:
            if widget == parent:
                return True
            widget = widget.master
        return False
        
    def delete_selected_file(self, event):
        selection = self.right_controller.get_file_list_curselection
        if not selection:
            return
        index = selection[0]
        file_to_remove = self.file_list[index]
        self.right_controller.delete_selected_file_from_listbox(index)
        del self.file_list[index]
        print(f"Removed: {file_to_remove}")
        self.current_file_path = None
        self.current_image = None
        self.annotations.clear()
        self.right_controller.delete_selected_annotation_from_listbox()
        self.clear_image_panel()
        print("Image panel and annotation list cleared.")

    def delete_file_from_listbox(self, first=None):
        self.right_controller.delete_selected_file_from_listbox(first)


    def delete_selected_annotation(self, event=None):
        if self.selected_annotation is not None:
            del self.annotations[self.selected_annotation]["shapes"][self.selected_shape_index]
            if not self.annotations[self.selected_annotation]["shapes"]:
                del self.annotations[self.selected_annotation]
                for i in range(self.right_controller.get_file_list_curselection("annotation")):
                    if self.right_controller.get_annotation_from_listbox(i) == self.selected_annotation:
                        self.right_controller.delete_selected_annotation_from_listbox(i)
                        break
            self.selected_annotation = None
            self.selected_shape_index = None
            self.update_display(apply_adjustments=False, redraw_annotations=True)


    def update_display(self, apply_adjustments=True, redraw_annotations=True):
        if self.current_image is None:
            self.tmp_image = None
            self.center_controller.clear_image_panel()
            self.drawing_mode = None
            return
        
        if apply_adjustments:
            self.adjusted_image = self.left_controller.adjust_brightness_and_sharpness(self.current_image)

        panel_size = self.get_image_panel_size()

        self.tmp_image = cv2.resize(self.adjusted_image, panel_size)

        if redraw_annotations:
            self.redraw_annotations()
            self.show_image()
        else:
            self.show_image()


    def show_image(self):
        if self.tmp_image is None:
            return
        img_rgb = cv2.cvtColor(self.tmp_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        self.center_controller.show_in_image_panel(img_tk)

    def show_image_with_tmp(self, tmp_image):
        img_rgb = cv2.cvtColor(tmp_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        self.center_controller.show_in_image_panel(img_tk)


    def get_image_panel_size(self):
        return self.center_controller.get_image_panel_size()
    
    def get_filter_slider_value(self):
        return self.left_controller.get_filter_slider_value()

    def set_slider_value(self, value={"brightness":50, "sharpness":0}):
        self.left_controller.set_slider_value(value)

    def redraw_annotations(self):
        if self.tmp_image is None:
            return
        disp_w, disp_h = self.get_image_panel_size()
        orig_w, orig_h = self.original_image_size
        scale_x = disp_w / orig_w
        scale_y = disp_h / orig_h

        temp_img = self.tmp_image.copy()
        for name, data in self.annotations.items():
            color = data["color"]
            for shape_data in data["shapes"]:
                shape = shape_data["shape"]
                if shape == "ellipse":
                    if "center" in shape_data:
                        center = shape_data["center"]
                        axes = shape_data["axes"]
                        angle = shape_data["angle"]
                        disp_center = (int(center[0] * scale_x), int(center[1] * scale_y))
                        disp_axes = (int(axes[0] * scale_x), int(axes[1] * scale_y))
                        cv2.ellipse(temp_img, disp_center, disp_axes, angle, 0, 360, color, 1)
                    else:
                        pts = shape_data["points"]
                        disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in pts]
                        center = ((disp_pts[0][0] + disp_pts[1][0]) // 2, (disp_pts[0][1] + disp_pts[1][1]) // 2)
                        axes = (abs(disp_pts[1][0]-disp_pts[0][0])//2, abs(disp_pts[1][1]-disp_pts[0][1])//2)
                        cv2.ellipse(temp_img, center, axes, 0, 0, 360, color, 1)
                elif shape in ["polygon", "closed_curve"]:
                    pts = shape_data["points"]
                    disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in pts]
                    cv2.polylines(temp_img, [np.array(disp_pts)], isClosed=(shape=="polygon"), color=color, thickness=1)
        self.tmp_image = temp_img
        self.show_image()
    
    def handle_ellipse(self, start, end):
        center = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        axes = (abs(end[0]-start[0])//2, abs(end[1]-start[1])//2)
        cv2.ellipse(self.tmp_image, center, axes, 0, 0, 360, (255,0,0), 1)
        self.show_image()

    def add_annotation_into_listbox(self, annotation_text):
        self.right_controller.add_annotation_into_listbox(annotation_text)
        
    def add_file_into_listbox(self, content, at=tk.END):
        self.right_controller.add_file_into_listbox(content, at=at)
    
    def get_size_of_listbox(self, type):
        return self.right_controller.get_listbox_size(type)

    def get_annotation_from_listbox(self, index):
        return self.right_controller.get_annotation_from_listbox(index)

    def get_annotation_color(self, annotation_text):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
                  (255, 255, 0), (255, 0, 255), (0, 255, 255)]
        if annotation_text in self.annotations:
            return self.annotations[annotation_text]["color"]
        else:
            return colors[len(self.annotations) % len(colors)]

    def redraw_annotations(self):
        if self.tmp_image is None:
            return
        disp_w, disp_h = self.get_image_panel_size()
        orig_w, orig_h = self.original_image_size
        scale_x = disp_w / orig_w
        scale_y = disp_h / orig_h

        temp_img = self.tmp_image.copy()
        for _, data in self.annotations.items():
            color = data["color"]
            for shape_data in data["shapes"]:
                shape = shape_data["shape"]
                if shape == "ellipse":
                    if "center" in shape_data:
                        center = shape_data["center"]
                        axes = shape_data["axes"]
                        angle = shape_data["angle"]
                        disp_center = (int(center[0] * scale_x), int(center[1] * scale_y))
                        disp_axes = (int(axes[0] * scale_x), int(axes[1] * scale_y))
                        cv2.ellipse(temp_img, disp_center, disp_axes, angle, 0, 360, color, 1)
                    else:
                        pts = shape_data["points"]
                        disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in pts]
                        center = ((disp_pts[0][0] + disp_pts[1][0]) // 2, (disp_pts[0][1] + disp_pts[1][1]) // 2)
                        axes = (abs(disp_pts[1][0]-disp_pts[0][0])//2, abs(disp_pts[1][1]-disp_pts[0][1])//2)
                        cv2.ellipse(temp_img, center, axes, 0, 0, 360, color, 1)
                elif shape in ["polygon", "closed_curve"]:
                    pts = shape_data["points"]
                    disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in pts]
                    cv2.polylines(temp_img, [np.array(disp_pts)], isClosed=(shape=="polygon"), color=color, thickness=1)
        self.tmp_image = temp_img
        self.show_image()

    def clear_image_panel(self):
        self.center_controller.clear_image_panel()

    def add_files_via_drag_and_drop(self, event):
        new_files = self.root.tk.splitlist(event.data)

        self.right_controller.add_files_via_drag_and_drop(new_files)