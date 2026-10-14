from typing import Optional
from PyQt6.QtWidgets import QTabWidget, QTextEdit, QWidget
from src.utils.constants import OUTPUT_TAB_NAMES
from .ast_tree_widget import ASTTreeWidget
from .error_panel import ErrorPanel

class OutputTabs(QTabWidget):
    """Un widget con múltiples pestañas para mostrar la salida del compilador."""

    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        self.tabs = {}
        self._ast_widget: ASTTreeWidget = None  # type: ignore
        self._error_panel: ErrorPanel = None  # type: ignore
        self._create_tabs()

    def _create_tabs(self):
        """Crea una pestaña para cada nombre en OUTPUT_TAB_NAMES."""
        for name in OUTPUT_TAB_NAMES:
            if name == "Sintáctico":
                widget = ASTTreeWidget()
                self._ast_widget = widget
            elif name == "Errores":
                widget = ErrorPanel()
                self._error_panel = widget
            else:
                widget = QTextEdit()
                widget.setReadOnly(True)
                widget.setFontFamily("Courier New")
            self.addTab(widget, name)
            self.tabs[name.lower().replace(" ", "_")] = widget

    def focus_tab(self, key: str) -> None:
        """Muestra la pestaña con la llave dada (p. ej. 'errores', 'sintáctico')."""
        if key in self.tabs:
            self.setCurrentWidget(self.tabs[key])

    def update_tokens(self, content: str):
        self.tabs["tokens"].setText(content)

    def update_ast(self, content: str):
        pass  # El árbol se gestiona exclusivamente vía set_ast() / ast_ready signal

    def set_ast(self, ast_dict: dict) -> None:
        self._ast_widget.populate(ast_dict)

    def update_semantic(self, content: str):
        self.tabs["semántico"].setText(content)

    def update_intermediate_code(self, content: str):
        self.tabs["código_intermedio"].setText(content)

    def update_symbol_table(self, content: str):
        self.tabs["tabla_de_símbolos"].setText(content)

    def update_errors(self, data: Optional[dict]) -> int:
        """Muestra los errores por fase (JSON de ERRORES ya parseado). Devuelve el total."""
        return self._error_panel.set_errors(data)

    def show_compiler_failure(self, message: str) -> None:
        self._error_panel.show_failure(message)

    def update_execution(self, content: str):
        self.tabs["ejecución"].setText(content)

    def clear_all(self):
        """Limpia el contenido de todas las pestañas."""
        for widget in self.tabs.values():
            widget.clear()
