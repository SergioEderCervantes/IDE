"""Errores del compilador con una estructura común para todas las fases."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Fases que reportan errores (se usan como etiqueta en los mensajes)
LEXICO = "léxico"
SINTACTICO = "sintáctico"
SEMANTICO = "semántico"


@dataclass(frozen=True)
class CompilerError:
    """Un error detectado en el programa fuente.

    linea/columna son None cuando no hay token de referencia (fin de archivo).
    """
    fase: str
    mensaje: str
    linea: Optional[int] = None
    columna: Optional[int] = None

    def __str__(self) -> str:
        if self.linea is None:
            return f"Error {self.fase}: {self.mensaje}"
        return f"Error {self.fase} en línea {self.linea}, col {self.columna}: {self.mensaje}"

    def to_dict(self) -> dict:
        return {"linea": self.linea, "columna": self.columna, "mensaje": self.mensaje}
