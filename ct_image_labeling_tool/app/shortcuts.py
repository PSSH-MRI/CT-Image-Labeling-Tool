from tkinterdnd2 import DND_FILES

def setup_shortcuts(app):
    root = app.root
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', lambda event: app.right_controller.add_files_via_drag_and_drop(root.tk.splitlist(event.data)))

    root.bind("<Delete>", lambda event: handle_delete_key(app, event))
    root.bind("<n>", lambda event: app.left_controller.set_drawing_mode("normal"))
    root.bind("<e>", lambda event: app.left_controller.set_drawing_mode("ellipse"))
    root.bind("<c>", lambda event: app.left_controller.set_drawing_mode("closed_curve"))

def handle_delete_key(app, event):
    x, y = app.root.winfo_pointerx(), app.root.winfo_pointery()
    widget_under = app.root.winfo_containing(x, y)
    if widget_under is None:
        return

    if is_descendant(widget_under, app.right_controller.get_file_listbox):
        app.right_controller.delete_selected_file_from_listbox()
        app.annotations.clear()
        app.current_image = None
        app.current_file_path = None
        app.center_controller.clear_image_panel()
        print("[INFO] File deleted and view cleared.")

    elif is_descendant(widget_under, app.center_controller.get_image_panel):
        app.annotation_manager.delete_selected_annotation()

def is_descendant(widget, parent):
    while widget is not None:
        if widget == parent:
            return True
        widget = widget.master
    return False