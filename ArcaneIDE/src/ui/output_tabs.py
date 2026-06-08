from PyQt6.QtWidgets import QTabWidget, QTextEdit, QWidget
from src.utils.constants import OUTPUT_TAB_NAMES
from .ast_tree_widget import ASTTreeWidget

class OutputTabs(QTabWidget):
    """Un widget con múltiples pestañas para mostrar la salida del compilador."""

    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        self.tabs = {}
        self._ast_widget: ASTTreeWidget = None  # type: ignore
        self._create_tabs()

    def _create_tabs(self):
        """Crea una pestaña para cada nombre en OUTPUT_TAB_NAMES."""
        for name in OUTPUT_TAB_NAMES:
            if name == "Sintáctico":
                widget = ASTTreeWidget()
                self._ast_widget = widget
            else:
                widget = QTextEdit()
                widget.setReadOnly(True)
                widget.setFontFamily("Courier New")
            self.addTab(widget, name)
            self.tabs[name.lower().replace(" ", "_")] = widget

    def update_tokens(self, content: str):
        self.tabs["tokens"].setText(content)

    def update_ast(self, content: str):
        pass  # El árbol se gestiona exclusivamente vía set_ast() / ast_ready signal

    def set_ast(self, ast_dict: dict) -> None:
        self._ast_widget.populate(ast_dict)
        self.setCurrentWidget(self._ast_widget)

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
        for widget in self.tabs.values():
            widget.clear()
