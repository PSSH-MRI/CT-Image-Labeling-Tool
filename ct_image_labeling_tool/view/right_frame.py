import tkinter as tk
from tkinter import Listbox


class RightFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(side=tk.RIGHT, padx=10, pady=10)
        self.setup_gui()

    def setup_gui(self):
        self.annotation_listbox = Listbox(self, height=15, width=50)
        self.annotation_listbox.pack(anchor="ne", pady=5)

        self.file_listbox = Listbox(self, height=10, width=50)
        self.file_listbox.pack(anchor="se", pady=5)
    
        self.load_files_btn = tk.Button(self, text="Load Images")
        self.load_files_btn.pack(anchor="se", pady=5)