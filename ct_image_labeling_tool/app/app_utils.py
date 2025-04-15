import tkinter as tk

class AppUtils:
    def __init__(self, app):
        self.app = app

    def get_annotation_color(self, annotation_text):
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255)
        ]
        if annotation_text in self.app.annotations:
            return self.app.annotations[annotation_text]["color"]
        else:
            return colors[len(self.app.annotations) % len(colors)]

    def add_annotation_into_listbox(self, annotation_text):
        self.app.right_controller.add_annotation_into_listbox(annotation_text)

    def add_file_into_listbox(self, content, at=tk.END):
        self.app.right_controller.add_file_into_listbox(content, at=at)

    def get_annotation_from_listbox(self, index):
        return self.app.right_controller.get_annotation_from_listbox(index)

    def get_size_of_listbox(self, list_type):
        return self.app.right_controller.get_listbox_size(list_type)