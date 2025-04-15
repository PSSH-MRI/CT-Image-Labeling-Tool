import numpy as np
import cv2
from math import atan2, degrees, radians, sin, cos

from view.center_frame import CenterFrame
from controller.annotation_save_popup import AnnotationSavePopup


class CenterFrameController:
    def __init__(self, master, root):
        self.master = master
        self.root = root
        self.view = CenterFrame(root)
        self.setup_ui_event()


    def setup_ui_event(self):
        # Events
        self.view.image_panel.bind("<Button-1>", self.click_on_image)
        self.view.image_panel.bind("<B1-Motion>", self.drag_on_image)
        self.view.image_panel.bind("<ButtonRelease-1>", self.end_drag_on_image)
        self.view.image_panel.bind("<Motion>", self.move_on_image)


    @property
    def get_image_panel(self):
        return self.view.image_panel


    def get_image_panel_size(self):
        return (self.view.image_panel.winfo_width(), self.view.image_panel.winfo_height())
    


    def show_in_image_panel(self, img):
        self.view.image_panel.configure(image=img)
        self.view.image_panel.image = img


    def clear_image_panel(self):
        self.view.image_panel.configure(image=None)


    def click_on_image(self, event):
        if self.master.current_image is None:
            print("No image loaded. Annotation is disabled.")
            return
        x, y = int(event.x), int(event.y)
        if self.master.drawing_mode == "closed_curve":
            self.master.is_drawing = True
            self.master.points = [(x, y)]
        elif self.master.drawing_mode == "ellipse":
            self.master.start_point = (x, y)
            self.master.is_drawing = True
        elif self.master.drawing_mode == "normal":
            if self.master.selected_annotation is None:
                return
            shape_data = self.master.annotations[self.master.selected_annotation]["shapes"][self.master.selected_shape_index]
            
            if shape_data["shape"] != "ellipse":
                return
            
            if "center" not in shape_data:
                pts = shape_data["points"]
                center = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
                axes = (abs(pts[1][0] - pts[0][0]) / 2, abs(pts[1][1] - pts[0][1]) / 2)
                angle = 0
                shape_data["center"] = center
                shape_data["axes"] = axes
                shape_data["angle"] = angle

            orig_center, orig_axes, angle = shape_data["center"], shape_data["axes"], shape_data["angle"]
            disp_w, disp_h = self.master.get_image_panel_size()
            orig_w, orig_h = self.master.original_image_size
            scale_x = disp_w / orig_w
            scale_y = disp_h / orig_h
            disp_center = (orig_center[0] * scale_x, orig_center[1] * scale_y)
            disp_axes = (orig_axes[0] * scale_x, orig_axes[1] * scale_y)
            vertices = self.compute_ellipse_vertices(disp_center, disp_axes, angle)
            click_pt = np.array([x, y])
            threshold = 10
            
            for vertex_label, vertex in vertices.items():
                dist = np.linalg.norm(click_pt - np.array(vertex))
                if dist < threshold:
                    self.master.normal_mod_mode = "resize"
                    self.master.normal_mod_vertex = vertex_label

                    self.master.normal_mod_start_mouse = (x, y)
                    self.master.normal_mod_start_params = (orig_center, orig_axes, angle)
                    print(f"Normal mode: resize started at {vertex_label}")
                    return

            top_vertex = vertices["top"]
            dist_top = np.linalg.norm(click_pt - np.array(top_vertex))
            
            if threshold < dist_top < 2 * threshold:
                self.master.normal_mod_mode = "rotate"
                self.master.normal_mod_start_mouse = (x, y)
                self.master.normal_mod_start_params = (orig_center, orig_axes, angle)
                print("Normal mode: rotate started")
                return

            if self.point_in_rotated_ellipse(x, y, disp_center, disp_axes, angle):
                self.master.normal_mod_mode = "move"
                self.master.normal_mod_start_mouse = (x, y)
                self.master.normal_mod_start_params = (orig_center, orig_axes, angle)
                print("Normal mode: move started")
                return
            


    def drag_on_image(self, event):
            x, y = int(event.x), int(event.y)
            
            if self.master.drawing_mode == "ellipse" and self.master.is_drawing:
                tmp_copy = self.master.tmp_image.copy()
                end_point = (x, y)
                center = ((self.master.start_point[0] + end_point[0]) // 2, (self.master.start_point[1] + end_point[1]) // 2)
                axes = (abs(end_point[0] - self.master.start_point[0]) // 2, abs(end_point[1] - self.master.start_point[1]) // 2)
                cv2.ellipse(tmp_copy, center, axes, 0, 0, 360, (255, 0, 0), 1)
                self.master.show_image_with_tmp(tmp_copy)
            elif self.master.drawing_mode == "closed_curve" and self.master.is_drawing:
                self.master.points.append((x, y))
                tmp_copy = self.master.tmp_image.copy()
                cv2.polylines(tmp_copy, [np.array(self.master.points)], isClosed=False, color=(0, 255, 255), thickness=1)
                self.master.show_image_with_tmp(tmp_copy)
            elif self.master.drawing_mode == "normal" and self.master.normal_mod_mode is not None:
                disp_w, disp_h = self.master.get_image_panel_size()
                orig_w, orig_h = self.master.original_image_size
                scale_x = orig_w / disp_w
                scale_y = orig_h / disp_h
                dx_disp = x - self.master.normal_mod_start_mouse[0]
                dy_disp = y - self.master.normal_mod_start_mouse[1]
                dx_orig = dx_disp * scale_x
                dy_orig = dy_disp * scale_y
                init_center, init_axes, init_angle = self.master.normal_mod_start_params
                if self.master.normal_mod_mode == "move":
                    new_center = (init_center[0] + dx_orig, init_center[1] + dy_orig)
                    new_axes = init_axes
                    new_angle = init_angle
                elif self.master.normal_mod_mode == "resize":
                    new_center = init_center
                    new_axes = list(init_axes)
                    if self.master.normal_mod_vertex in ["left", "right"]:
                        new_a = max(5, init_axes[0] + (dx_orig if self.master.normal_mod_vertex == "right" else -dx_orig))
                        new_axes[0] = new_a
                    elif self.master.normal_mod_vertex in ["top", "bottom"]:
                        new_b = max(5, init_axes[1] + (dy_orig if self.master.normal_mod_vertex == "bottom" else -dy_orig))
                        new_axes[1] = new_b
                    new_axes = tuple(new_axes)
                    new_angle = init_angle
                elif self.master.normal_mod_mode == "rotate":
                    angle_start = degrees(atan2(self.master.normal_mod_start_mouse[1] - (init_center[1] / scale_y),
                                                self.master.normal_mod_start_mouse[0] - (init_center[0] / scale_x)))
                    angle_now = degrees(atan2(y - (init_center[1] * (disp_h/orig_h)),
                                            x - (init_center[0] * (disp_w/orig_w))))
                    new_angle = init_angle + (angle_now - angle_start)
                    new_center = init_center
                    new_axes = init_axes
                    
                updated_data = {"shape": "ellipse", "center": new_center, "axes": new_axes, "angle": new_angle,
                                "image_size": self.master.original_image_size}
                
                self.master.annotations[self.master.selected_annotation]["shapes"][self.master.selected_shape_index] = updated_data
                self.master.update_display()


    def end_drag_on_image(self, event):
        x, y = int(event.x), int(event.y)
        if self.master.drawing_mode == "ellipse" and self.master.is_drawing:
            end_point = (x,y)
            self.master.handle_ellipse(self.master.start_point, end_point)
            
            AnnotationSavePopup(
                root=self.root,
                app=self.master,
                points=[self.master.start_point, end_point],
                shape="ellipse"
            )
            
            self.master.start_point = None
            self.master.is_drawing = False
        elif self.master.drawing_mode == "polygon" and len(self.master.points) > 1:
            self.master.points.append(self.master.points[0])
            
            AnnotationSavePopup(
                root=self.root,
                app=self.master,
                points=self.master.points,
                shape="polygon"
            )
            
            self.master.points = []
        elif self.master.drawing_mode == "closed_curve" and self.master.is_drawing:
            self.master.points.append((x,y))
            if len(self.master.points) > 1 and self.master.points[0] != self.master.points[-1]:
                self.master.points.append(self.master.points[0])
            
            AnnotationSavePopup(
                root=self.root,
                app=self.master,
                points=self.master.points,
                shape="closed_curve"
            )
            
            self.master.is_drawing = False
        elif self.master.drawing_mode == "normal":
            self.master.normal_mod_mode = None
            self.master.normal_mod_vertex = None
            self.master.normal_mod_start_mouse = None
            self.master.normal_mod_start_params = None


    def move_on_image(self, event):
        if self.master.tmp_image is None or self.master.adjusted_image is None:
            return
        
        panel_w, panel_h = self.master.get_image_panel_size()
        cursor_x, cursor_y = int(event.x), int(event.y)
        new_sel_name = None
        new_sel_index = None
        
        for name, data in self.master.annotations.items():
            for idx, shape_data in enumerate(data["shapes"]):
                shape = shape_data["shape"]
                if shape == "ellipse":
                    if "center" in shape_data:
                        center = shape_data["center"]
                        axes = shape_data["axes"]
                        angle = shape_data["angle"]
                        # 변환: 원본 -> 디스플레이
                        disp_center = (int(center[0] * (panel_w / self.master.original_image_size[0])),
                                       int(center[1] * (panel_h / self.master.original_image_size[1])))
                        disp_axes = (int(axes[0] * (panel_w / self.master.original_image_size[0])),
                                     int(axes[1] * (panel_h / self.master.original_image_size[1])))
                        if self.point_in_rotated_ellipse(cursor_x, cursor_y, disp_center, disp_axes, angle):
                            new_sel_name = name
                            new_sel_index = idx
                            break
                    else:
                        pts = shape_data["points"]
                        disp_pts = [(int(pt[0] * (panel_w / self.master.original_image_size[0])), int(pt[1] * (panel_h / self.master.original_image_size[1]))) for pt in pts]
                        center = ((disp_pts[0][0] + disp_pts[1][0])//2, (disp_pts[0][1] + disp_pts[1][1])//2)
                        axes = (abs(disp_pts[1][0]-disp_pts[0][0])//2, abs(disp_pts[1][1]-disp_pts[0][1])//2)
                        if self.is_point_in_ellipse(cursor_x, cursor_y, center, axes):
                            new_sel_name = name
                            new_sel_index = idx
                            break
                elif shape in ["polygon", "closed_curve"]:
                    pts = shape_data["points"]
                    disp_pts = [(int(pt[0] * (panel_w / self.master.original_image_size[0])), int(pt[1] * (panel_h / self.master.original_image_size[1]))) for pt in pts]
                    if self.is_point_in_polygon(cursor_x, cursor_y, disp_pts):
                        new_sel_name = name
                        new_sel_index = idx
                        break
            if new_sel_name:
                break
            
        if new_sel_name is not None:
            self.master.selected_annotation = new_sel_name
            self.master.selected_shape_index = new_sel_index
            self.highlight_selected_annotation(new_sel_name, new_sel_index)
        else:
            self.master.update_display(apply_adjustments=False, redraw_annotations=True)


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
    
    
    def is_point_in_polygon(self, x, y, points):
        poly = np.array(points, dtype=np.int32)
        return cv2.pointPolygonTest(poly, (x, y), False) >= 0


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


    def highlight_selected_annotation(self, annotation_name, shape_index):
        try:
            disp_w, disp_h = self.master.get_image_panel_size()
            orig_w, orig_h = self.master.original_image_size
            scale_x = disp_w / orig_w
            scale_y = disp_h / orig_h

            base_img = cv2.resize(self.master.adjusted_image, (disp_w, disp_h))
            overlay = base_img.copy()
            color = self.master.annotations[annotation_name]["color"]
            shape_data = self.master.annotations[annotation_name]["shapes"][shape_index]

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

            color_overlay = np.full(overlay.shape, color, dtype=np.uint8)
            mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            mask_norm = mask_gray.astype(float) / 255.0

            highlighted = base_img.copy()
            for c in range(3):
                highlighted[:, :, c] = highlighted[:, :, c] * (1 - 0.3 * mask_norm) + color_overlay[:, :, c] * (
                            0.3 * mask_norm)

            self.master.show_image_with_tmp(highlighted)
        except Exception as e:
            print(f"[DEBUG] Error in highlight_selected_annotation: {e}")

