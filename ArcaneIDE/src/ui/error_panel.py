from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget
from .data_table import DataTable

# (llave en el JSON de ERRORES, título de la sub-pestaña)
_FASES = [
    ("lexico", "Léxicos"),
    ("sintactico", "Sintácticos"),
    ("semantico", "Semánticos"),
]

_COLOR_AVISO = "#e5a50a"
_COLOR_FALLA = "#e64553"


class ErrorPanel(QWidget):
    """Errores separados por fase (una tabla por fase) y avisos del compilador.

    El título de cada sub-pestaña muestra el conteo: "Sintácticos (2)", o "(—)" si
    esa fase no se ejecutó.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._mensaje = QLabel()
        self._mensaje.setWordWrap(True)
        self._mensaje.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self._fases = QTabWidget()
        self._tablas: dict[str, DataTable] = {}
        for key, titulo in _FASES:
            tabla = DataTable(["Línea", "Columna", "Descripción"])
            self._tablas[key] = tabla
            self._fases.addTab(tabla, titulo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._mensaje)
        layout.addWidget(self._fases)

        self.clear()

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
        self._show_message("\n".join(data.get("avisos") or []), _COLOR_AVISO)
        return total

    def show_failure(self, message: str) -> None:
        """Falla del compilador en sí (no del programa fuente)."""
        self.clear()
        self._show_message(f"Error del compilador:\n{message}", _COLOR_FALLA)

    def clear(self) -> None:
        for i, (key, titulo) in enumerate(_FASES):
            self._tablas[key].clear()
            self._fases.setTabText(i, f"{titulo} (—)")
        self._show_message("", None)

    def _show_message(self, text: str, color: Optional[str]) -> None:
        self._mensaje.setText(text)
        self._mensaje.setStyleSheet(f"color: {color}; padding: 4px;" if color else "")
        self._mensaje.setVisible(bool(text))
