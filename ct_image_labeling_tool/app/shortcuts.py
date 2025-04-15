from tkinterdnd2 import DND_FILES

def setup_shortcuts(app):
    root = app.root
    
    
    # Enable drag and drop support
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', app.add_files_via_drag_and_drop)

    # Keyboard shortcuts for mode switching
    # n: normal, e: ellipse, c: closed curve, p: polygon
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
        app.delete_selected_file(event)
    elif is_descendant(widget_under, app.center_controller.get_image_panel):
        app.delete_selected_annotation(event)
        
def is_descendant(widget, parent):
    while widget is not None:
        if widget == parent:
            return True
        widget = widget.master
    return False