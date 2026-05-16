# LabelForge — YOLO Dataset Editor (Tactical Edition)

![Main Screen View](assets/images/Ekran%20Resmi%202026-05-17%2001.54.54.png)

LabelForge is a powerful desktop application developed to quickly, reliably, and thoroughly edit, inspect, and expand YOLO format datasets, which are frequently used in computer vision projects. Its special "Tactical" (dark green/black) theme enables long working hours without eye strain. The application is developed using Tkinter, CustomTkinter, and Pillow (PIL), offering high-performance image and label manipulation.

## Core Features

![Features View](assets/images/Ekran%20Resmi%202026-05-17%2001.55.39.png)

### Modern and Advanced User Interface

Unlike classic and boring interfaces, LabelForge offers a "Dark" themed design based on CustomTkinter. The application uses a paned window layout to maximize your workspace. The left panel contains images and classes, the middle panel displays the original and annotated images, and the right panel houses the label list and tools.

### Comprehensive Image and Label Management

- **Automatic Scanning:** Images and YOLO format (`.txt`) labels in the selected folder are scanned and matched within seconds.
- **Class Management:** The `classes.txt` file is read automatically. New classes can be added, renamed, or unnecessary classes can be completely deleted through the interface. Color assignments are made uniquely and visually distinct for each class.
- **Mark as Reviewed:** To keep track of your progress in large datasets, you can mark images as "Reviewed" (by double-clicking the image name). This data is saved across sessions.

### Professional Bounding Box (BBox) Drawing and Editing

![BBox Drawing Screen](assets/images/Ekran%20Resmi%202026-05-17%2001.55.53.png)

- **Advanced Viewing:** Precise zooming with the mouse wheel (Scroll/Pinch) and panning (dragging) are available. The "FIT" button instantly resets the image to its original view.
- **Manual Drawing Mode:** A special "Draw Manual BBox" screen can be opened for missing or new objects to be detected. From here, you can select the desired class and add new bounding boxes using the drag-and-drop method.
- **Selection and Deletion:** In the full-screen "Annotated" view, multiple BBoxes can be selected by clicking or dragging and can be quickly deleted using the `DEL` or `Command+Backspace` (Mac) key.
- **Undo / Redo:** You can instantly undo or redo incorrect edits and deletions (`Ctrl+Z`, `Ctrl+Y`).

### Full Screen Detail View - Bulk Selection and Deletion Feature

![Full Screen Inspection](assets/images/Ekran%20Resmi%202026-05-17%2001.56.11.png)

To better inspect small details in images, "Original" or "Annotated" images can be opened in a full-screen window. Advanced mouse and keyboard controls remain active while in full-screen mode.

### Session Tracking

Your folder selections, classes, files marked as "reviewed," and the last viewed file are saved to be automatically loaded upon the application's next startup (`~/.labelforge_session.json`).

---

## Requirements and Installation

To run the project on your computer, the following Python libraries must be installed:

- Python 3.8 or higher
- `customtkinter`
- `Pillow`

**Installation Steps:**

1. Clone the repository to your computer:

   ```bash
   git clone https://github.com/SerhanEnsar/LabelForge.git
   cd LabelForge
   ```

2. Install the required libraries:

   ```bash
   pip install customtkinter Pillow
   ```

3. Launch the application:
   ```bash
   python labelforge.py
   ```

---

## User Guide

![User Interface](assets/images/Ekran%20Resmi%202026-05-17%2001.57.47.png)

After launching the project, you can start the labeling process by following these steps:

### 1. Selecting Folders

From the menu located on the top bar:

- **DATASET:** If your dataset is in a main directory (containing `images`, `labels`, and `classes.txt` inside), simply selecting this folder is enough. Other folders will be detected automatically.
- Alternatively, you can select the **IMAGES** and **LABELS** folders separately.
- After selecting the folders, click the **SCAN** button to load the images into the left panel.

### 2. Interface Controls

- **Left Click and Drag:** Pans the image.
- **Mouse Wheel / Touchpad:** Zooms in/out at the cursor's location.
- **Arrow Keys:** Allows quick navigation in the image list or panning the image in the drawing screen.

### 3. Label Editing

- You can view the list of existing boxes from the right panel and delete them using the "✕" button next to them.
- You can switch to the new labeling window by pressing the **✏ DRAW MANUAL BBOX** button on the original image screen.
- In drawing mode, select your class from the left menu, draw the box by left-clicking and dragging on the image, and save it by pressing the "Apply" button.

### 4. Class Settings

From the "CLASS LABELS" panel at the bottom left, you can click the "⋯" (three dots) icon next to each class to delete that class, rename it, or remove all labels belonging to that class from the current image at once.

---

## Contributing

This project is open-source. If you would like to contribute to the project:

1. "Fork" this repository.
2. Create a new feature branch (`git checkout -b feature/NewFeature`).
3. Commit your changes (`git commit -m 'Add some NewFeature'`).
4. Push to the branch (`git push origin feature/NewFeature`).
5. Open a "Pull Request".

## License

This project is licensed under the [MIT License](LICENSE). You are free to use and modify it as you wish.
