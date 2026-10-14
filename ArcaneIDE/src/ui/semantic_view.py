from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSplitter, QStackedWidget, QTabWidget, QVBoxLayout, QWidget
from .ast_tree_widget import ASTTreeWidget
from .data_table import DataTable

_SIN_RESULTADO = "Ejecuta el análisis semántico (F7) para ver el árbol anotado y el recorrido."


class SemanticView(QWidget):
    """Resultado del análisis semántico.

    - Comparación: AST original (fase sintáctica) junto al AST anotado, con la columna
      de atributos (tipo, valor, dtype, dir, verificación) y los nodos CONV.
    - Recorrido: traza del análisis (inserciones y búsquedas en la tabla de símbolos,
      conversiones y verificaciones), en orden.
    Si el análisis no se ejecutó, se muestra un mensaje con el motivo.
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

        self._mensaje = QLabel(_SIN_RESULTADO)
        self._mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mensaje.setWordWrap(True)

        self._paginas = QStackedWidget()
        self._paginas.addWidget(self._mensaje)
        self._paginas.addWidget(self._tabs)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._paginas)

    def set_tema_claro(self, tema_claro: bool) -> None:
        self._original.set_tema_claro(tema_claro)
        self._anotado.set_tema_claro(tema_claro)

    def set_result(self, ast_original: Optional[dict], semantico: Optional[dict],
                   aviso: Optional[str] = None) -> None:
        """`semantico` es el JSON de la sección SEMANTICO: {ast, recorrido, ...}.

        Si es None, se muestra `aviso` (por qué no se ejecutó) o el mensaje por defecto.
        """
        self.clear()
        if not semantico:
            if aviso:
                self._mensaje.setText(aviso)
            return
        self._original.populate(ast_original or {})
        self._anotado.populate(semantico.get("ast") or {})
        self._recorrido.set_rows([
            [paso.get("linea"), paso.get("accion"), paso.get("detalle")]
            for paso in semantico.get("recorrido") or []
        ])
        self._paginas.setCurrentWidget(self._tabs)

    def clear(self) -> None:
        self._original.clear()
        self._anotado.clear()
        self._recorrido.clear()
        self._mensaje.setText(_SIN_RESULTADO)
        self._paginas.setCurrentWidget(self._mensaje)
