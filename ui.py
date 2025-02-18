import sys

from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QLabel, QScrollArea,                      QSlider, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
                             QStyle, QMessageBox, QPlainTextEdit)
from PyQt6.QtGui import QFont, QPainter, QColor, QImage, QPen, QPageSize
from PyQt6.QtCore import Qt, QTimer, QMarginsF, QSizeF, QByteArray, QBuffer
import os
import random
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

import json
import base64

from widgets import ScrollableImage, PaperSettings, TypewriterSettings, PAGE_BREAK_MARKER


class TypewriterConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cached_text = {}
        self.pages = []
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.convert_text)

        QApplication.instance().setAttribute(Qt.ApplicationAttribute.AA_SynthesizeTouchForUnhandledMouseEvents)

        self.initUI()

    def initUI(self):
        self.setWindowTitle("typy - A typewriter simulator by VX Software")
        self.setGeometry(100, 100, 1200, 800)

        self.text_cache = {}
        self.current_text = ""
        self.rendered_pages = []  #List of rendered QImages
        self.page_text = []  #List of text content per page
        self.current_page = 0
        self.rendered_chars = {}  #(page, x, y): (char, properties)
        self.text_positions = {}  #(page, line, char_index): (x, y)
        self.pages = []


        #Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()

        #Create left panel
        left_panel = self.create_left_panel()

        #Create right panel
        right_panel = self.create_right_panel()

        #Add panels to main layout
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)

        main_widget.setLayout(main_layout)
        self.apply_styles()

    def create_left_panel(self):
        left_panel = QVBoxLayout()

        #Create toolbar
        toolbar = QHBoxLayout()

        self.load_button = QPushButton('Upload')
        self.load_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.load_button.clicked.connect(self.load_file)


        self.save_all_button = QPushButton('Export')
        self.save_all_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_VistaShield))
        self.save_all_button.clicked.connect(self.save_all_pages)

        left_panel.addSpacing(10)

        self.save_project_button = QPushButton('Save')
        self.save_project_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_project_button.clicked.connect(self.save_project)

        self.load_project_button = QPushButton('Load')
        self.load_project_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent))
        self.load_project_button.clicked.connect(self.load_project)

        toolbar.addWidget(self.save_project_button)
        toolbar.addWidget(self.load_project_button)

        toolbar.addWidget(self.load_button)
        toolbar.addWidget(self.save_all_button)
        toolbar.addStretch()

        #text editor
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont('Courier', 12))
        self.text_edit.textChanged.connect(self.on_text_changed)

        #Optional: Set a placeholder text
        self.text_edit.setPlaceholderText("typy!")

        #Make it read monospace text better
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        #Create settings
        self.typewriter_settings = TypewriterSettings()
        self.typewriter_settings.settingsChanged.connect(self.on_settings_changed)

        self.paper_settings = PaperSettings()
        self.paper_settings.settingsChanged.connect(self.on_settings_changed)

        #Add all elements to left panel
        left_panel.addLayout(toolbar)
        left_panel.addWidget(self.text_edit)
        left_panel.addWidget(self.typewriter_settings)
        left_panel.addWidget(self.paper_settings)

        return left_panel

    def create_right_panel(self):
        right_panel = QVBoxLayout()

        #Create navigation bar
        nav_bar = QHBoxLayout()

        self.prev_button = QPushButton("Previous")
        self.prev_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.prev_button.clicked.connect(self.previous_page)

        self.next_button = QPushButton("Next")
        self.next_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.next_button.clicked.connect(self.next_page)

        self.page_label = QLabel("Page: 0/0")

        self.zoom_label = QLabel("Zoom: 100%")
        self.preview = ScrollableImage()

        self.reset_view_button = QPushButton("Fit to Screen")
        self.reset_view_button.clicked.connect(self.preview.fit_to_screen)

        nav_bar.addWidget(self.prev_button)
        nav_bar.addWidget(self.page_label)
        nav_bar.addWidget(self.next_button)
        nav_bar.addStretch()
        nav_bar.addWidget(self.zoom_label)
        nav_bar.addWidget(self.reset_view_button)

        #Create preview area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.preview)
        self.scroll_area.setWidgetResizable(True)

        #Connect preview signals
        self.preview.zoomChanged.connect(self.update_zoom_label)
        self.preview.pageChanged.connect(self.update_page_label)

        right_panel.addLayout(nav_bar)
        right_panel.addWidget(self.scroll_area)

        return right_panel

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d2d;
            }
            QTextEdit {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
            QGroupBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 1ex;
                color: #ffffff;
                padding: 10px;
            }
            QLabel {
                color: #ffffff;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 2px;
            }
        """)

    def on_text_changed(self):
        if self.typewriter_settings.auto_update.isChecked():
            self.update_timer.start(500)  #Delay for better performance

    def load_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as file:
                    self.text_edit.setText(file.read())
            except Exception as e:
                self.show_error_message(f"Error loading file: {str(e)}")

    def setup_painter(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = self.typewriter_settings.get_font()
        painter.setFont(font)

    def create_blank_page(self, width, height):
        page = QImage(width, height, QImage.Format.Format_RGB32)
        page.fill(QColor('#ffffff'))  #Fill with white by default
        return page

    def convert_text(self):
        if not self.text_edit.toPlainText():
            return

        try:
            #Get page dimensions and DPI
            dpi = self.paper_settings.dpi.value()
            page_width, page_height = self.paper_settings.get_page_size()
            margin_pixels = self.paper_settings.get_margin_pixels()

            #Calculate font size in pixels
            font_size_pixels = self.typewriter_settings.get_font_size_pixels(dpi)

            #Clear pages
            self.pages = []
            current_page = self.create_blank_page(page_width, page_height)
            painter = QPainter(current_page)

            #Set up the painter with proper font
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            font = self.typewriter_settings.get_font(dpi)
            painter.setFont(font)

            y_position = margin_pixels
            line_height = int(font_size_pixels * 1.5)  #1.5 line spacing
            available_width = page_width - (2 * margin_pixels)

            #Process text
            lines = self.text_edit.toPlainText().split('\n')
            for line in lines:
                if line.strip() == PAGE_BREAK_MARKER:
                    #Finish the current page and start a new one
                    painter.end()
                    self.pages.append(current_page)
                    current_page = self.create_blank_page(page_width, page_height)
                    painter = QPainter(current_page)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setFont(font)
                    y_position = margin_pixels
                    continue

                words = line.split(' ')
                current_line = ''
                for word in words:
                    test_line = current_line + word + ' '
                    if painter.fontMetrics().horizontalAdvance(test_line) > available_width:
                        #Draw the current line and start a new one
                        self.draw_line(painter, current_line, margin_pixels, y_position)
                        y_position += line_height
                        current_line = word + ' '
                        if y_position + line_height > page_height - margin_pixels:
                            #Finish the current page and start a new one
                            painter.end()
                            self.pages.append(current_page)
                            current_page = self.create_blank_page(page_width, page_height)
                            painter = QPainter(current_page)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                            painter.setFont(font)
                            y_position = margin_pixels
                    else:
                        current_line = test_line
                #Draw the last line
                self.draw_line(painter, current_line, margin_pixels, y_position)
                y_position += line_height
                if y_position + line_height > page_height - margin_pixels:
                    #Finish the current page and start a new one
                    painter.end()
                    self.pages.append(current_page)
                    current_page = self.create_blank_page(page_width, page_height)
                    painter = QPainter(current_page)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setFont(font)
                    y_position = margin_pixels

            #Add the final page
            painter.end()
            self.pages.append(current_page)

            #Update preview
            self.preview.setPages(self.pages)
            self.update_page_label()

        except Exception as e:
            self.show_error_message(f"Error converting text: {str(e)}")

    def on_settings_changed(self):
        if self.typewriter_settings.auto_update.isChecked():
            self.update_timer.start(200)

    def generate_ink_effects(self, effect_scale):
        effects = []
        for _ in range(random.randint(1, 3)):
            dx = random.uniform(-2, 2) * effect_scale
            dy = random.uniform(-2, 2) * effect_scale
            alpha = random.uniform(0.1, 0.3)
            effects.append((dx, dy, alpha))
        return effects

    def draw_line(self, painter, text, x, y):
        settings = self.typewriter_settings
        baseline = y + painter.fontMetrics().ascent()
        effect_scale = settings.get_effect_scale(self.paper_settings.get_dpi())

        for char in text:
            #Calculate variations
            darkness = random.uniform(
                1.0 - settings.darkness_variation.value(),
                1.0
            )
            v_offset = random.uniform(
                -settings.vertical_misalignment.value() * effect_scale,
                settings.vertical_misalignment.value() * effect_scale
            )

            #Draw main character
            color = QColor(0, 0, 0)
            color.setAlphaF(darkness)
            pen = QPen(color)
            pen.setWidthF(effect_scale)  #Scale pen width with font size
            painter.setPen(pen)

            char_x = x + random.uniform(-0.5, 0.5) * effect_scale
            painter.drawText(int(char_x), int(baseline + v_offset), char)

            #Add ink effects
            if settings.ink_splatter.isChecked() and random.random() < settings.ink_effect_prob.value():
                self.apply_ink_effects(painter, char_x, baseline + v_offset, char, darkness, effect_scale)

            #Move to next character position
            x += painter.fontMetrics().horizontalAdvance(char) + random.uniform(
                -settings.char_spacing.value() * effect_scale,
                settings.char_spacing.value() * effect_scale
            )

    def generate_ink_splatter(self, x, y, scale):
        splatter = []
        #Generate random dots around the point
        for _ in range(random.randint(3, 8)):
            dx = random.gauss(0, 2) * scale
            dy = random.gauss(0, 2) * scale
            size = random.uniform(0.5, 2) * scale
            alpha = random.uniform(0.1, 0.4)
            splatter.append((x + dx, y + dy, size, alpha))
        return splatter

    def draw_ink_splatter(self, painter, splatter):
        original_pen = painter.pen()
        for x, y, size, alpha in splatter:
            color = QColor(0, 0, 0)
            color.setAlphaF(alpha)
            painter.setPen(QPen(color, size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPoint(int(x), int(y))
        painter.setPen(original_pen)

    def apply_ink_effects(self, painter, x, y, char, darkness, effect_scale):
        #Original character with varying pressure
        pressure_variations = [
            (0.2, -0.5, -0.5),
            (0.3, 0.5, 0.5),
            (0.4, -0.3, 0.3)
        ]

        for alpha_mod, dx_mod, dy_mod in pressure_variations:
            color = QColor(0, 0, 0)
            color.setAlphaF(darkness * alpha_mod)
            dx = dx_mod * effect_scale
            dy = dy_mod * effect_scale
            painter.setPen(QPen(color, effect_scale * 0.8))
            painter.drawText(int(x + dx), int(y + dy), char)

        #Add ink bleeding effect
        if random.random() < 0.3:
            bleed_points = random.randint(2, 5)
            for _ in range(bleed_points):
                dx = random.gauss(0, 1) * effect_scale
                dy = random.gauss(0, 1) * effect_scale
                color = QColor(0, 0, 0)
                color.setAlphaF(darkness * random.uniform(0.1, 0.3))
                painter.setPen(QPen(color, effect_scale * 0.5))
                painter.drawText(int(x + dx), int(y + dy), char)

        #Add ink splatters
        if random.random() < 0.2:
            splatter = self.generate_ink_splatter(x, y, effect_scale)
            self.draw_ink_splatter(painter, splatter)

    def finish_page(self, painter, page):
        painter.end()
        self.pages.append(page)

    def save_image(self):
        if not self.pages:
            self.show_error_message("No pages to save!")
            return

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Document",
            "",
            "PDF Document (*.pdf);;PNG Images (*.png)"
        )

        if not file_name:
            return

        try:
            if selected_filter == "PDF Document (*.pdf)":
                self.save_as_images(file_name) #changed to save as pdf always..!
            else:
                self.save_as_images(file_name)
        except Exception as e:
            self.show_error_message(f"Error saving file: {str(e)}")

    def save_as_pdf(self, file_name):
        if not file_name.lower().endswith('.pdf'):
            file_name += '.pdf'

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_name)

        #Set paper size
        page_size = self.paper_settings.get_page_size()
        page_size_mm = QSizeF(page_size[0] * 25.4 / self.paper_settings.dpi.value(),
                              page_size[1] * 25.4 / self.paper_settings.dpi.value())
        printer.setPageSize(QPageSize(page_size_mm, QPageSize.Unit.Millimeter))

        #Set margins
        margins = QMarginsF(0, 0, 0, 0)
        printer.setPageMargins(margins)

        painter = QPainter()
        painter.begin(printer)

        for i, page in enumerate(self.pages):
            if i > 0:
                printer.newPage()
            painter.drawImage(0, 0, page)

        painter.end()

        self.show_success_message(f"PDF saved successfully to {file_name}")

    def save_as_images(self, file_name):
        base, ext = os.path.splitext(file_name)
        if not ext.lower() == '.png':
            ext = '.png'

        image_files = []
        for i, page in enumerate(self.pages):
            page_file = f"{base}_page_{i + 1}{ext}"
            page.save(page_file)
            image_files.append(page_file)

        self.convert_images_to_pdf(image_files, f"{base}.pdf")
        self.show_success_message(f"Saved {len(self.pages)} pages as PNG images and converted to PDF")

    def convert_images_to_pdf(self, image_files, pdf_file):
        c = canvas.Canvas(pdf_file, pagesize=letter)
        for image_file in image_files:
            image = Image.open(image_file)
            c.drawImage(image_file, 0, 0, width=letter[0], height=letter[1])
            c.showPage()
        c.save()

    def save_project(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "typy Project (*.typy)"
        )

        if not file_name:
            return

        if not file_name.endswith('.typy'):
            file_name += '.typy'

        try:
            project_data = {
                'text': self.text_edit.toPlainText(),
                'paper_settings': {
                    'paper_size': self.paper_settings.paper_size.currentText(),
                    'dpi': self.paper_settings.dpi.value(),
                    'margin': self.paper_settings.margin.value()
                },
                'typewriter_settings': {
                    'font_size': self.typewriter_settings.font_size.value(),
                    'darkness_variation': self.typewriter_settings.darkness_variation.value(),
                    'vertical_misalignment': self.typewriter_settings.vertical_misalignment.value(),
                    'char_spacing': self.typewriter_settings.char_spacing.value(),
                    'ink_splatter': self.typewriter_settings.ink_splatter.isChecked(),
                    'ink_fade': self.typewriter_settings.ink_fade.isChecked(),
                    'ink_effect_prob': self.typewriter_settings.ink_effect_prob.value()
                },
                'pages': []
            }

            #Save rendered pages as base64 encoded PNG
            for page in self.pages:
                #Convert QImage to bytes
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QBuffer.OpenModeFlag.WriteOnly)
                page.save(buffer, "PNG")
                #Convert to base64 and store
                page_data = base64.b64encode(byte_array.data()).decode()
                project_data['pages'].append(page_data)

            with open(file_name, 'w') as f:
                json.dump(project_data, f)

            self.show_success_message(f"Project saved successfully to {file_name}")

        except Exception as e:
            self.show_error_message(f"Error saving project: {str(e)}")

    def load_project(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            "",
            "typy Project (*.typy)"
        )

        if not file_name:
            return

        try:
            with open(file_name, 'r') as f:
                project_data = json.load(f)

            #Restore text
            self.text_edit.setPlainText(project_data['text'])

            #Restore paper settings
            paper_settings = project_data['paper_settings']
            self.paper_settings.paper_size.setCurrentText(paper_settings['paper_size'])
            self.paper_settings.dpi.setValue(paper_settings['dpi'])
            self.paper_settings.margin.setValue(paper_settings['margin'])

            #Restore typewriter settings
            tw_settings = project_data['typewriter_settings']
            self.typewriter_settings.font_size.setValue(tw_settings['font_size'])
            self.typewriter_settings.darkness_variation.setValue(tw_settings['darkness_variation'])
            self.typewriter_settings.vertical_misalignment.setValue(tw_settings['vertical_misalignment'])
            self.typewriter_settings.char_spacing.setValue(tw_settings['char_spacing'])
            self.typewriter_settings.ink_splatter.setChecked(tw_settings['ink_splatter'])
            self.typewriter_settings.ink_fade.setChecked(tw_settings['ink_fade'])
            self.typewriter_settings.ink_effect_prob.setValue(tw_settings['ink_effect_prob'])

            #Restore pages
            self.pages = []
            for page_data in project_data['pages']:
                #Convert base64 back to QImage
                byte_array = QByteArray.fromBase64(page_data.encode())
                image = QImage()
                image.loadFromData(byte_array, "PNG")
                self.pages.append(image)

            #Update preview
            self.preview.setPages(self.pages)
            self.update_page_label()

            self.show_success_message("Project loaded successfully")

        except Exception as e:
            self.show_error_message(f"Error loading project: {str(e)}")

    def save_all_pages(self):
        self.save_image()

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success_message(self, message):
        QMessageBox.information(self, "Success", message)

    def update_zoom_label(self, zoom):
        self.zoom_label.setText(f"Zoom: {int(zoom * 100)}%")

    def update_page_label(self):
        if hasattr(self, 'preview') and self.preview.pages:
            current = self.preview.getCurrentPage()
            total = self.preview.getTotalPages()
            self.page_label.setText(f"Page: {current}/{total}")
        else:
            self.page_label.setText("Page: 0/0")

    def next_page(self):
        self.preview.nextPage()

    def previous_page(self):
        self.preview.previousPage()

    def reset_view(self):
        self.preview.resetView()
        self.update_zoom_label(1.0)

    def calculate_line_height(self):
        return int(self.typewriter_settings.font_size.value() * 2.5)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.previous_page()
        elif event.key() == Qt.Key.Key_Right:
            self.next_page()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Plus:
                self.preview.zoom *= 1.1
                self.preview.update()
                self.update_zoom_label(self.preview.zoom)
            elif event.key() == Qt.Key.Key_Minus:
                self.preview.zoom /= 1.1
                self.preview.zoom = max(0.1, self.preview.zoom)
                self.preview.update()
                self.update_zoom_label(self.preview.zoom)
            elif event.key() == Qt.Key.Key_0:
                self.reset_view()
        super().keyPressEvent(event)
