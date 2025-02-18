# main.py

import sys
from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QFont, QColor
from ui import TypewriterConverter

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))

    # Set dark palette
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.WindowText, QColor("white"))
    palette.setColor(palette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor("white"))
    palette.setColor(palette.ColorRole.ToolTipText, QColor("white"))
    palette.setColor(palette.ColorRole.Text, QColor("white"))
    palette.setColor(palette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ButtonText, QColor("white"))
    palette.setColor(palette.ColorRole.BrightText, QColor("red"))
    palette.setColor(palette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.HighlightedText, QColor("black"))
    app.setPalette(palette)

    font = app.font()
    font.setFamily('Courier')
    app.setFont(font)

    window = TypewriterConverter()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
