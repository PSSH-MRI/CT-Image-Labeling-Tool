import base64
import tkinter as tk
import cv2
import numpy as np

from model.annotation import EllipseAnnotation, PolygonAnnotation

class AnnotationSavePopup(tk.Toplevel):
    def __init__(self, root, app, points, shape):
        super().__init__(root)
        self.root = root
        self.app = app
        self.points = points
        self.shape = shape

        self.setup_ui()

    def setup_ui(self):
        self.title("Select or Enter Annotation Text")
        self.geometry("400x250")
        self.root.update_idletasks()

        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()

        popup_w, popup_h = 400, 250
        pos_x = main_x + (main_w - popup_w) // 2
        pos_y = main_y + (main_h - popup_h) // 2
        self.geometry(f"{popup_w}x{popup_h}+{pos_x}+{pos_y}")

        self.transient(self.root)
        self.grab_set()
        self.focus_force()
        self.lift()

        label_font = ("Helvetica", 14, "bold")
        entry_font = ("Helvetica", 14)
        button_font = ("Helvetica", 12)

        tk.Label(self, text="Select existing annotation (or leave blank):", font=label_font).pack(pady=5)

        existing = [self.app.utils.get_annotation_from_listbox(i)
                    for i in range(self.app.utils.get_size_of_listbox("annotation"))]
        if not existing:
            existing = ["No existing annotations"]

        self.selected_var = tk.StringVar(self)
        self.selected_var.set(existing[0])

        self.option_menu = tk.OptionMenu(self, self.selected_var, *existing)
        self.option_menu.config(font=entry_font)
        self.option_menu.pack(pady=5)

        tk.Label(self, text="Or enter a new annotation name:", font=label_font).pack(pady=5)
        self.text_entry = tk.Entry(self, width=30, font=entry_font)
        self.text_entry.pack(pady=5)
        self.text_entry.focus_set()

        self.save_btn = tk.Button(self, text="Save", command=self.save_annotation, font=button_font)
        self.save_btn.pack(pady=10)
        self.text_entry.bind("<Return>", lambda event: self.save_annotation())
        self.bind("<Escape>", self.close_popup)

        self.wait_window(self)

    def save_annotation(self):
        annotation_text = self.text_entry.get().strip()
        if annotation_text == "" or annotation_text == "No existing annotations":
            annotation_text = self.selected_var.get()
        if annotation_text and annotation_text != "No existing annotations":
            color = self.app.utils.get_annotation_color(annotation_text)
            disp_w, disp_h = self.app.tmp_image.shape[1], self.app.tmp_image.shape[0]
            orig_w, orig_h = self.app.original_image_size
            scale_x = orig_w / disp_w
            scale_y = orig_h / disp_h

            if self.shape == "ellipse":
                if isinstance(self.points, dict):
                    center = self.points["center"]
                    axes = self.points["axes"]
                    angle = self.points["angle"]
                    new_shape = EllipseAnnotation(
                        shape="ellipse",
                        center=(center[0] * scale_x, center[1] * scale_y),
                        axes=(axes[0] * scale_x, axes[1] * scale_y),
                        angle=angle,
                        image_size=self.app.original_image_size
                    )
                else:
                    pt1 = (self.points[0][0] * scale_x, self.points[0][1] * scale_y)
                    pt2 = (self.points[1][0] * scale_x, self.points[1][1] * scale_y)
                    center = ((pt1[0] + pt2[0]) / 2, (pt1[1] + pt2[1]) / 2)
                    axes = (abs(pt2[0] - pt1[0]) / 2, abs(pt2[1] - pt1[1]) / 2)
                    new_shape = EllipseAnnotation(
                        shape="ellipse",
                        center=center,
                        axes=axes,
                        angle=0,
                        image_size=self.app.original_image_size
                    )

                mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                cv2.ellipse(mask, tuple(map(int, new_shape.center)),
                            tuple(map(int, new_shape.axes)), new_shape.angle, 0, 360, 255, -1)
                _, buffer = cv2.imencode(".png", mask)
                new_shape.mask = base64.b64encode(buffer).decode("utf-8")

            else:
                converted_points = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in self.points]
                new_shape = PolygonAnnotation(
                    shape=self.shape,
                    points=converted_points,
                    image_size=self.app.original_image_size
                )
                mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                cv2.fillPoly(mask, [np.array(converted_points, dtype=np.int32)], color=255)
                _, buffer = cv2.imencode(".png", mask)
                new_shape.mask = base64.b64encode(buffer).decode("utf-8")

            if annotation_text not in self.app.annotations:
                from model.annotation import AnnotationGroup
                self.app.annotations[annotation_text] = AnnotationGroup(color=color)
                self.app.utils.add_annotation_into_listbox(annotation_text)

            self.app.annotations[annotation_text].shapes.append(new_shape)

        self.destroy()
        self.app.update_display(apply_adjustments=False, redraw_annotations=True)

    def close_popup(self, event=None):
        self.destroy()