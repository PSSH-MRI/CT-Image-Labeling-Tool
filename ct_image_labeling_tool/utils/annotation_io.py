import os
import json
import cv2
import base64
import numpy as np
from model.annotation import EllipseAnnotation, PolygonAnnotation, AnnotationGroup

def save_annotations_to_json(file_path, annotations: dict, original_size):
    if not file_path or not annotations:
        return None

    json_file = os.path.splitext(file_path)[0] + ".json"
    orig_w, orig_h = original_size

    label_data = {"file_path": [os.path.basename(file_path)], "annotations": []}

    for name, group in annotations.items():
        for shape_data in group.shapes:
            if isinstance(shape_data, EllipseAnnotation):
                if shape_data.mask is None:
                    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                    cv2.ellipse(mask, tuple(map(int, shape_data.center)),
                                tuple(map(int, shape_data.axes)), shape_data.angle, 0, 360, 255, -1)
                    _, buffer = cv2.imencode(".png", mask)
                    shape_data.mask = base64.b64encode(buffer).decode("utf-8")
                entry = {
                    "name": name,
                    "shape": "ellipse",
                    "center": shape_data.center,
                    "axes": shape_data.axes,
                    "angle": shape_data.angle,
                    "color": group.color,
                    "mask": shape_data.mask,
                    "orig_size": shape_data.image_size
                }
            elif isinstance(shape_data, PolygonAnnotation):
                ann_size = shape_data.image_size
                scale_x = orig_w / ann_size[0]
                scale_y = orig_h / ann_size[1]
                converted_points = [(int(pt[0] * scale_x), int(pt[1] * scale_y)) for pt in shape_data.points]

                mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                cv2.fillPoly(mask, [np.array(converted_points, dtype=np.int32)], color=255)
                _, buffer = cv2.imencode(".png", mask)
                mask_encoded = base64.b64encode(buffer).decode("utf-8")

                entry = {
                    "name": name,
                    "shape": shape_data.shape,
                    "points": converted_points,
                    "color": group.color,
                    "mask": mask_encoded,
                    "orig_size": shape_data.image_size
                }
            else:
                continue

            label_data["annotations"].append(entry)

    with open(json_file, "w") as json_obj:
        json.dump(label_data, json_obj, indent=4)

    return json_file

def load_annotations_from_json(json_path):
    with open(json_path, "r") as file:
        data = json.load(file)

    annotations = {}
    for annotation in data.get("annotations", []):
        name = annotation["name"]
        shape = annotation["shape"]
        color = tuple(annotation["color"])
        mask = annotation.get("mask")
        orig_size = tuple(annotation.get("orig_size"))

        if shape == "ellipse" and "center" in annotation:
            shape_data = EllipseAnnotation(
                shape="ellipse",
                center=tuple(annotation["center"]),
                axes=tuple(annotation["axes"]),
                angle=annotation["angle"],
                image_size=orig_size,
                mask=mask
            )
        else:
            shape_data = PolygonAnnotation(
                shape=shape,
                points=[tuple(pt) for pt in annotation["points"]],
                image_size=orig_size,
                mask=mask
            )

        if name not in annotations:
            annotations[name] = AnnotationGroup(color=color)
        annotations[name].shapes.append(shape_data)

    return annotations