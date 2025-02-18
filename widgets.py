
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QPinchGesture
)

from PyQt6.QtGui import (
    QFont, QPainter, QColor)

from PyQt6.QtCore import (
    Qt, QRect, pyqtSignal,
    QEvent)


PAGE_BREAK_MARKER = '!pb'

class ScrollableImage(QWidget):
    zoomChanged = pyqtSignal(float)
    pageChanged = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 800)
        self.zoom = 1.0
        self.pages = []
        self.current_page = 0
        self.shadow_offset = 5

        #Track pinch gestures
        self.grabGesture(Qt.GestureType.PinchGesture)

        #Track touch events
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)

        #Initial position
        self.offset_x = 0
        self.offset_y = 0
        self.last_pos = None
        self.panning = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        #Draw checkered background
        bg_size = 20
        for x in range(0, self.width(), bg_size):
            for y in range(0, self.height(), bg_size):
                if (x // bg_size + y // bg_size) % 2:
                    painter.fillRect(x, y, bg_size, bg_size, QColor('#8c5d3b'))
                else:
                    painter.fillRect(x, y, bg_size, bg_size, QColor('#764428'))

        if self.pages and self.current_page < len(self.pages):
            current_image = self.pages[self.current_page]
            paper_width = int(current_image.width() * self.zoom)
            paper_height = int(current_image.height() * self.zoom)

            #Center position with offset
            x = int((self.width() - paper_width) // 2 + self.offset_x)
            y = int((self.height() - paper_height) // 2 + self.offset_y)

            #Draw shadow
            shadow_rect = QRect(
                x + self.shadow_offset,
                y + self.shadow_offset,
                paper_width,
                paper_height
            )
            painter.fillRect(shadow_rect, QColor(0, 0, 0, 50))

            #Draw paper
            paper_rect = QRect(x, y, paper_width, paper_height)
            painter.fillRect(paper_rect, QColor('#ffffff'))

            #Draw content
            scaled_image = current_image.scaled(
                paper_width,
                paper_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawImage(x, y, scaled_image)

    def event(self, event):
        if event.type() == QEvent.Type.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        pinch = event.gesture(Qt.GestureType.PinchGesture)
        if pinch:
            center = pinch.centerPoint().toPoint()
            if pinch.changeFlags() & QPinchGesture.ChangeFlag.ScaleFactorChanged:
                old_zoom = self.zoom
                self.zoom *= pinch.scaleFactor()
                self.zoom = max(0.1, min(5.0, self.zoom))

                #Adjust offset to zoom towards gesture center
                zoom_factor = self.zoom / old_zoom
                self.offset_x = center.x() - (center.x() - self.offset_x) * zoom_factor
                self.offset_y = center.y() - (center.y() - self.offset_y) * zoom_factor

                self.zoomChanged.emit(self.zoom)
                self.update()
            return True
        return False

    def setPages(self, pages):
        self.pages = pages
        self.current_page = 0
        self.offset_x = 0
        self.offset_y = 0
        self.update()
        self.pageChanged.emit(self.current_page + 1, len(self.pages))

        #Add these missing methods

    def fit_to_screen(self):
        if not self.pages:
            return
        current_image = self.pages[self.current_page]
        paper_width = current_image.width()
        paper_height = current_image.height()
        available_width = self.width()
        available_height = self.height()
        self.zoom = min(available_width / paper_width, available_height / paper_height)
        self.update()
        self.zoomChanged.emit(self.zoom)

    def getCurrentPage(self):
        return self.current_page + 1

    def getTotalPages(self):
        return len(self.pages)

    def resetView(self):
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            old_zoom = self.zoom

            if delta > 0:
                self.zoom *= 1.1
            else:
                self.zoom /= 1.1

            self.zoom = max(0.1, min(5.0, self.zoom))

            #Adjust offset to zoom towards mouse position
            zoom_factor = self.zoom / old_zoom
            mouse_x = event.position().x()
            mouse_y = event.position().y()

            self.offset_x = mouse_x - (mouse_x - self.offset_x) * zoom_factor
            self.offset_y = mouse_y - (mouse_y - self.offset_y) * zoom_factor

            self.zoomChanged.emit(self.zoom)
            self.update()
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.panning = True
            self.last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self.panning and self.last_pos is not None:
            delta = event.position() - self.last_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_pos = event.position()
            self.update()

    def nextPage(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.pageChanged.emit(self.current_page + 1, len(self.pages))
            self.update()

    def previousPage(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.pageChanged.emit(self.current_page + 1, len(self.pages))
            self.update()


class PaperSettings(QGroupBox):
    settingsChanged = pyqtSignal()

    PAPER_SIZES = {
        "a4": (210, 297),  #mm
        "letter": (216, 279),
        "a5": (148, 210),
        "b5": (176, 250),
        "legal": (216, 356),
        "a3": (297, 420)
    }

    def __init__(self, title="Paper Settings", parent=None):
        super().__init__(title, parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout()

        #Paper size selection
        self.paper_size = QComboBox()
        self.paper_size.addItems(self.PAPER_SIZES.keys())
        layout.addRow("Paper Size:", self.paper_size)

        #DPI selection
        self.dpi = QSpinBox()
        self.dpi.setRange(72, 600)
        self.dpi.setValue(300)
        self.dpi.setSingleStep(72)
        layout.addRow("DPI:", self.dpi)

        #Margins in mm
        self.margin = QSpinBox()
        self.margin.setRange(5, 50)  #mm
        self.margin.setValue(20)  #mm
        self.margin.setSingleStep(5)
        layout.addRow("Margins (mm):", self.margin)

        for widget in self.findChildren((QSpinBox, QComboBox)):
            if isinstance(widget, QSpinBox):
                widget.valueChanged.connect(self.settingsChanged.emit)
            else:
                widget.currentIndexChanged.connect(self.settingsChanged.emit)

        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.settingsChanged.emit)
        layout.addRow(self.apply_button)

        self.setLayout(layout)

    def get_page_size(self):
        #Get size in mm
        size_mm = self.PAPER_SIZES[self.paper_size.currentText()]

        #Convert mm to pixels at the specified DPI
        dpi = self.dpi.value()
        width = int((size_mm[0] * dpi) / 25.4)
        height = int((size_mm[1] * dpi) / 25.4)

        return (width, height)

    def get_margin_pixels(self):
        #Convert mm to pixels
        return int((self.margin.value() * self.dpi.value()) / 25.4)

    def get_dpi(self):
        return self.dpi.value()

    def get_margin_mm(self):
        return self.margin.value()


class TypewriterSettings(QGroupBox):
    settingsChanged = pyqtSignal()

    def __init__(self, title="Simulation Settings", parent=None):
        super().__init__(title, parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout()

        #Font size in points
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(12)
        self.font_size.setSingleStep(1)
        layout.addRow("Font Size (pt):", self.font_size)

        #Character darkness variation
        self.darkness_variation = QDoubleSpinBox()
        self.darkness_variation.setRange(0.0, 1.0)
        self.darkness_variation.setValue(0.17)
        self.darkness_variation.setSingleStep(0.02)
        layout.addRow("Darkness Variation:", self.darkness_variation)

        #Vertical misalignment
        self.vertical_misalignment = QDoubleSpinBox()
        self.vertical_misalignment.setRange(0.0, 3.0)
        self.vertical_misalignment.setValue(0.4)
        self.vertical_misalignment.setSingleStep(0.1)
        layout.addRow("Vertical Misalignment:", self.vertical_misalignment)

        #Character spacing variation
        self.char_spacing = QDoubleSpinBox()
        self.char_spacing.setRange(0.0, 2.0)
        self.char_spacing.setValue(0.45)
        self.char_spacing.setSingleStep(0.1)
        layout.addRow("Character Spacing:", self.char_spacing)

        #Ink effects
        self.ink_splatter = QCheckBox("Enable Ink Splatter")
        self.ink_splatter.setChecked(True)
        layout.addRow(self.ink_splatter)

        self.ink_fade = QCheckBox("Variable Ink Fade")
        self.ink_fade.setChecked(True)
        layout.addRow(self.ink_fade)

        self.ink_effect_prob = QDoubleSpinBox()
        self.ink_effect_prob.setRange(0.000, 1.000)
        self.ink_effect_prob.setValue(0.300)
        self.ink_effect_prob.setSingleStep(0.050)
        layout.addRow("Ink Effect Probability:", self.ink_effect_prob)

        #Live preview toggle
        self.auto_update = QCheckBox("Live Preview (Uncheck when loading project)")
        self.auto_update.setChecked(False)
        layout.addRow(self.auto_update)

        #Connect all controls to emit settingsChanged
        for widget in self.findChildren((QSpinBox, QDoubleSpinBox, QCheckBox)):
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(self.settingsChanged.emit)
            else:
                widget.stateChanged.connect(self.settingsChanged.emit)

        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.settingsChanged.emit)
        layout.addRow(self.apply_button)

        self.setLayout(layout)

    def get_font_size_pixels(self, dpi):
        #Convert points to pixels based on DPI
        return int((self.font_size.value() * dpi) / 72)

    def get_font(self, dpi):
        font = QFont('Courier')
        pixel_size = self.get_font_size_pixels(dpi)
        font.setPixelSize(pixel_size)
        return font

    def get_effect_scale(self, dpi):
        #Return a scaling factor for effects based on font size
        return self.get_font_size_pixels(dpi) / 12.0
