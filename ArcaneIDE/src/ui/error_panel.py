from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget
from .data_table import DataTable
from .paleta import paleta

# (llave en el JSON de ERRORES, título de la sub-pestaña)
_FASES = [
    ("lexico", "Léxicos"),
    ("sintactico", "Sintácticos"),
    ("semantico", "Semánticos"),
]


class ErrorPanel(QWidget):
    """Errores separados por fase (una tabla por fase) y avisos del compilador.

    El título de cada sub-pestaña muestra el conteo: "Sintácticos (2)", o "(—)" si
    esa fase no se ejecutó.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paleta = paleta(tema_claro=False)

        # Avisos del pipeline (una o dos líneas)
        self._mensaje = QLabel()
        self._mensaje.setWordWrap(True)
        self._mensaje.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # Falla del compilador: puede ser un traceback largo, así que va en un área con
        # scroll y altura limitada para no desplazar el resto de la ventana
        self._falla = QPlainTextEdit()
        self._falla.setReadOnly(True)
        self._falla.setMaximumHeight(160)

        self._fases = QTabWidget()
        self._tablas: dict[str, DataTable] = {}
        for key, titulo in _FASES:
            tabla = DataTable(["Línea", "Columna", "Descripción"])
            self._tablas[key] = tabla
            self._fases.addTab(tabla, titulo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._mensaje)
        layout.addWidget(self._falla)
        layout.addWidget(self._fases)

        self.clear()

    def set_tema_claro(self, tema_claro: bool) -> None:
        self._paleta = paleta(tema_claro)
        self._aplicar_colores()

    def set_errors(self, data: Optional[dict]) -> int:
        """Llena las tablas con el JSON de la sección ERRORES. Devuelve el total de errores."""
        data = data or {}
        total = 0
        primera_con_errores = None

        for i, (key, titulo) in enumerate(_FASES):
            errores = data.get(key)
            if errores is None:
                self._tablas[key].clear()
                self._fases.setTabText(i, f"{titulo} (—)")
                continue
            self._tablas[key].set_rows(
                [[e.get("linea"), e.get("columna"), e.get("mensaje")] for e in errores]
            )
            self._fases.setTabText(i, f"{titulo} ({len(errores)})")
            total += len(errores)
            if errores and primera_con_errores is None:
                primera_con_errores = i

        if primera_con_errores is not None:
            self._fases.setCurrentIndex(primera_con_errores)
        self._mensaje.setText("\n".join(data.get("avisos") or []))
        self._mensaje.setVisible(bool(self._mensaje.text()))
        return total

    def show_failure(self, message: str) -> None:
        """Falla del compilador en sí (no del programa fuente)."""
        self.clear()
        self._falla.setPlainText(f"Error del compilador:\n{message}")
        self._falla.setVisible(True)
        # La última línea de un traceback es la que dice qué falló
        self._falla.verticalScrollBar().setValue(self._falla.verticalScrollBar().maximum())  # type: ignore

    def clear(self) -> None:
        for i, (key, titulo) in enumerate(_FASES):
            self._tablas[key].clear()
            self._fases.setTabText(i, f"{titulo} (—)")
        self._mensaje.clear()
        self._mensaje.setVisible(False)
        self._falla.clear()
        self._falla.setVisible(False)
        self._aplicar_colores()

    def _aplicar_colores(self) -> None:
        self._mensaje.setStyleSheet(f"color: {self._paleta['aviso']}; padding: 4px;")
        self._falla.setStyleSheet(f"color: {self._paleta['falla']};")
