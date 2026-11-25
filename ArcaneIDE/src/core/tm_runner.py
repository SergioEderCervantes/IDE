"""Ejecuta un archivo .tm en el simulador TM de la materia (TM/tm.exe, compilado de TM/tm.c,
extendido para números reales).

El simulador es interactivo: lee comandos (g = ejecutar, s = un paso, d = memoria,
r = registros, v = ver el .ci, q = salir) y, cuando el programa ejecuta IN (entero) o INR
(real), pide un número.
TMRunner lo corre con la entrada y la salida conectadas al IDE: manda 'g' al iniciar y
reenvía lo que escriba el usuario. tm.c vacía su salida (fflush) antes de pedir un comando
o un número, así que cada pregunta llega a tiempo a la consola del IDE.
"""
from __future__ import annotations
import codecs
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

# ArcaneIDE/src/core/tm_runner.py → la raíz del repositorio está tres carpetas arriba
_CARPETA_TM = Path(__file__).resolve().parents[3] / "TM"


def ruta_simulador() -> Optional[Path]:
    """El ejecutable del simulador. ARCANE_TM permite usar otro; si no, TM/tm.exe (o TM/tm
    fuera de Windows)."""
    propio = os.environ.get("ARCANE_TM")
    candidatos = [Path(propio)] if propio else []
    candidatos.append(_CARPETA_TM / ("tm.exe" if sys.platform == "win32" else "tm"))
    return next((c for c in candidatos if c.is_file()), None)


SIN_SIMULADOR = (
    f"No se encontró el simulador TM en {_CARPETA_TM}.\n"
    f"Compílalo con TM/{'compilar_tm.bat' if sys.platform == 'win32' else 'compilar_tm.sh'} "
    "(necesita gcc) o indica otro con la variable ARCANE_TM."
)


class TMRunner(QObject):
    salida = pyqtSignal(str)   # texto que imprimió el simulador
    termino = pyqtSignal()     # el simulador se cerró
    fallo = pyqtSignal(str)    # no se pudo iniciar

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._leer)
        self._process.finished.connect(lambda *_: self.termino.emit())
        self._process.errorOccurred.connect(self._error)
        self.archivo: Optional[str] = None
        # El texto de un cout sale en UTF-8 byte por byte (OUTC): una letra con acento puede
        # quedar partida entre dos lecturas, así que se decodifica de forma incremental
        self._decodificador = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def iniciar(self, archivo_tm: str) -> None:
        """Carga el .tm en el simulador y lo ejecuta (comando g)."""
        self.detener()
        self.archivo = archivo_tm
        simulador = ruta_simulador()
        if simulador is None:
            self.fallo.emit(SIN_SIMULADOR)
            return
        self._decodificador.reset()
        self._process.setWorkingDirectory(str(Path(archivo_tm).parent))
        self._process.start(str(simulador), [archivo_tm])
        self.enviar("g")

    def enviar(self, texto: str) -> None:
        """Una línea para el simulador: un número que pide IN o un comando."""
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.write((texto + "\n").encode("ascii", errors="replace"))

    def detener(self) -> None:
        if self.is_running():
            self._process.kill()
            self._process.waitForFinished(1000)

    def abrir_en_consola(self, archivo_tm: str) -> Optional[str]:
        """Abre el simulador en una ventana de consola aparte. Devuelve un mensaje de error
        o None si se abrió."""
        simulador = ruta_simulador()
        if simulador is None:
            return SIN_SIMULADOR
        if sys.platform != "win32":
            return "Abrir en consola solo está disponible en Windows; usa la consola de esta pestaña."
        # chcp 65001: la consola en UTF-8, para que el texto con acentos de un cout se vea bien
        comando = f'cmd /c chcp 65001 >nul & "{simulador}" "{archivo_tm}"'
        subprocess.Popen(comando, cwd=str(Path(archivo_tm).parent),
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        return None

    def _leer(self) -> None:
        datos = bytes(self._process.readAllStandardOutput())  # type: ignore
        texto = self._decodificador.decode(datos)
        if texto:
            self.salida.emit(texto)

    def _error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.fallo.emit(f"No se pudo iniciar el simulador TM ({self._process.program()}).")
