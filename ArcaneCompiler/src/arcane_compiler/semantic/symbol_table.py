"""Tabla de símbolos del análisis semántico.

El lenguaje tiene un solo ámbito (main): las declaraciones solo pueden ir al nivel de
`main`, nunca dentro de if/while/do. Por eso la tabla es un único diccionario
nombre → Symbol y no necesita eliminar entradas al salir de un bloque.

La dirección de memoria se asigna con un contador secuencial (memloc) en orden de
declaración, como en el lenguaje TINY de Louden: la primera variable es la 0, la
siguiente la 1, etc.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator, Optional
from .tipos import Tipo


@dataclass
class Symbol:
    nombre: str
    tipo: Tipo
    direccion: int
    declaracion: int  # línea donde se declaró
    referencias: list[int] = field(default_factory=list)  # líneas donde se usa (sin repetir)

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "tipo": str(self.tipo),
            "direccion": self.direccion,
            "declaracion": self.declaracion,
            "referencias": list(self.referencias),
        }


class SymbolTable:
    def __init__(self) -> None:
        self._simbolos: dict[str, Symbol] = {}
        self._memloc = 0

    def insert(self, nombre: str, tipo: Tipo, linea: int) -> Optional[Symbol]:
        """Inserta un identificador declarado y le asigna la siguiente dirección.

        Devuelve None si ya existía (declaración duplicada); en ese caso la tabla no
        cambia y no se consume dirección.
        """
        if nombre in self._simbolos:
            return None
        simbolo = Symbol(nombre, tipo, self._memloc, linea)
        self._simbolos[nombre] = simbolo
        self._memloc += 1
        return simbolo

    def lookup(self, nombre: str) -> Optional[Symbol]:
        """Busca un identificador. None si no fue declarado."""
        return self._simbolos.get(nombre)

    def add_reference(self, nombre: str, linea: int) -> None:
        """Registra la línea de un uso del identificador (una vez por línea)."""
        simbolo = self._simbolos.get(nombre)
        if simbolo is not None and linea not in simbolo.referencias:
            simbolo.referencias.append(linea)

    def __contains__(self, nombre: str) -> bool:
        return nombre in self._simbolos

    def __iter__(self) -> Iterator[Symbol]:
        """Recorre los símbolos en orden de declaración (= orden de dirección)."""
        return iter(self._simbolos.values())

    def __len__(self) -> int:
        return len(self._simbolos)

    def to_list(self) -> list[dict]:
        return [s.to_dict() for s in self]
