from typing import Optional
from PyQt6.QtWidgets import QTabWidget, QTextEdit, QWidget
from src.utils.constants import OUTPUT_TAB_NAMES
from .ast_tree_widget import ASTTreeWidget
from .data_table import DataTable
from .error_panel import ErrorPanel
from .semantic_view import SemanticView
from .tm_console import TMConsole
from .tm_view import TMView

class OutputTabs(QTabWidget):
    """Un widget con múltiples pestañas para mostrar la salida del compilador."""

    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        self.tabs = {}
        self._ast_widget: ASTTreeWidget = None  # type: ignore
        self._error_panel: ErrorPanel = None  # type: ignore
        self._semantic_view: SemanticView = None  # type: ignore
        self._symbol_table: DataTable = None  # type: ignore
        self._tm_view: TMView = None  # type: ignore
        self._tm_console: TMConsole = None  # type: ignore
        self._ultimo_ast: Optional[dict] = None  # AST original, para la comparación semántica
        self._create_tabs()

    def _create_tabs(self):
        """Crea una pestaña para cada nombre en OUTPUT_TAB_NAMES."""
        for name in OUTPUT_TAB_NAMES:
            if name == "Sintáctico":
                widget = ASTTreeWidget()
                self._ast_widget = widget
            elif name == "Semántico":
                widget = SemanticView()
                self._semantic_view = widget
            elif name == "Tabla de Símbolos":
                widget = DataTable(["Nombre", "Tipo", "Dirección", "Referencias"])
                self._symbol_table = widget
            elif name == "Errores":
                widget = ErrorPanel()
                self._error_panel = widget
            elif name == "Código Intermedio":
                widget = TMView()
                self._tm_view = widget
            elif name == "Ejecución":
                widget = TMConsole()
                self._tm_console = widget
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
        self._ultimo_ast = ast_dict
        self._ast_widget.populate(ast_dict)

    def update_semantic(self, data: Optional[dict], aviso: Optional[str] = None) -> None:
        """JSON de la sección SEMANTICO ya parseado (None si la fase no se ejecutó;
        en ese caso `aviso` explica por qué)."""
        self._semantic_view.set_result(self._ultimo_ast, data, aviso)

    def update_intermediate_code(self, content: str):
        """Código de tres direcciones (.ci)."""
        # Texto plano: el código lleva <, > y && que no deben interpretarse como HTML
        self.tabs["código_intermedio_de_tres_direcciones"].setPlainText(content)

    def update_tm_code(self, content: str, aviso: Optional[str] = None) -> None:
        """Código TM (.tm), en la pestaña Código Intermedio."""
        self._tm_view.set_codigo(content, aviso)

    def update_symbol_table(self, simbolos: Optional[list]) -> None:
        """JSON de la sección TABLA_SIMBOLOS ya parseado (None si la fase no se ejecutó)."""
        self._symbol_table.set_rows([
            [s.get("nombre"), s.get("tipo"), s.get("direccion"),
             ", ".join(str(linea) for linea in s.get("referencias") or [])]
            for s in simbolos or []
        ])

    def update_errors(self, data: Optional[dict]) -> int:
        """Muestra los errores por fase (JSON de ERRORES ya parseado). Devuelve el total."""
        return self._error_panel.set_errors(data)

    def show_compiler_failure(self, message: str) -> None:
        self._error_panel.show_failure(message)

    def run_tm(self, archivo_tm: str) -> None:
        """Carga el .tm en el simulador TM de la pestaña Ejecución y lo ejecuta."""
        self._tm_console.ejecutar(archivo_tm)

    def execution_message(self, mensaje: str) -> None:
        self._tm_console.mostrar_mensaje(mensaje)

    def stop_tm(self) -> None:
        self._tm_console.detener()

    def set_tema_claro(self, tema_claro: bool) -> None:
        """Ajusta los colores de resaltado al brillo del tema."""
        self._ast_widget.set_tema_claro(tema_claro)
        self._semantic_view.set_tema_claro(tema_claro)
        self._error_panel.set_tema_claro(tema_claro)
        self._tm_console.set_tema_claro(tema_claro)

    def clear_all(self):
        """Limpia el contenido de todas las pestañas (y detiene el simulador TM)."""
        self._ultimo_ast = None
        for widget in self.tabs.values():
            widget.clear()
