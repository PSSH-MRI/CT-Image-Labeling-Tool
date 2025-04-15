from controller.left_frame_controller import LeftFrameController
from controller.right_frame_controller import RightFrameController
from controller.center_frame_controller import CenterFrameController

from app.shortcuts import setup_shortcuts
from app.annotation_manager import AnnotationManager
from app.app_utils import AppUtils

class ImageLabelingApp:
    def __init__(self, root):
        self.root = root

        # File and image variables
        self.file_list = []
        self.current_file_path = None
        self.current_image = None
        self.adjusted_image = None
        self.tmp_image = None
        self.original_image_size = None

        # Annotations
        self.annotations = {}
        self.annotations_per_file = {}
        self.drawing_mode = None
        self.points = []
        self.selected_annotation = None
        self.selected_shape_index = None

        # Normal edit mode
        self.normal_mod_mode = None
        self.normal_mod_vertex = None
        self.normal_mod_start_mouse = None
        self.normal_mod_start_params = None

        # Drawing mode
        self.is_drawing = False
        self.start_point = None

        # Controllers
        self.left_controller = LeftFrameController(self, root)
        self.right_controller = RightFrameController(self, root)
        self.center_controller = CenterFrameController(self, root)

        # Helpers
        self.annotation_manager = AnnotationManager(self)
        self.utils = AppUtils(self)

        # Shortcuts
        setup_shortcuts(self)

        # Delegate annotation-related helpers
        self.update_display = self.annotation_manager.update_display
        self.redraw_annotations = self.annotation_manager.redraw_annotations
        self.show_image = self.annotation_manager.show_image
        self.show_image_with_tmp = self.annotation_manager.show_image_with_tmp
        self.handle_ellipse = self.annotation_manager.handle_ellipse
        self.get_image_panel_size = self.annotation_manager.get_image_panel_size