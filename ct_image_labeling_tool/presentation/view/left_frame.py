import tkinter as tk


"""
Widget Type의 프로퍼티를 가지고 있고, 뷰 갱신 등의 동작만 할 수 있도록
"""
class LeftFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(side=tk.LEFT, padx=10, pady=10)
        self.setup_gui()

    def setup_gui(self):
        # 유틸 버튼
        self.validation_btn = tk.Button(self, text="Validation")
        self.validation_btn.pack(anchor="nw", pady=5)
        self.save_json_btn = tk.Button(self, text="Save Labels (JSON)")
        self.save_json_btn.pack(anchor="nw", pady=5)

        # 모드 전환 버튼
        self.closed_curve_btn = tk.Button(self, text="Closed Curve")
        self.closed_curve_btn.pack(anchor="nw", pady=5)
        self.ellipse_btn = tk.Button(self, text="Ellipse")
        self.ellipse_btn.pack(anchor="nw", pady=5)
        self.normal_btn = tk.Button(self, text="Normal Mode")
        self.normal_btn.pack(anchor="nw", pady=5)

        # Image Filtering
        self.brightness_label = tk.Label(self, text="Brightness")
        self.brightness_label.pack(anchor="nw", pady=2)
        self.brightness_slider = tk.Scale(self, from_=0, to=100, orient=tk.HORIZONTAL)
        self.brightness_slider.set(50)
        self.brightness_slider.pack(anchor="nw", pady=5)

        self.sharpness_label = tk.Label(self, text="Sharpness")
        self.sharpness_label.pack(anchor="nw", pady=2)
        self.sharpness_slider = tk.Scale(self, from_=0, to=10, resolution=1, orient=tk.HORIZONTAL)
        self.sharpness_slider.set(0)
        self.sharpness_slider.pack(anchor="nw", pady=5)

        self.reset_btn = tk.Button(self, text="Reset Adjustments")
        self.reset_btn.pack(anchor="nw", pady=10)

