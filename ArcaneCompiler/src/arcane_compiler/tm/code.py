"""Escritura de instrucciones TM: el equivalente de code.h y code.c del TINY de la materia.

cgen.py decide QUÉ instrucciones generar; este módulo las escribe con el formato que lee el
simulador (tm.c) y lleva la cuenta de las direcciones para resolver los saltos. Las
funciones tienen los nombres de code.c en snake_case (emitRO → emit_ro, emitSkip →
emit_skip, …) para que la correspondencia sea directa.

Formato de una instrucción (el mismo printf de code.c):

    "%3d:  %5s  %d,%d,%d "  + "\\t" + comentario      RO: registro, registro, registro
    "%3d:  %5s  %d,%d(%d) " + "\\t" + comentario      RM: registro, desplazamiento(base)

Las líneas que empiezan con '*' son comentarios. El archivo conserva el orden en que se
escriben las líneas: una instrucción que se completa después (un salto hacia adelante)
aparece más abajo con su dirección original, igual que en el .tm de TINY. El simulador
coloca cada instrucción en su dirección, así que el orden del archivo no importa.

Saltos (la TM no tiene etiquetas, solo direcciones):
- emit_skip(n) aparta n direcciones para una instrucción que todavía no se conoce y
  devuelve la primera.
- emit_backup(loc) regresa a esa dirección para escribirla; emit_restore() vuelve a la
  siguiente dirección libre.
- emit_rm_abs(op, r, a) escribe un salto a la dirección absoluta `a` como desplazamiento
  relativo al pc: d = a - (dirección actual + 1), porque al ejecutar una instrucción el pc
  ya apunta a la siguiente.
"""
from __future__ import annotations
from dataclasses import dataclass

# ─── Registros (code.h) ──────────────────────────────────────────────────────
PC = 7    # contador del programa
MP = 6    # "memory pointer": apunta al tope de la memoria; ahí se guardan los temporales
GP = 5    # "global pointer": apunta al inicio de la memoria; ahí están las variables
AC = 0    # acumulador
AC1 = 1   # segundo acumulador
AC2 = 2   # tercer registro: TINY no lo usa; aquí lo usan %, ^, && y ||

# ─── Límites del simulador (tm.c) ────────────────────────────────────────────
IADDR_SIZE = 1024   # memoria de instrucciones
DADDR_SIZE = 1024   # memoria de datos

# Instrucciones de solo registros (RO); las demás son registro-memoria (RM / RA).
# INR (leer un real), DIVR (división real), OUTC (escribir un carácter), OUTN (escribir un
# número sin terminar la línea) y POW (potencia real) son la extensión de TM/tm.c.
OPS_RO = frozenset({"HALT", "IN", "OUT", "ADD", "SUB", "MUL", "DIV",
                    "INR", "DIVR", "OUTC", "OUTN", "POW"})


@dataclass(frozen=True)
class Instruccion:
    direccion: int
    op: str
    r: int
    s: int | str   # RO: segundo registro.  RM: desplazamiento d ("7.59" en un LDC real)
    t: int         # RO: tercer registro.   RM: registro base
    comentario: str = ""

    @property
    def es_ro(self) -> bool:
        return self.op in OPS_RO

    def operandos(self) -> str:
        if self.es_ro:
            return f"{self.r},{self.s},{self.t}"
        return f"{self.r},{self.s}({self.t})"

    def texto(self) -> str:
        return f"{self.direccion:3d}:  {self.op:>5}  {self.operandos()} \t{self.comentario}"


class Emisor:
    """Lleva el archivo .tm que se está escribiendo (las variables globales de code.c)."""

    def __init__(self) -> None:
        self.lineas: list[str] = []                       # el archivo, en orden de escritura
        self.instrucciones: dict[int, Instruccion] = {}   # dirección → instrucción
        self._emit_loc = 0        # dirección de la siguiente instrucción (emitLoc)
        self._high_emit_loc = 0   # dirección más alta usada hasta ahora (highEmitLoc)

    @property
    def total(self) -> int:
        """Cuántas direcciones de instrucción ocupa el programa."""
        return self._high_emit_loc

    def emit_comment(self, comentario: str) -> None:
        self.lineas.append(f"* {comentario}")

    def emit_ro(self, op: str, r: int, s: int, t: int, comentario: str = "") -> None:
        """Instrucción de solo registros: op r,s,t."""
        self._escribir(Instruccion(self._emit_loc, op, r, s, t, comentario))

    def emit_rm(self, op: str, r: int, d: int | str, s: int, comentario: str = "") -> None:
        """Instrucción registro-memoria: op r,d(s). `d` es texto solo en un LDC con decimales."""
        self._escribir(Instruccion(self._emit_loc, op, r, d, s, comentario))

    def emit_skip(self, cuantas: int) -> int:
        """Aparta `cuantas` direcciones para completarlas después; devuelve la primera.
        emit_skip(0) solo consulta la dirección actual."""
        loc = self._emit_loc
        self._emit_loc += cuantas
        self._high_emit_loc = max(self._high_emit_loc, self._emit_loc)
        return loc

    def emit_backup(self, loc: int) -> None:
        """Regresa a una dirección apartada con emit_skip."""
        if loc > self._high_emit_loc:
            raise ValueError(f"emit_backup a una dirección que no se ha apartado: {loc}")
        self._emit_loc = loc

    def emit_restore(self) -> None:
        """Vuelve a la siguiente dirección libre después de un emit_backup."""
        self._emit_loc = self._high_emit_loc

    def emit_rm_abs(self, op: str, r: int, a: int, comentario: str = "") -> None:
        """Salto a la dirección absoluta `a`, escrito relativo al pc."""
        self.emit_rm(op, r, a - (self._emit_loc + 1), PC, comentario)

    def _escribir(self, instruccion: Instruccion) -> None:
        self.instrucciones[instruccion.direccion] = instruccion
        self.lineas.append(instruccion.texto())
        self._emit_loc += 1
        self._high_emit_loc = max(self._high_emit_loc, self._emit_loc)
