import sys
from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet
from src.ui.main_window import MainWindow

def main():
    """The main entry point for the IDE application."""
    app = QApplication(sys.argv)
    
    # Apply default dark theme
    apply_stylesheet(app, theme='dark_purple.xml')
    
    main_window = MainWindow(app)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
