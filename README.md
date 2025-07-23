# CT Image Labeling Tool

A lightweight annotation tool designed for labeling CT axial L3 images for machine learning applications. This tool supports efficient data labeling and is optimized for preparing training datasets in medical image analysis.

## Features

*   **DICOM Image Viewer:** Load and display DICOM (.dcm) files, as well as standard image formats (PNG, JPG).
*   **Image Adjustments:** Interactively adjust brightness and sharpness to enhance the visibility of CT images, making it easier to identify anatomical structures.
*   **Advanced Annotation Tools:**
    *   **Multiple Drawing Modes:** Create annotations using ellipses and closed curves (free-form polygons).
    *   **Interactive Editing:**
        *   **Move, Resize, and Rotate:** Select and modify existing annotations with intuitive mouse controls. Ellipses can be rotated, and all shapes can be moved and resized.
        *   **Edit Annotation Names:** Easily rename annotations directly from the list.
*   **Efficient Workflow:**
    *   **JSON Export:** Annotations are saved in a clean JSON format, with one file per image, including shape data, labels, and colors.
    *   **Annotation Indicators:** Files with existing annotations are marked with a "✅" in the file list for quick identification.
    *   **Drag-and-Drop:** Add files to the queue by simply dragging them into the application window.
*   **Simple GUI:** An intuitive graphical user interface built with Tkinter.


## Key Packages

*   **Pillow (PIL):** Used for image processing.
*   **OpenCV (cv2):** Used for image processing.
*   **NumPy:** Used for numerical operations.
*   **Tkinter:** Used for the graphical user interface.
*   **pydicom:** Used for handling DICOM files.

## Installation

### Using `venv` (Python's built-in virtual environment)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/PSSH-MRI/CT-Image-Labeling-Tool.git
    cd CT-Image-Labeling-Tool
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Create a virtual environment
    python -m venv venv

    # Activate the virtual environment
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Using `conda`

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/PSSH-MRI/CT-Image-Labeling-Tool.git
    cd CT-Image-Labeling-Tool
    ```

2.  **Create and activate a conda environment:**
    ```bash
    # Create a new conda environment (e.g., named 'ct-labeling')
    conda create -n ct-labeling python=3.9

    # Activate the conda environment
    conda activate ct-labeling
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the application:**
    ```bash
    python -m ct_image_labeling_tool
    ```

2.  **Load Images:**
    *   Click the `Load Images` button to open a file dialog and select your DICOM or image files.
    *   Alternatively, drag and drop image files directly into the application window.

3.  **Annotate Images:**

    *   **Drawing Modes:** Use the buttons on the left or the following keyboard shortcuts to switch between modes:
        *   `n`: **Normal Mode** - Select, move, resize, and rotate existing annotations.
        *   `e`: **Ellipse Mode** - Draw ellipse annotations.
        *   `c`: **Closed Curve Mode** - Draw free-form, closed-curve annotations.

    *   **Creating Annotations:**
        *   **Ellipse:** In Ellipse Mode, click and drag to create an ellipse.
        *   **Closed Curve:** In Closed Curve Mode, click to place the starting point, then drag the mouse to draw a free-form curve. Release the mouse to complete the shape.
        *   After drawing a shape, a popup will appear asking for an annotation name. Enter a name and click `OK` to save it.

    *   **Editing and Deleting Annotations:**
        *   Switch to **Normal Mode** (`n`).
        *   **Select:** Hover over an annotation to see it highlighted. Click to select it.
        *   **Move:** Click and drag the selected annotation to move it.
        *   **Resize:** For ellipses, drag the corner handles to resize the shape.
        *   **Rotate:** For ellipses, drag the area near the top handle to rotate it.
        *   **Delete an Annotation:** Select an annotation on the image and press the `Delete` key to remove it.

4.  **File and Annotation Management:**
    *   **Navigate Images:** Use the file list on the right to switch between images.
    *   **Delete a File:** Select a file from the list on the right and press the `Delete` key to remove it from the list.
    *   **Save Annotations:** Click the `Save Labels (JSON)` button on the left panel to save the current image's annotations to a JSON file. Files with saved annotations are marked with a "✅".
    

5.  **Adjust Image Properties:**
    *   Use the sliders on the left to adjust the brightness and sharpness of the image for better visibility.

## How to Cite

If you use this tool in your research, please cite it as follows:

```
@software{CT_Image_Labeling_Tool,
  author = {Mastoid1 and seunggyun-jeong},
  title = {CT-Image-Labeling-Tool},
  url = {https://github.com/PSSH-MRI/CT-Image-Labeling-Tool},
  version = {1.0.0},
  year = {2024}
}
```

## Authors
<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Mastoid1">
        <img src="https://github.com/Mastoid1.png" width="100px;" alt="Mastoid1"/>
        <br />
        <sub><b>Mastoid1</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/seunggyun-jeong">
        <img src="https://github.com/seunggyun-jeong.png" width="100px;" alt="seunggyun-jeong"/>
        <br />
        <sub><b>seunggyun-jeong</b></sub>
      </a>
    </td>
  </tr>
</table>

## Acknowledgements

This tool was inspired by and references the open-source image annotation tool, [labelme](https://github.com/wkentaro/labelme).