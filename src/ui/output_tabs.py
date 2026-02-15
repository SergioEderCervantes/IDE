from PyQt6.QtWidgets import QTabWidget, QTextEdit, QVBoxLayout, QWidget
from src.utils.constants import OUTPUT_TAB_NAMES

class OutputTabs(QTabWidget):
    """A widget with multiple tabs to display compiler output."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.tabs = {}
        self._create_tabs()

    def _create_tabs(self):
        """Creates a tab for each name in OUTPUT_TAB_NAMES."""
        for name in OUTPUT_TAB_NAMES:
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFontFamily("Courier New")
            self.addTab(text_edit, name)
            self.tabs[name.lower().replace(" ", "_")] = text_edit

    def update_tokens(self, content: str):
        self.tabs["tokens"].setText(content)

    def update_ast(self, content: str):
        self.tabs["ast"].setText(content)

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
        """Clears the text from all tabs."""
        for text_edit in self.tabs.values():
            text_edit.clear()
