from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QTabWidget, QVBoxLayout, QWidget
from .ast_tree_widget import ASTTreeWidget
from .data_table import DataTable


class SemanticView(QWidget):
    """Resultado del análisis semántico.

    - Comparación: AST original (fase sintáctica) junto al AST anotado, con la columna
      de atributos (tipo, valor, dtype, dir, verificación) y los nodos CONV.
    - Recorrido: traza del análisis (inserciones y búsquedas en la tabla de símbolos,
      conversiones y verificaciones), en orden.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._original = ASTTreeWidget(titulo="AST original")
        self._anotado = ASTTreeWidget(titulo="AST anotado", con_atributos=True)
        comparacion = QSplitter(Qt.Orientation.Horizontal)
        comparacion.addWidget(self._original)
        comparacion.addWidget(self._anotado)
        comparacion.setSizes([350, 650])

        self._recorrido = DataTable(["Línea", "Acción", "Detalle"])

        self._tabs = QTabWidget()
        self._tabs.addTab(comparacion, "Comparación")
        self._tabs.addTab(self._recorrido, "Recorrido")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    def set_result(self, ast_original: Optional[dict], semantico: Optional[dict]) -> None:
        """`semantico` es el JSON de la sección SEMANTICO: {ast, recorrido, ...}."""
        self.clear()
        if not semantico:
            return
        self._original.populate(ast_original or {})
        self._anotado.populate(semantico.get("ast") or {})
        self._recorrido.set_rows([
            [paso.get("linea"), paso.get("accion"), paso.get("detalle")]
            for paso in semantico.get("recorrido") or []
        ])

    def clear(self) -> None:
        self._original.clear()
        self._anotado.clear()
        self._recorrido.clear()
