import tkinter as tk
from tkinter import filedialog, Listbox, messagebox, simpledialog
import cv2
import numpy as np
import pydicom
from PIL import Image, ImageTk
import json
import base64
import sys
import os
import subprocess
from math import atan2, degrees, hypot, radians, cos, sin
from tkinterdnd2 import DND_FILES, TkinterDnD

def init_tkdnd(root):
    try:
        root.tk.call('package', 'require', 'tkdnd')
        print("[INFO] tkdnd 패키지 로드 성공")
        root.tk.call('namespace', 'eval', '::tkdnd', '')
        print("[INFO] 네임스페이스 초기화 완료")
    except tk.TclError as e:
        print(f"[ERROR] tkdnd 초기화 실패: {e}")
        raise RuntimeError('Unable to load tkdnd library.')

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

        self.setup_gui()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


    def setup_gui(self):
        self.left_frame = tk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, padx=10, pady=10)
        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        self.center_frame = tk.Frame(self.root)
        self.center_frame.pack(side=tk.TOP, padx=10, pady=10, expand=True, fill=tk.BOTH)

        # 좌측 버튼들
        validation_btn = tk.Button(self.left_frame, text="Validation", command=self.run_validation)
        validation_btn.pack(anchor="nw", pady=5)
        save_json_btn = tk.Button(self.left_frame, text="Save Labels (JSON)", command=self.save_labels_to_json)
        save_json_btn.pack(anchor="nw", pady=5)
        # 모드 전환 버튼들을 저장
        self.btn_closed_curve = tk.Button(self.left_frame, text="Closed Curve",
                                          command=lambda: self.set_drawing_mode("closed_curve"))
        self.btn_closed_curve.pack(anchor="nw", pady=5)
        self.btn_ellipse = tk.Button(self.left_frame, text="Ellipse",
                                     command=lambda: self.set_drawing_mode("ellipse"))
        self.btn_ellipse.pack(anchor="nw", pady=5)
        self.btn_normal = tk.Button(self.left_frame, text="Normal Mode",
                                    command=lambda: self.set_drawing_mode("normal"))
        self.btn_normal.pack(anchor="nw", pady=5)

        # 슬라이더
        brightness_label = tk.Label(self.left_frame, text="Brightness")
        brightness_label.pack(anchor="nw", pady=2)
        self.brightness_slider = tk.Scale(self.left_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.update_adjusted_image)
        self.brightness_slider.set(50)
        self.brightness_slider.pack(anchor="nw", pady=5)
        sharpness_label = tk.Label(self.left_frame, text="Sharpness")
        sharpness_label.pack(anchor="nw", pady=2)
        self.sharpness_slider = tk.Scale(self.left_frame, from_=0, to=10, resolution=1, orient=tk.HORIZONTAL, command=self.update_adjusted_image)
        self.sharpness_slider.set(0)
        self.sharpness_slider.pack(anchor="nw", pady=5)
        reset_btn = tk.Button(self.left_frame, text="Reset Adjustments", command=self.reset_adjustments)
        reset_btn.pack(anchor="nw", pady=10)

        # 이미지 패널
        self.image_panel = tk.Label(self.center_frame)
        self.image_panel.pack(expand=True, fill=tk.BOTH)
        self.image_panel.bind("<Button-1>", self.on_mouse_click)
        self.image_panel.bind("<B1-Motion>", self.on_mouse_drag)
        self.image_panel.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.image_panel.bind("<Motion>", self.on_mouse_move)

        # Listbox들
        self.annotation_listbox = Listbox(self.right_frame, height=15, width=50)
        self.annotation_listbox.pack(anchor="ne", pady=5)
        self.annotation_listbox.bind("<Double-Button-1>", self.edit_annotation_name)
        self.file_listbox = Listbox(self.right_frame, height=10, width=50)
        self.file_listbox.pack(anchor="se", pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self.display_selected_image)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.add_files_via_drag_and_drop)
        load_files_btn = tk.Button(self.right_frame, text="Load Images", command=self.load_files)
        load_files_btn.pack(anchor="se", pady=5)

        self.root.bind("<Delete>", self.handle_delete_key)
        self.setup_shortcuts()  # 단축키 설정 추가

    def setup_shortcuts(self):
        # 단축키를 통해 모드 전환 (예: n: normal, e: ellipse, c: closed_curve, p: polygon)
        self.root.bind("<n>", lambda event: self.set_drawing_mode("normal"))
        self.root.bind("<e>", lambda event: self.set_drawing_mode("ellipse"))
        self.root.bind("<c>", lambda event: self.set_drawing_mode("closed_curve"))

    def set_drawing_mode(self, mode):
        self.drawing_mode = mode
        self.points = []
        self.is_drawing = False

        # 모든 버튼을 "raised" 상태로 초기화
        self.btn_closed_curve.config(relief="raised", bg="SystemButtonFace")
        self.btn_ellipse.config(relief="raised", bg="SystemButtonFace")
        self.btn_normal.config(relief="raised", bg="SystemButtonFace")


        # 선택된 모드의 버튼을 "sunken" 상태로 변경
        if mode == "closed_curve":
            self.btn_closed_curve.config(relief="sunken", bg="lightblue")
        elif mode == "ellipse":
            self.btn_ellipse.config(relief="sunken", bg="lightblue")
        elif mode == "normal":
            self.btn_normal.config(relief="sunken", bg="lightblue")

        if mode == "normal":
            self.normal_mod_mode = None
            self.normal_mod_vertex = None
            self.normal_mod_start_mouse = None
            self.normal_mod_start_params = None
        print(f"Drawing mode set to: {mode}")

    def handle_delete_key(self, event):
        x, y = event.x_root, event.y_root
        widget_under = self.root.winfo_containing(x, y)
        if widget_under is None:
            return
        if self.is_descendant(widget_under, self.file_listbox):
            self.delete_selected_file(event)
        elif self.is_descendant(widget_under, self.image_panel):
            self.delete_selected_annotation(event)

    def is_descendant(self, widget, parent):
        while widget is not None:
            if widget == parent:
                return True
            widget = widget.master
        return False

    def edit_annotation_name(self, event):
        selection = self.annotation_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        old_name = self.annotation_listbox.get(index)
        new_name = simpledialog.askstring("Rename Annotation", "Enter new annotation name:", initialvalue=old_name)
        if new_name and new_name.strip():
            new_name = new_name.strip()
            if new_name in self.annotations:
                messagebox.showerror("Error", "Annotation with this name already exists.")
                return
            self.annotations[new_name] = self.annotations.pop(old_name)
            self.annotation_listbox.delete(index)
            self.annotation_listbox.insert(index, new_name)
            print(f"Annotation renamed from {old_name} to {new_name}")

    def load_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.dcm"), ("All files", "*.*")])
        if file_paths:
            unsaved = {file: data for file, data in self.annotations_per_file.items() if data and not os.path.exists(os.path.splitext(file)[0] + ".json")}
            if unsaved:
                response = messagebox.askyesno("Warning", "There are unsaved annotations for some files. Do you want to discard them?")
                if response:
                    for file in unsaved.keys():
                        del self.annotations_per_file[file]
                    self.annotations.clear()
                    self.current_file_path = None
                    self.current_image = None
                    self.image_panel.configure(image=None)
                    self.annotation_listbox.delete(0, tk.END)
                    print("[INFO] Unsaved annotations discarded.")
                else:
                    print("[INFO] File load cancelled.")
                    return
            self.annotations_per_file.clear()
            self.annotations.clear()
            self.current_file_path = None
            self.current_image = None
            self.image_panel.configure(image=None)
            self.annotation_listbox.delete(0, tk.END)
            self.file_list = list(file_paths)
            self.file_listbox.delete(0, tk.END)
            for file in self.file_list:
                file_name = os.path.basename(file)
                json_file_path = os.path.splitext(file)[0] + ".json"
                if os.path.exists(json_file_path):
                    display_name = f"{file_name} ✅"
                    self.load_annotations_from_json(json_file_path)
                    self.annotations_per_file[file] = self.annotations.copy()
                else:
                    display_name = file_name
                self.file_listbox.insert(tk.END, display_name)
            if self.file_list:
                self.current_file_path = self.file_list[0]
                self.current_image = self.load_image(self.file_list[0])
                self.adjusted_image = self.current_image.copy()
                if self.current_file_path in self.file_settings:
                    settings = self.file_settings[self.current_file_path]
                    self.brightness_slider.set(settings["brightness"])
                    self.sharpness_slider.set(settings["sharpness"])
                else:
                    self.brightness_slider.set(50)
                    self.sharpness_slider.set(0)
                self.update_display(apply_adjustments=False, redraw_annotations=False)
            else:
                self.current_file_path = None
                self.current_image = None
                self.annotations.clear()
                self.image_panel.configure(image=None)
                self.annotation_listbox.delete(0, tk.END)
                print("No files loaded.")

    def add_files_via_drag_and_drop(self, event):
        new_files = self.root.tk.splitlist(event.data)
        for file in new_files:
            if file not in self.file_list:
                self.file_list.append(file)
                file_name = os.path.basename(file)
                json_file_path = os.path.splitext(file)[0] + ".json"
                display_name = f"{file_name} ✅" if os.path.exists(json_file_path) else file_name
                self.file_listbox.insert(tk.END, display_name)
        print(f"Files added via drag-and-drop: {new_files}")
        if self.file_list and self.current_image is None:
            self.current_file_path = self.file_list[0]
            self.current_image = self.load_image(self.current_file_path)
            self.adjusted_image = self.current_image.copy()
            json_file_path = os.path.splitext(self.current_file_path)[0] + ".json"
            if os.path.exists(json_file_path):
                print(f"[INFO] JSON file found for {self.current_file_path}")
                self.load_annotations_from_json(json_file_path)
            else:
                self.annotations.clear()
            self.annotation_listbox.delete(0, tk.END)
            for name in self.annotations.keys():
                self.annotation_listbox.insert(tk.END, name)
            self.update_display(apply_adjustments=False, redraw_annotations=True)

    def display_selected_image(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            file_path = self.file_list[selection[0]]
            if self.current_file_path:
                self.file_settings[self.current_file_path] = {
                    "brightness": self.brightness_slider.get(),
                    "sharpness": self.sharpness_slider.get()
                }
                self.annotations_per_file[self.current_file_path] = self.annotations.copy()
            self.current_file_path = file_path
            self.current_image = self.load_image(file_path)
            if self.current_image is None:
                print(f"Error: Failed to load {file_path}")
                return
            json_file_path = os.path.splitext(file_path)[0] + ".json"
            if os.path.exists(json_file_path):
                print(f"[INFO] JSON file found: {json_file_path}")
                try:
                    self.load_annotations_from_json(json_file_path)
                    self.annotations_per_file[file_path] = self.annotations.copy()
                except Exception as e:
                    print(f"[ERROR] Failed to load annotations from JSON: {e}")
            else:
                print(f"[INFO] No JSON file found for {file_path}")
                if file_path in self.annotations_per_file:
                    self.annotations = self.annotations_per_file[file_path].copy()
                    print(f"[INFO] Restored annotations from memory for {file_path}")
                else:
                    self.annotations.clear()
            self.annotation_listbox.delete(0, tk.END)
            for name in self.annotations.keys():
                self.annotation_listbox.insert(tk.END, name)
            if file_path in self.file_settings:
                settings = self.file_settings[file_path]
                self.brightness_slider.set(settings["brightness"])
                self.sharpness_slider.set(settings["sharpness"])
            else:
                self.brightness_slider.set(50)
                self.sharpness_slider.set(0)
            self.adjusted_image = self.current_image.copy()
            self.update_display(apply_adjustments=False, redraw_annotations=True)
        else:
            print("No file selected from the listbox.")

    def delete_selected_file(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        file_to_remove = self.file_list[index]
        self.file_listbox.delete(index)
        del self.file_list[index]
        print(f"Removed: {file_to_remove}")
        self.current_file_path = None
        self.current_image = None
        self.annotations.clear()
        self.annotation_listbox.delete(0, tk.END)
        self.image_panel.configure(image=None)
        print("Image panel and annotation list cleared.")

    def load_image(self, file_path):
        self.current_file_path = file_path
        if file_path.endswith(".dcm"):
            ds = pydicom.dcmread(file_path)
            img = ds.pixel_array
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        self.original_image_size = (img.shape[1], img.shape[0])
        return img

    def save_current_image(self):
        if self.current_image is not None:
            save_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                     filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")])
            if save_path:
                annotated_image = self.apply_annotations_to_original(self.current_image)
                cv2.imwrite(save_path, annotated_image)

    def apply_annotations_to_original(self, image):
        annotated_image = image.copy()
        for name, data in self.annotations.items():
            color = data["color"]
            for shape_data in data["shapes"]:
                if shape_data["shape"] == "ellipse":
                    if "center" in shape_data:
                        center = shape_data["center"]
                        axes = shape_data["axes"]
                        angle = shape_data["angle"]
                        cv2.ellipse(annotated_image, tuple(map(int, center)), tuple(map(int, axes)), angle, 0, 360, color, 2)
                    else:
                        pts = shape_data["points"]
                        center = ((pts[0][0] + pts[1][0]) // 2, (pts[0][1] + pts[1][1]) // 2)
                        axes = (abs(pts[1][0]-pts[0][0])//2, abs(pts[1][1]-pts[0][1])//2)
                        cv2.ellipse(annotated_image, center, axes, 0, 0, 360, color, 2)
                elif shape_data["shape"] in ["polygon", "closed_curve"]:
                    cv2.polylines(annotated_image, [np.array(shape_data["points"])], isClosed=(shape_data["shape"]=="polygon"),
                                  color=color, thickness=1)
        return annotated_image

    def load_annotations_from_json(self, json_file):
        try:
            with open(json_file, "r") as file:
                data = json.load(file)
                print(f"[INFO] Loaded JSON data from: {json_file}")
            self.annotations.clear()
            for annotation in data.get("annotations", []):
                name = annotation["name"]
                shape = annotation["shape"]
                color = tuple(annotation["color"])
                mask = annotation.get("mask")
                orig_size = annotation.get("orig_size", self.original_image_size)
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
                if name not in self.annotations:
                    self.annotations[name] = {"color": color, "shapes": []}
                    self.annotation_listbox.insert(tk.END, name)
                self.annotations[name]["shapes"].append(shape_data)
            print("[INFO] Annotations loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load JSON annotations: {e}")

    def save_labels_to_json(self):
        if not self.current_file_path:
            print("No file is currently loaded.")
            return
        json_file = os.path.splitext(self.current_file_path)[0] + ".json"
        if os.path.exists(json_file):
            response = messagebox.askyesno("Overwrite Confirmation",
                                           f"A file named '{os.path.basename(json_file)}' already exists. Do you want to overwrite it?")
            if not response:
                print("Save operation cancelled.")
                return
        self.annotations_per_file[self.current_file_path] = self.annotations.copy()
        label_data = {"file_path": [os.path.basename(self.current_file_path)], "annotations": []}
        orig_w, orig_h = self.original_image_size

        for name, data in self.annotations.items():
            for shape_data in data["shapes"]:
                if shape_data["shape"] == "ellipse" and "center" in shape_data:
                    # 만약 mask 키가 없다면 생성
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
                    # polygon, closed_curve, 또는 ellipse 구 방식인 경우
                    ann_size = shape_data["image_size"]
                    scale_x = orig_w / ann_size[0]
                    scale_y = orig_h / ann_size[1]
                    # 만약 "points" 키가 없는 경우(ellipse의 구 방식) mask를 생성하지 않음
                    if "points" in shape_data:
                        converted_points = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in shape_data["points"]]
                    else:
                        converted_points = []
                    # mask 생성
                    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                    if shape_data["shape"] in ["polygon", "closed_curve"]:
                        cv2.fillPoly(mask, [np.array(converted_points, dtype=np.int32)], color=255)
                    else:
                        # ellipse 구 방식: 두 점으로부터 생성
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
        self.file_listbox.delete(0, tk.END)
        for file in self.file_list:
            file_name = os.path.basename(file)
            json_file_path = os.path.splitext(file)[0] + ".json"
            display_name = f"{file_name} ✅" if os.path.exists(json_file_path) else file_name
            self.file_listbox.insert(tk.END, display_name)


    def adjust_brightness_and_sharpness(self, image, brightness=50, sharpness=0):
        if brightness != 50:
            brightness_scale = (brightness - 50) * 2.55
            image = cv2.convertScaleAbs(image, alpha=1, beta=int(brightness_scale))
        if sharpness > 0:
            kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]]) * sharpness
            high_pass = cv2.filter2D(image, -1, kernel)
            image = cv2.addWeighted(image, 1, high_pass, 1, 0)
        return image

    def reset_adjustments(self):
        self.brightness_slider.set(50)
        self.sharpness_slider.set(0)
        self.update_adjusted_image()

    def update_display(self, apply_adjustments=True, redraw_annotations=True):
        if self.current_image is None:
            self.tmp_image = None
            self.image_panel.configure(image=None)
            self.drawing_mode = None
            return
        if apply_adjustments:
            brightness = self.brightness_slider.get()
            sharpness = self.sharpness_slider.get()
            self.adjusted_image = self.adjust_brightness_and_sharpness(self.current_image, brightness, sharpness)
        panel_size = (self.image_panel.winfo_width(), self.image_panel.winfo_height())
        self.tmp_image = cv2.resize(self.adjusted_image, panel_size)
        if redraw_annotations:
            self.redraw_annotations()
        else:
            self.show_image()

    def update_adjusted_image(self, _=None):
        self.update_display(apply_adjustments=True, redraw_annotations=True)

    def resize_image(self, image, target_size):
        target_w, target_h = target_size
        resized = cv2.resize(image, (target_w, target_h))
        self.current_image_size = (target_w, target_h)
        return resized

    def show_image(self):
        if self.tmp_image is None:
            return
        img_rgb = cv2.cvtColor(self.tmp_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)
        self.image_panel.configure(image=img_tk)
        self.image_panel.image = img_tk

    def show_image_with_tmp(self, tmp_image):
        img_rgb = cv2.cvtColor(tmp_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)
        self.image_panel.configure(image=img_tk)
        self.image_panel.image = img_tk

    def highlight_selected_annotation(self, annotation_name, shape_index):
        try:
            # 원본 -> 디스플레이 scale factor 계산
            disp_w, disp_h = self.image_panel.winfo_width(), self.image_panel.winfo_height()
            orig_w, orig_h = self.original_image_size
            scale_x = disp_w / orig_w
            scale_y = disp_h / orig_h

            # base_img는 현재 조정된 이미지(self.adjusted_image)를 디스플레이 크기로 리사이즈한 이미지입니다.
            base_img = cv2.resize(self.adjusted_image, (disp_w, disp_h))
            overlay = base_img.copy()
            color = self.annotations[annotation_name]["color"]
            shape_data = self.annotations[annotation_name]["shapes"][shape_index]

            if shape_data["shape"] == "ellipse":
                if "center" in shape_data:
                    center = shape_data["center"]
                    axes = shape_data["axes"]
                    angle = shape_data["angle"]
                    disp_center = (int(center[0] * scale_x), int(center[1] * scale_y))
                    disp_axes = (int(axes[0] * scale_x), int(axes[1] * scale_y))
                    mask = np.zeros(overlay.shape, dtype=np.uint8)
                    cv2.ellipse(mask, disp_center, disp_axes, angle, 0, 360, (255, 255, 255), -1)
                else:
                    pts = shape_data["points"]
                    disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in pts]
                    mask = np.zeros(overlay.shape, dtype=np.uint8)
                    cv2.ellipse(mask, ((disp_pts[0][0] + disp_pts[1][0]) // 2, (disp_pts[0][1] + disp_pts[1][1]) // 2),
                                (abs(disp_pts[1][0] - disp_pts[0][0]) // 2, abs(disp_pts[1][1] - disp_pts[0][1]) // 2),
                                0, 0, 360, (255, 255, 255), -1)
            else:
                pts = shape_data["points"]
                disp_pts = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in pts]
                mask = np.zeros(overlay.shape, dtype=np.uint8)
                cv2.fillPoly(mask, [np.array(disp_pts, dtype=np.int32)], (255, 255, 255))

            # 컬러 오버레이 생성
            color_overlay = np.full(overlay.shape, color, dtype=np.uint8)
            mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            mask_norm = mask_gray.astype(float) / 255.0

            # base_img를 그대로 유지하면서 하이라이트 효과 적용
            highlighted = base_img.copy()
            for c in range(3):
                highlighted[:, :, c] = highlighted[:, :, c] * (1 - 0.3 * mask_norm) + color_overlay[:, :, c] * (
                            0.3 * mask_norm)

            # self.tmp_image를 직접 수정하지 않고, highlighted 이미지를 화면에 표시합니다.
            self.show_image_with_tmp(highlighted)
        except Exception as e:
            print(f"[DEBUG] Error in highlight_selected_annotation: {e}")

    def on_mouse_click(self, event):
        if self.current_image is None:
            print("No image loaded. Annotation is disabled.")
            return
        x, y = int(event.x), int(event.y)
        if self.drawing_mode == "polygon":
            self.handle_polygon(x, y)
        elif self.drawing_mode == "closed_curve":
            self.is_drawing = True
            self.points = [(x, y)]
        elif self.drawing_mode == "ellipse":
            self.start_point = (x, y)
            self.is_drawing = True
        elif self.drawing_mode == "normal":
            if self.selected_annotation is None:
                return
            shape_data = self.annotations[self.selected_annotation]["shapes"][self.selected_shape_index]
            if shape_data["shape"] != "ellipse":
                return
            # 만약 "center"가 없다면, 원래 두 점으로부터 계산 (수정 모드 시작 전에 원본 좌표로 변환)
            if "center" not in shape_data:
                pts = shape_data["points"]
                center = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
                axes = (abs(pts[1][0] - pts[0][0]) / 2, abs(pts[1][1] - pts[0][1]) / 2)
                angle = 0
                shape_data["center"] = center
                shape_data["axes"] = axes
                shape_data["angle"] = angle
            # 기존 원본 좌표 (annotation 데이터는 원본 기준)
            orig_center, orig_axes, angle = shape_data["center"], shape_data["axes"], shape_data["angle"]
            # 화면 scale factor: 원본 -> display
            disp_w, disp_h = self.image_panel.winfo_width(), self.image_panel.winfo_height()
            orig_w, orig_h = self.original_image_size
            scale_x = disp_w / orig_w
            scale_y = disp_h / orig_h
            # 변환한 디스플레이 좌표
            disp_center = (orig_center[0] * scale_x, orig_center[1] * scale_y)
            disp_axes = (orig_axes[0] * scale_x, orig_axes[1] * scale_y)
            # 디스플레이 좌표 기준으로 타원 꼭짓점 계산
            vertices = self.compute_ellipse_vertices(disp_center, disp_axes, angle)
            click_pt = np.array([x, y])
            threshold = 10
            for vertex_label, vertex in vertices.items():
                dist = np.linalg.norm(click_pt - np.array(vertex))
                if dist < threshold:
                    self.normal_mod_mode = "resize"
                    self.normal_mod_vertex = vertex_label
                    # 저장하는 start 값은 원본 좌표
                    self.normal_mod_start_mouse = (x, y)
                    self.normal_mod_start_params = (orig_center, orig_axes, angle)
                    print(f"Normal mode: resize started at {vertex_label}")
                    return
            # Rotate 모드: top vertex 근처 (디스플레이 좌표)
            top_vertex = vertices["top"]
            dist_top = np.linalg.norm(click_pt - np.array(top_vertex))
            if threshold < dist_top < 2 * threshold:
                self.normal_mod_mode = "rotate"
                self.normal_mod_start_mouse = (x, y)
                self.normal_mod_start_params = (orig_center, orig_axes, angle)
                print("Normal mode: rotate started")
                return
            # Move 모드: 클릭이 타원 내부 (디스플레이 좌표)
            if self.point_in_rotated_ellipse(x, y, disp_center, disp_axes, angle):
                self.normal_mod_mode = "move"
                self.normal_mod_start_mouse = (x, y)
                self.normal_mod_start_params = (orig_center, orig_axes, angle)
                print("Normal mode: move started")
                return

    def on_mouse_drag(self, event):
        x, y = int(event.x), int(event.y)
        if self.drawing_mode == "ellipse" and self.is_drawing:
            tmp_copy = self.tmp_image.copy()
            end_point = (x, y)
            center = ((self.start_point[0] + end_point[0]) // 2, (self.start_point[1] + end_point[1]) // 2)
            axes = (abs(end_point[0] - self.start_point[0]) // 2, abs(end_point[1] - self.start_point[1]) // 2)
            cv2.ellipse(tmp_copy, center, axes, 0, 0, 360, (255, 0, 0), 1)
            self.show_image_with_tmp(tmp_copy)
        elif self.drawing_mode == "closed_curve" and self.is_drawing:
            self.points.append((x, y))
            tmp_copy = self.tmp_image.copy()
            cv2.polylines(tmp_copy, [np.array(self.points)], isClosed=False, color=(0, 255, 255), thickness=1)
            self.show_image_with_tmp(tmp_copy)
        elif self.drawing_mode == "normal" and self.normal_mod_mode is not None:
            # 원본 좌표 기준으로 수정: 화면에서 이동한 delta를 원본 좌표 delta로 변환
            disp_w, disp_h = self.image_panel.winfo_width(), self.image_panel.winfo_height()
            orig_w, orig_h = self.original_image_size
            scale_x = orig_w / disp_w
            scale_y = orig_h / disp_h
            dx_disp = x - self.normal_mod_start_mouse[0]
            dy_disp = y - self.normal_mod_start_mouse[1]
            dx_orig = dx_disp * scale_x
            dy_orig = dy_disp * scale_y
            init_center, init_axes, init_angle = self.normal_mod_start_params
            if self.normal_mod_mode == "move":
                new_center = (init_center[0] + dx_orig, init_center[1] + dy_orig)
                new_axes = init_axes
                new_angle = init_angle
            elif self.normal_mod_mode == "resize":
                new_center = init_center
                new_axes = list(init_axes)
                if self.normal_mod_vertex in ["left", "right"]:
                    new_a = max(5, init_axes[0] + (dx_orig if self.normal_mod_vertex == "right" else -dx_orig))
                    new_axes[0] = new_a
                elif self.normal_mod_vertex in ["top", "bottom"]:
                    new_b = max(5, init_axes[1] + (dy_orig if self.normal_mod_vertex == "bottom" else -dy_orig))
                    new_axes[1] = new_b
                new_axes = tuple(new_axes)
                new_angle = init_angle
            elif self.normal_mod_mode == "rotate":
                # 회전의 경우는 화면 좌표에서 계산한 각도 차이를 원본 각도에 더합니다.
                angle_start = degrees(atan2(self.normal_mod_start_mouse[1] - (init_center[1] / scale_y),
                                             self.normal_mod_start_mouse[0] - (init_center[0] / scale_x)))
                angle_now = degrees(atan2(y - (init_center[1] * (disp_h/orig_h)),
                                           x - (init_center[0] * (disp_w/orig_w))))
                new_angle = init_angle + (angle_now - angle_start)
                new_center = init_center
                new_axes = init_axes
            updated_data = {"shape": "ellipse", "center": new_center, "axes": new_axes, "angle": new_angle,
                            "image_size": self.original_image_size}
            self.annotations[self.selected_annotation]["shapes"][self.selected_shape_index] = updated_data
            self.update_display(apply_adjustments=False, redraw_annotations=True)


    def on_mouse_release(self, event):
        x, y = int(event.x), int(event.y)
        if self.drawing_mode == "ellipse" and self.is_drawing:
            end_point = (x,y)
            self.handle_ellipse(self.start_point, end_point)
            self.prompt_annotation_text([self.start_point, end_point], shape="ellipse")
            self.start_point = None
            self.is_drawing = False
        elif self.drawing_mode == "polygon" and len(self.points) > 1:
            self.points.append(self.points[0])
            self.prompt_annotation_text(self.points, shape="polygon")
            self.points = []
        elif self.drawing_mode == "closed_curve" and self.is_drawing:
            self.points.append((x,y))
            if len(self.points) > 1 and self.points[0] != self.points[-1]:
                self.points.append(self.points[0])
            self.prompt_annotation_text(self.points, shape="closed_curve")
            self.is_drawing = False
        elif self.drawing_mode == "normal":
            self.normal_mod_mode = None
            self.normal_mod_vertex = None
            self.normal_mod_start_mouse = None
            self.normal_mod_start_params = None

    def on_mouse_move(self, event):
        if self.tmp_image is None or self.adjusted_image is None:
            return
        panel_w, panel_h = self.image_panel.winfo_width(), self.image_panel.winfo_height()
        cursor_x, cursor_y = int(event.x), int(event.y)
        new_sel_name = None
        new_sel_index = None
        for name, data in self.annotations.items():
            for idx, shape_data in enumerate(data["shapes"]):
                shape = shape_data["shape"]
                if shape == "ellipse":
                    if "center" in shape_data:
                        center = shape_data["center"]
                        axes = shape_data["axes"]
                        angle = shape_data["angle"]
                        # 변환: 원본 -> 디스플레이
                        disp_center = (int(center[0] * (panel_w / self.original_image_size[0])),
                                       int(center[1] * (panel_h / self.original_image_size[1])))
                        disp_axes = (int(axes[0] * (panel_w / self.original_image_size[0])),
                                     int(axes[1] * (panel_h / self.original_image_size[1])))
                        if self.point_in_rotated_ellipse(cursor_x, cursor_y, disp_center, disp_axes, angle):
                            new_sel_name = name
                            new_sel_index = idx
                            break
                    else:
                        pts = shape_data["points"]
                        disp_pts = [(int(pt[0] * (panel_w / self.original_image_size[0])), int(pt[1] * (panel_h / self.original_image_size[1]))) for pt in pts]
                        center = ((disp_pts[0][0] + disp_pts[1][0])//2, (disp_pts[0][1] + disp_pts[1][1])//2)
                        axes = (abs(disp_pts[1][0]-disp_pts[0][0])//2, abs(disp_pts[1][1]-disp_pts[0][1])//2)
                        if self.is_point_in_ellipse(cursor_x, cursor_y, center, axes):
                            new_sel_name = name
                            new_sel_index = idx
                            break
                elif shape in ["polygon", "closed_curve"]:
                    pts = shape_data["points"]
                    disp_pts = [(int(pt[0] * (panel_w / self.original_image_size[0])), int(pt[1] * (panel_h / self.original_image_size[1]))) for pt in pts]
                    if self.is_point_in_polygon(cursor_x, cursor_y, disp_pts):
                        new_sel_name = name
                        new_sel_index = idx
                        break
            if new_sel_name:
                break
        if new_sel_name is not None:
            self.selected_annotation = new_sel_name
            self.selected_shape_index = new_sel_index
            self.highlight_selected_annotation(new_sel_name, new_sel_index)
        else:
            self.update_display(apply_adjustments=False, redraw_annotations=True)

    def is_point_in_polygon(self, x, y, points):
        poly = np.array(points, dtype=np.int32)
        return cv2.pointPolygonTest(poly, (x, y), False) >= 0

    def is_point_in_ellipse(self, x, y, center, axes):
        a, b = axes
        if a == 0 or b == 0:
            return False
        return ((x - center[0])**2)/(a**2) + ((y - center[1])**2)/(b**2) <= 1

    def handle_ellipse(self, start, end):
        center = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        axes = (abs(end[0]-start[0])//2, abs(end[1]-start[1])//2)
        cv2.ellipse(self.tmp_image, center, axes, 0, 0, 360, (255,0,0), 1)
        self.show_image()

    def handle_ellipse_creation(self, center, axes, angle):
        self.prompt_annotation_text({"center": center, "axes": axes, "angle": angle}, shape="ellipse")

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
        existing = [self.annotation_listbox.get(i) for i in range(self.annotation_listbox.size())]
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
                    self.annotation_listbox.insert(tk.END, annotation_text)
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

    def get_current_annotation_image_size(self):
        return (self.tmp_image.shape[1], self.tmp_image.shape[0]) if self.tmp_image is not None else (0, 0)

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
        disp_w, disp_h = self.image_panel.winfo_width(), self.image_panel.winfo_height()
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

    def delete_selected_annotation(self, event=None):
        if self.selected_annotation is not None:
            del self.annotations[self.selected_annotation]["shapes"][self.selected_shape_index]
            if not self.annotations[self.selected_annotation]["shapes"]:
                del self.annotations[self.selected_annotation]
                for i in range(self.annotation_listbox.size()):
                    if self.annotation_listbox.get(i) == self.selected_annotation:
                        self.annotation_listbox.delete(i)
                        break
            self.selected_annotation = None
            self.selected_shape_index = None
            self.update_display(apply_adjustments=False, redraw_annotations=True)

    def run_validation(self):
        try:
            script_path = self.resource_path("Taemu_Validation.py")
            subprocess.run([sys.executable, script_path], check=True)
            print("Validation completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Validation script failed: {e}")
        finally:
            self.is_drawing = False
            self.start_point = None
            self.points = []
            self.drawing_mode = None
            print("Annotation mode reset.")

    class AnnotationMaskGenerator:
        def __init__(self, annotations):
            self.annotations = annotations

        def create_mask(self, image_size):
            mask = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)
            for name, data in self.annotations.items():
                color = tuple(data["color"])
                for shape_data in data["shapes"]:
                    pts = np.array(shape_data["points"], dtype=np.int32)
                    shape = shape_data["shape"]
                    if shape in ["polygon", "closed_curve"]:
                        cv2.fillPoly(mask, [pts], color=color)
                    elif shape == "ellipse":
                        pts = shape_data["points"]
                        center = ((pts[0][0] + pts[1][0]) // 2, (pts[0][1] + pts[1][1]) // 2)
                        axes = (abs(pts[1][0]-pts[0][0])//2, abs(pts[1][1]-pts[0][1])//2)
                        cv2.ellipse(mask, center, axes, 0, 0, 360, color=color, thickness=-1)
            return mask

    def on_mouse_move(self, event):
        if self.tmp_image is None or self.adjusted_image is None:
            return
        panel_w, panel_h = self.image_panel.winfo_width(), self.image_panel.winfo_height()
        cursor_x, cursor_y = int(event.x), int(event.y)
        new_sel_name = None
        new_sel_index = None
        for name, data in self.annotations.items():
            for idx, shape_data in enumerate(data["shapes"]):
                shape = shape_data["shape"]
                if shape == "ellipse":
                    if "center" in shape_data:
                        center = shape_data["center"]
                        axes = shape_data["axes"]
                        angle = shape_data["angle"]
                        disp_center = (int(center[0] * (panel_w/self.original_image_size[0])),
                                       int(center[1] * (panel_h/self.original_image_size[1])))
                        disp_axes = (int(axes[0] * (panel_w/self.original_image_size[0])),
                                     int(axes[1] * (panel_h/self.original_image_size[1])))
                        if self.point_in_rotated_ellipse(cursor_x, cursor_y, disp_center, disp_axes, angle):
                            new_sel_name = name
                            new_sel_index = idx
                            break
                    else:
                        pts = shape_data["points"]
                        disp_pts = [(int(pt[0] * (panel_w/self.original_image_size[0])), int(pt[1] * (panel_h/self.original_image_size[1]))) for pt in pts]
                        center = ((disp_pts[0][0]+disp_pts[1][0])//2, (disp_pts[0][1]+disp_pts[1][1])//2)
                        axes = (abs(disp_pts[1][0]-disp_pts[0][0])//2, abs(disp_pts[1][1]-disp_pts[0][1])//2)
                        if self.is_point_in_ellipse(cursor_x, cursor_y, center, axes):
                            new_sel_name = name
                            new_sel_index = idx
                            break
                elif shape in ["polygon", "closed_curve"]:
                    pts = shape_data["points"]
                    disp_pts = [(int(pt[0] * (panel_w/self.original_image_size[0])), int(pt[1] * (panel_h/self.original_image_size[1]))) for pt in pts]
                    if self.is_point_in_polygon(cursor_x, cursor_y, disp_pts):
                        new_sel_name = name
                        new_sel_index = idx
                        break
            if new_sel_name:
                break
        if new_sel_name is not None:
            self.selected_annotation = new_sel_name
            self.selected_shape_index = new_sel_index
            self.highlight_selected_annotation(new_sel_name, new_sel_index)
        else:
            self.update_display(apply_adjustments=False, redraw_annotations=True)

    def is_point_in_ellipse(self, x, y, center, axes):
        a, b = axes
        if a == 0 or b == 0:
            return False
        return ((x - center[0])**2)/(a**2) + ((y - center[1])**2)/(b**2) <= 1

    def point_in_rotated_ellipse(self, x, y, center, axes, angle):
        theta = radians(angle)
        dx = x - center[0]
        dy = y - center[1]
        xr = dx * cos(theta) + dy * sin(theta)
        yr = -dx * sin(theta) + dy * cos(theta)
        a, b = axes
        return (xr**2)/(a**2) + (yr**2)/(b**2) <= 1

    def compute_ellipse_vertices(self, center, axes, angle):
        a, b = axes
        theta = radians(angle)
        cx, cy = center
        top = (cx, cy - b)
        bottom = (cx, cy + b)
        left = (cx - a, cy)
        right = (cx + a, cy)
        def rotate(pt):
            x, y = pt
            rx = x - cx
            ry = y - cy
            new_x = rx * cos(theta) - ry * sin(theta) + cx
            new_y = rx * sin(theta) + ry * cos(theta) + cy
            return (int(new_x), int(new_y))
        return {"top": rotate(top), "bottom": rotate(bottom),
                "left": rotate(left), "right": rotate(right)}

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    init_tkdnd(root)
    app = ImageLabelingApp(root)
    root.mainloop()
