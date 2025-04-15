from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union

@dataclass
class EllipseAnnotation:
    shape: str  # always "ellipse"
    center: Tuple[float, float]
    axes: Tuple[float, float]
    angle: float
    image_size: Tuple[int, int]
    mask: Optional[str] = None

@dataclass
class PolygonAnnotation:
    shape: str  # "polygon" or "closed_curve"
    points: List[Tuple[int, int]]
    image_size: Tuple[int, int]
    mask: Optional[str] = None

AnnotationShape = Union[EllipseAnnotation, PolygonAnnotation]

@dataclass
class AnnotationGroup:
    color: Tuple[int, int, int]
    shapes: List[AnnotationShape] = field(default_factory=list)

@dataclass
class AnnotationFile:
    file_path: str
    annotations: dict[str, AnnotationGroup]