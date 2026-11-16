"""Pestaña Ejecución: consola del simulador TM.

Muestra lo que imprime el simulador (las preguntas de IN y los resultados de OUT) y tiene
una línea para escribir: el número que pide IN o un comando de la TM (d 0 5, r, v, h, q).
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from src.core.tm_runner import TMRunner
from .paleta import paleta

# Lo que imprime tm.c
_PREGUNTAS_IN = ("(IN): ", "(INR): ")  # entero / real
_PREGUNTA_COMANDO = "Comando TM (h=ayuda): "
_RESULTADO = "Resultado del programa (OUT):"
_FIN = "Ejecucion finalizada (HALT)"


class TMConsole(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._paleta = paleta(tema_claro=False)
        self._runner = TMRunner(self)
        self._runner.salida.connect(self._mostrar)
        self._runner.termino.connect(self._al_terminar)
        self._runner.fallo.connect(self._al_fallar)
        self._archivo: Optional[str] = None
        self._pendiente = ""   # el final de una línea que todavía no llega completa
        self._eco_g = False    # falta mostrar el 'g' que se mandó solo al iniciar

        self._estado = QLabel()
        self._estado.setWordWrap(True)
        self._otra_vez = QPushButton("Ejecutar de nuevo")
        self._otra_vez.setToolTip("Vuelve a cargar el .tm en el simulador y lo ejecuta (g)")
        self._otra_vez.clicked.connect(self._reiniciar)
        self._detener = QPushButton("Detener")
        self._detener.clicked.connect(self._runner.detener)
        self._consola_externa = QPushButton("Abrir en consola")
        self._consola_externa.setToolTip("Abre el simulador TM en una ventana de consola aparte")
        self._consola_externa.clicked.connect(self._abrir_en_consola)

        barra = QHBoxLayout()
        barra.addWidget(self._estado, 1)
        barra.addWidget(self._otra_vez)
        barra.addWidget(self._detener)
        barra.addWidget(self._consola_externa)

        self._texto = QPlainTextEdit()
        self._texto.setReadOnly(True)
        self._texto.setFont(QFont("Courier New", 10))

        self._entrada = QLineEdit()
        self._entrada.setFont(QFont("Courier New", 10))
        self._entrada.setPlaceholderText(
            "Escribe el número que pide IN, o un comando de la TM (h = ayuda), y presiona Enter"
        )
        self._entrada.returnPressed.connect(self._enviar)
        enviar = QPushButton("Enviar")
        enviar.clicked.connect(self._enviar)
        linea = QHBoxLayout()
        linea.addWidget(QLabel(">"))
        linea.addWidget(self._entrada, 1)
        linea.addWidget(enviar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(barra)
        layout.addWidget(self._texto, 1)
        layout.addLayout(linea)
        self.clear()

    # ─── API para OutputTabs ─────────────────────────────────────────────────

    def ejecutar(self, archivo_tm: str) -> None:
        """Carga el .tm recién generado en el simulador y lo ejecuta."""
        self._archivo = archivo_tm
        self._reiniciar()

    def mostrar_mensaje(self, mensaje: str) -> None:
        """Cuando no hay nada que ejecutar (errores, falta el simulador…)."""
        self.clear()
        self._estado.setText(mensaje)

    def detener(self) -> None:
        self._runner.detener()

    def clear(self) -> None:
        """Detiene el simulador: el .tm que estaba corriendo ya no es del programa actual."""
        self._runner.detener()
        self._archivo = None
        self._pendiente = ""
        self._texto.clear()
        self._estado.setText("Presiona F9 (Ejecutar) para compilar el programa y correrlo en el simulador TM.")
        self._actualizar_botones()

    def set_tema_claro(self, tema_claro: bool) -> None:
        self._paleta = paleta(tema_claro)

    # ─── Simulador ───────────────────────────────────────────────────────────

    def _reiniciar(self) -> None:
        if not self._archivo:
            return
        self._runner.detener()  # antes de limpiar: al cerrarse escribe lo que le quedaba
        self._texto.clear()
        self._pendiente = ""
        self._eco_g = True
        self._estado.setText(f"Simulador TM: {Path(self._archivo).name}, ejecutando (g)…")
        self._runner.iniciar(self._archivo)  # si falla, _al_fallar cambia el estado
        self._actualizar_botones()
        self._entrada.setFocus()

    def _enviar(self) -> None:
        texto = self._entrada.text().strip()
        if not texto or not self._runner.is_running():
            return
        self._entrada.clear()
        self._eco(texto)
        self._runner.enviar(texto)

    def _eco(self, texto: str) -> None:
        """Lo que se le manda al simulador (la consola no lo repite: la entrada es un tubo)."""
        self._escribir(texto + "\n", self._formato(self._paleta["conversion"], negrita=True))

    def _mostrar(self, datos: str) -> None:
        texto = self._pendiente + datos.replace("\r\n", "\n")
        self._pendiente = ""
        if self._eco_g and _PREGUNTA_COMANDO in texto:
            # El primer prompt de comandos lo contestó el 'g' automático
            corte = texto.index(_PREGUNTA_COMANDO) + len(_PREGUNTA_COMANDO)
            self._procesar(texto[:corte])
            self._eco("g")
            self._eco_g = False
            texto = texto[corte:]
        self._procesar(texto)

    def _procesar(self, texto: str) -> None:
        """Escribe la salida por líneas para resaltar los resultados y los errores. Las
        preguntas (IN y el prompt de comandos) no terminan en salto de línea: se muestran
        en cuanto llegan."""
        *completas, resto = texto.split("\n")
        for linea in completas:
            self._escribir(linea + "\n", self._formato_de(linea))
        if resto.endswith(": "):
            self._escribir(resto, self._formato_de(resto))
            self._pendiente = ""
            if resto.endswith(_PREGUNTAS_IN):
                self._estado.setText("El programa pide un número: escríbelo abajo y presiona Enter.")
            elif resto.endswith(_PREGUNTA_COMANDO) and _FIN in self._texto.toPlainText()[-300:]:
                self._estado.setText(
                    "El programa terminó (HALT). Puedes usar comandos de la TM: d 0 5 (memoria), "
                    "r (registros), v (código .ci), q (salir)."
                )
        else:
            self._pendiente = resto

    def _al_terminar(self) -> None:
        if self._pendiente:
            self._escribir(self._pendiente, QTextCharFormat())
            self._pendiente = ""
        self._estado.setText("El simulador TM se cerró. Presiona «Ejecutar de nuevo» para correrlo otra vez.")
        self._actualizar_botones()

    def _al_fallar(self, mensaje: str) -> None:
        self._estado.setText(mensaje)
        self._actualizar_botones()

    def _abrir_en_consola(self) -> None:
        if self._archivo:
            error = self._runner.abrir_en_consola(self._archivo)
            if error:
                self._estado.setText(error)

    def _actualizar_botones(self) -> None:
        corriendo = self._runner.is_running()
        self._otra_vez.setEnabled(bool(self._archivo))
        self._consola_externa.setEnabled(bool(self._archivo))
        self._detener.setEnabled(corriendo)
        self._entrada.setEnabled(corriendo)

    # ─── Texto ───────────────────────────────────────────────────────────────

    def _formato_de(self, linea: str) -> QTextCharFormat:
        if linea.startswith(_RESULTADO):
            return self._formato(None, negrita=True)
        if linea.startswith("Error"):
            return self._formato(self._paleta["falla"], negrita=True)
        return QTextCharFormat()

    @staticmethod
    def _formato(color: Optional[str], negrita: bool = False) -> QTextCharFormat:
        formato = QTextCharFormat()
        if color:
            formato.setForeground(QColor(color))
        if negrita:
            formato.setFontWeight(QFont.Weight.Bold)
        return formato

    def _escribir(self, texto: str, formato: QTextCharFormat) -> None:
        cursor = self._texto.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(texto, formato)
        self._texto.setTextCursor(cursor)
        self._texto.ensureCursorVisible()
