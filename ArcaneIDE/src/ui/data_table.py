from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


class DataTable(QTableWidget):
    """Tabla de solo lectura que se llena con filas de texto (errores, tabla de símbolos)."""

    def __init__(self, headers: list[str], parent=None):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setWordWrap(True)
        self.verticalHeader().setVisible(False)  # type: ignore
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)  # type: ignore
        header.setStretchLastSection(True)  # type: ignore

    def set_rows(self, rows: list[list]) -> None:
        """Reemplaza el contenido. None se muestra como celda vacía."""
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))
        self.resizeRowsToContents()

    def clear_rows(self) -> None:
        """Vacía las filas conservando los encabezados (QTableWidget.clear() los borra)."""
        self.setRowCount(0)
