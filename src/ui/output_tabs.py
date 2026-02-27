from PyQt6.QtWidgets import QTabWidget, QTextEdit, QWidget
from src.utils.constants import OUTPUT_TAB_NAMES

class OutputTabs(QTabWidget):
    """Un widget con múltiples pestañas para mostrar la salida del compilador."""

    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        self.tabs = {}
        self._create_tabs()

    def _create_tabs(self):
        """Crea una pestaña para cada nombre en OUTPUT_TAB_NAMES."""
        for name in OUTPUT_TAB_NAMES:
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFontFamily("Courier New")
            self.addTab(text_edit, name)
            self.tabs[name.lower().replace(" ", "_")] = text_edit

    def update_tokens(self, content: str):
        self.tabs["tokens"].setText(content)

    def update_ast(self, content: str):
        self.tabs["sintáctico"].setText(content)

    def update_semantic(self, content: str):
        self.tabs["semántico"].setText(content)

    def update_intermediate_code(self, content: str):
        self.tabs["código_intermedio"].setText(content)

    def update_symbol_table(self, content: str):
        self.tabs["tabla_de_símbolos"].setText(content)

    def update_errors(self, content: str):
        self.tabs["errores"].setText(content)

    def update_execution(self, content: str):
        self.tabs["ejecución"].setText(content)

    def clear_all(self):
        """Limpia el texto de todas las pestañas."""
        for text_edit in self.tabs.values():
            text_edit.clear()
