import sys
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet
from src.ui.main_window import MainWindow


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "liga.compiladores.ide"
        )
    except Exception:
        pass


def main():
    """The main entry point for the IDE application."""
    _set_windows_app_id()
    app = QApplication(sys.argv)

    icon_path = Path(__file__).resolve().parent / "assets" / "logoIDE.jpg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Apply default dark theme
    apply_stylesheet(app, theme='dark_purple.xml')
    
    main_window = MainWindow(app)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
