"""Pestaña Código Intermedio: el código TM (.tm) del programa recién compilado.

La tabla muestra cada instrucción en su dirección, con su operación, sus operandos y el
comentario del generador. "Archivo .tm" muestra el archivo tal como lo lee el simulador:
ahí los saltos que se completan después (emit_backup) aparecen más abajo con su dirección
original, igual que en el .tm del tiny.exe de la materia.
"""
from __future__ import annotations
import re
from typing import Optional

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from .data_table import DataTable

# "  9:    JLT  0,2(7) \tbr if true"  →  dirección, operación, operandos, comentario
_INSTRUCCION = re.compile(r"^\s*(\d+):\s+(\w+)\s+(\S+)\s*(?:\t(.*))?$")
_ARCHIVO = re.compile(r"^\* File: (.*)$", re.MULTILINE)


def instrucciones(texto: str) -> list[tuple[int, str, str, str]]:
    """Las instrucciones del .tm ordenadas por dirección (los comentarios '*' se omiten)."""
    filas = []
    for linea in texto.splitlines():
        m = _INSTRUCCION.match(linea)
        if m:
            filas.append((int(m.group(1)), m.group(2), m.group(3), (m.group(4) or "").strip()))
    return sorted(filas)


class TMView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._titulo = QLabel()
        self._boton_tabla = QPushButton("Tabla")
        self._boton_archivo = QPushButton("Archivo .tm")
        for i, boton in enumerate((self._boton_tabla, self._boton_archivo)):
            boton.setCheckable(True)
            boton.clicked.connect(lambda _=False, i=i: self._mostrar(i))

        barra = QHBoxLayout()
        barra.addWidget(self._titulo, 1)
        barra.addWidget(self._boton_tabla)
        barra.addWidget(self._boton_archivo)

        self._tabla = DataTable(["Dirección", "Instrucción", "Operandos", "Comentario"])
        self._archivo = QPlainTextEdit()
        self._archivo.setReadOnly(True)
        self._archivo.setFont(QFont("Courier New", 10))
        self._archivo.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._vistas = QStackedWidget()
        self._vistas.addWidget(self._tabla)
        self._vistas.addWidget(self._archivo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(barra)
        layout.addWidget(self._vistas, 1)
        self._mostrar(0)
        self.clear()

    def set_codigo(self, texto: str, aviso: Optional[str] = None) -> None:
        """Contenido de la sección CODIGO_TM ('' si no se generó; `aviso` dice por qué)."""
        if not texto.strip():
            self.clear()
            if aviso:
                self._titulo.setText(aviso)
            return
        filas = instrucciones(texto)
        archivo = _ARCHIVO.search(texto)
        nombre = archivo.group(1).strip() if archivo else "programa.tm"
        self._titulo.setText(f"Código TM generado: {nombre}, {len(filas)} instrucciones")
        self._tabla.set_rows([list(f) for f in filas])
        self._archivo.setPlainText(texto)

    def clear(self) -> None:
        self._tabla.clear()
        self._archivo.clear()
        self._titulo.setText("Presiona F8 (Código intermedio) o F9 (Ejecutar) para generar el código TM.")

    def _mostrar(self, indice: int) -> None:
        self._vistas.setCurrentIndex(indice)
        self._boton_tabla.setChecked(indice == 0)
        self._boton_archivo.setChecked(indice == 1)
