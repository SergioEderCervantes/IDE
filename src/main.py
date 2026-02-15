import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    """The main entry point for the IDE application."""
    app = QApplication(sys.argv)
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
