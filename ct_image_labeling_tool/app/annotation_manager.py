import cv2
import numpy as np
from PIL import Image, ImageTk
from model.annotation import EllipseAnnotation, PolygonAnnotation

class AnnotationManager:
    def __init__(self, app):
        self.app = app

    def update_display(self, apply_adjustments=True, redraw_annotations=True):
        if self.app.current_image is None:
            self.app.tmp_image = None
            self.app.center_controller.clear_image_panel()
            self.app.drawing_mode = None
            return

        if apply_adjustments:
            self.app.adjusted_image = self.app.left_controller.adjust_brightness_and_sharpness(
                self.app.current_image)

        panel_size = self.app.center_controller.get_image_panel_size()
        self.app.tmp_image = cv2.resize(self.app.adjusted_image, panel_size)

        if redraw_annotations:
            self.redraw_annotations()
            self.show_image()
        else:
            self.show_image()

    def show_image(self):
        if self.app.tmp_image is None:
            return
        img_rgb = cv2.cvtColor(self.app.tmp_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)
        self.app.center_controller.show_in_image_panel(img_tk)

    def show_image_with_tmp(self, tmp_image):
        img_rgb = cv2.cvtColor(tmp_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)
        self.app.center_controller.show_in_image_panel(img_tk)

    def redraw_annotations(self):
        if self.app.tmp_image is None:
            return

        disp_w, disp_h = self.app.center_controller.get_image_panel_size()
        orig_w, orig_h = self.app.original_image_size
        scale_x = disp_w / orig_w
        scale_y = disp_h / orig_h

        temp_img = self.app.tmp_image.copy()

        for name, group in self.app.annotations.items():
            color = group.color
            for shape in group.shapes:
                if isinstance(shape, EllipseAnnotation):
                    disp_center = (int(shape.center[0] * scale_x), int(shape.center[1] * scale_y))
                    disp_axes = (int(shape.axes[0] * scale_x), int(shape.axes[1] * scale_y))
                    cv2.ellipse(temp_img, disp_center, disp_axes, shape.angle, 0, 360, color, 1)
                elif isinstance(shape, PolygonAnnotation):
                    disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in shape.points]
                    is_closed = shape.shape == "polygon"
                    cv2.polylines(temp_img, [np.array(disp_pts)], isClosed=is_closed, color=color, thickness=1)

        self.app.tmp_image = temp_img
        self.show_image()

    def delete_selected_annotation(self):
        name = self.app.selected_annotation
        index = self.app.selected_shape_index
        if name is not None and index is not None:
            group = self.app.annotations[name]
            del group.shapes[index]
            if not group.shapes:
                del self.app.annotations[name]
                for i in range(self.app.right_controller.get_file_list_curselection("annotation")):
                    if self.app.right_controller.get_annotation_from_listbox(i) == name:
                        self.app.right_controller.delete_selected_annotation_from_listbox(i)
                        break
            self.app.selected_annotation = None
            self.app.selected_shape_index = None
            self.update_display(apply_adjustments=False, redraw_annotations=True)

    def handle_ellipse(self, start, end):
        center = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        axes = (abs(end[0] - start[0]) // 2, abs(end[1] - start[1]) // 2)
        cv2.ellipse(self.app.tmp_image, center, axes, 0, 0, 360, (255, 0, 0), 1)
        self.show_image()

    def get_image_panel_size(self):
        return self.app.center_controller.get_image_panel_size()