import base64
from PIL import Image, ImageTk
import cv2
import numpy as np
import tkinter as tk
from tkinterdnd2 import DND_FILES

from presentation.view.left_frame import LeftFrame
from presentation.view.right_frame import RightFrame
from presentation.view.center_frame import CenterFrame

from presentation.controller.left_frame_controller import LeftFrameController
from presentation.controller.right_frame_controller import RightFrameController
from presentation.controller.center_frame_controller import CenterFrameController

class ImageLabelingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CT Image Labeling Tool")
        self.root.geometry("1600x800")

        # 파일 및 이미지 관련 변수들
        self.file_list = []  # 로드된 파일 경로 목록
        self.current_file_path = None
        self.current_image = None  # 원본 이미지
        self.adjusted_image = None  # 명암/선명도 조정 후 이미지
        self.tmp_image = None  # 화면에 표시할 임시 이미지
        self.original_image_size = None
        self.current_image_size = None

        # Annotation 관련 변수들
        # { annotation_name: {"color": (B,G,R), "shapes": [shape_data, ...] } }
        self.annotations = {}
        self.annotations_per_file = {}
        self.file_settings = {}  # 파일별 슬라이더 설정 저장
        # drawing_mode: "polygon", "closed_curve", "ellipse"(생성 모드) 또는 "normal"(수정 모드)
        self.drawing_mode = None
        self.points = []  # 생성 모드 시 임시 점 리스트
        self.selected_annotation = None
        self.selected_shape_index = None

        # Normal 모드(수정) 관련 변수
        self.normal_mod_mode = None  # "move", "resize", "rotate" 또는 None
        self.normal_mod_vertex = None  # "top", "bottom", "left", "right" (resize 시)
        self.normal_mod_start_mouse = None  # 수정 시작 시 마우스 좌표 (x,y)
        self.normal_mod_start_params = None  # 수정 시작 시 타원 파라미터 (center, axes, angle)

        # 생성(그리기) 관련 변수
        self.is_drawing = False
        self.start_point = None  # 타원 생성 시작점

        self.is_updating_image = False

        self.left_frame = LeftFrame(root)
        self.left_controller = LeftFrameController(self, self.left_frame)
        self.right_frame = RightFrame(root)
        self.right_controller = RightFrameController(self, self.right_frame)
        self.center_frame = CenterFrame(root)
        self.center_controller = CenterFrameController(self, self.center_frame)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.add_files_via_drag_and_drop)

        self.root.bind("<Delete>", self.handle_delete_key)
        self.setup_shortcuts()  # 단축키 설정 추가
    

    def setup_shortcuts(self):
        # 단축키를 통해 모드 전환 (예: n: normal, e: ellipse, c: closed_curve, p: polygon)
        self.root.bind("<n>", lambda event: self.left_controller.set_drawing_mode("normal"))
        self.root.bind("<e>", lambda event: self.left_controller.set_drawing_mode("ellipse"))
        self.root.bind("<c>", lambda event: self.left_controller.set_drawing_mode("closed_curve"))


    def handle_delete_key(self, event):
        x, y = event.x_root, event.y_root
        widget_under = self.root.winfo_containing(x, y)
        if widget_under is None:
            return
        if self.is_descendant(widget_under, self.right_frame.file_listbox):
            self.delete_selected_file(event)
        elif self.is_descendant(widget_under, self.center_frame.image_panel):
            self.delete_selected_annotation(event)

        
    def delete_selected_file(self, event):
        selection = self.right_frame.file_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        file_to_remove = self.file_list[index]
        self.right_frame.file_listbox.delete(index)
        del self.file_list[index]
        print(f"Removed: {file_to_remove}")
        self.current_file_path = None
        self.current_image = None
        self.annotations.clear()
        self.right_frame.annotation_listbox.delete(0, tk.END)
        self.center_frame.image_panel.configure(image=None)
        print("Image panel and annotation list cleared.")


    def delete_selected_annotation(self, event=None):
        if self.selected_annotation is not None:
            del self.annotations[self.selected_annotation]["shapes"][self.selected_shape_index]
            if not self.annotations[self.selected_annotation]["shapes"]:
                del self.annotations[self.selected_annotation]
                for i in range(self.right_frame.annotation_listbox.size()):
                    if self.right_frame.annotation_listbox.get(i) == self.selected_annotation:
                        self.right_frame.annotation_listbox.delete(i)
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
        print(panel_size)
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

    def set_slider_value(self, value):
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

    def prompt_annotation_text(self, points, shape):
        popup = tk.Toplevel(self.root)
        popup.title("Select or Enter Annotation Text")
        popup.geometry("400x250")
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        popup_w, popup_h = 400, 250
        pos_x = main_x + (main_w - popup_w) // 2
        pos_y = main_y + (main_h - popup_h) // 2
        popup.geometry(f"{popup_w}x{popup_h}+{pos_x}+{pos_y}")
        popup.transient(self.root)
        popup.grab_set()
        popup.focus_force()
        popup.lift()

        label_font = ("Helvetica", 14, "bold")
        entry_font = ("Helvetica", 14)
        button_font = ("Helvetica", 12)
        label_existing = tk.Label(popup, text="Select existing annotation (or leave blank):", font=label_font)
        label_existing.pack(pady=5)
        existing = [self.right_frame.annotation_listbox.get(i) for i in range(self.right_frame.annotation_listbox.size())]
        if not existing:
            existing = ["No existing annotations"]
        selected_var = tk.StringVar(popup)
        selected_var.set(existing[0])
        option_menu = tk.OptionMenu(popup, selected_var, *existing)
        option_menu.config(font=entry_font)
        option_menu.pack(pady=5)
        label_new = tk.Label(popup, text="Or enter a new annotation name:", font=label_font)
        label_new.pack(pady=5)
        text_entry = tk.Entry(popup, width=30, font=entry_font)
        text_entry.pack(pady=5)
        text_entry.focus_set()

        def save_annotation():
            annotation_text = text_entry.get().strip()
            if annotation_text == "" or annotation_text == "No existing annotations":
                annotation_text = selected_var.get()
            if annotation_text and annotation_text != "No existing annotations":
                color = self.get_annotation_color(annotation_text)
                disp_w, disp_h = self.tmp_image.shape[1], self.tmp_image.shape[0]
                orig_w, orig_h = self.original_image_size
                scale_x = orig_w / disp_w
                scale_y = orig_h / disp_h

                if shape == "ellipse":
                    if isinstance(points, dict):
                        center = points["center"]
                        axes = points["axes"]
                        angle = points["angle"]
                        new_center = [center[0] * scale_x, center[1] * scale_y]
                        new_axes = [axes[0] * scale_x, axes[1] * scale_y]
                        new_shape_data = {
                            "shape": "ellipse",
                            "center": new_center,
                            "axes": new_axes,
                            "angle": angle,
                            "image_size": self.original_image_size
                        }
                    else:
                        pts = points
                        pt1 = (pts[0][0] * scale_x, pts[0][1] * scale_y)
                        pt2 = (pts[1][0] * scale_x, pts[1][1] * scale_y)
                        center = ((pt1[0] + pt2[0]) / 2, (pt1[1] + pt2[1]) / 2)
                        axes = (abs(pt2[0] - pt1[0]) / 2, abs(pt2[1] - pt1[1]) / 2)
                        angle = 0
                        new_shape_data = {
                            "shape": "ellipse",
                            "center": list(center),
                            "axes": list(axes),
                            "angle": angle,
                            "image_size": self.original_image_size
                        }
                    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                    cv2.ellipse(mask, tuple(map(int, new_shape_data["center"])),
                                tuple(map(int, new_shape_data["axes"])), new_shape_data["angle"], 0, 360, 255, -1)
                    _, buffer = cv2.imencode(".png", mask)
                    mask_base64 = base64.b64encode(buffer).decode("utf-8")
                    new_shape_data["mask"] = mask_base64
                else:
                    converted_points = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in points]
                    new_shape_data = {
                        "shape": shape,
                        "points": converted_points,
                        "image_size": self.original_image_size
                    }
                    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                    cv2.fillPoly(mask, [np.array(converted_points, dtype=np.int32)], color=255)
                    _, buffer = cv2.imencode(".png", mask)
                    mask_base64 = base64.b64encode(buffer).decode("utf-8")
                    new_shape_data["mask"] = mask_base64

                if annotation_text not in self.annotations:
                    self.annotations[annotation_text] = {"color": color, "shapes": []}
                    self.right_frame.annotation_listbox.insert(tk.END, annotation_text)
                self.annotations[annotation_text]["shapes"].append(new_shape_data)

            popup.destroy()
            self.update_display(apply_adjustments=False, redraw_annotations=True)

        def close_popup(event=None):
            popup.destroy()

        save_btn = tk.Button(popup, text="Save", command=save_annotation, font=button_font)
        save_btn.pack(pady=10)
        text_entry.bind("<Return>", lambda event: save_annotation())
        popup.bind("<Escape>", close_popup)
        popup.wait_window(popup)

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

    def clear_image_panel(self):
        self.center_controller

    def add_files_via_drag_and_drop(self, event):
        new_files = self.root.tk.splitlist(event.data)

        self.right_controller.add_files_via_drag_and_drop(new_files)