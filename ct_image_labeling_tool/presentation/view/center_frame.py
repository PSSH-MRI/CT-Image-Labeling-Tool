import tkinter as tk

class CenterFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(side=tk.TOP, padx=10, pady=10, expand=True, fill=tk.BOTH)
        self.setup_gui()

    def setup_gui(self):
        # 이미지 패널
        self.image_panel = tk.Label(self)
        self.image_panel.pack(expand=True, fill=tk.BOTH)