"""Instrucciones del código intermedio de tres direcciones.

Cada instrucción es un cuádruplo (op, arg1, arg2, resultado). Su texto sigue el formato
del archivo .ci del TINY de la materia (Tiny_Intermedio_TM, intermedio.c), con las
instrucciones que agrega nuestro lenguaje:

    read x                  lectura (cin)
    write a                 escritura (cout); con dos elementos: write "texto", a
    x = a                   copia
    t1 = a + b              operación binaria (+ - * / % ^ < <= > >= == != && ||)
    t1 = -a                 menos unario
    t1 = !a                 negación lógica
    t1 = (float) a          conversión int → float
    if_false a goto L1      salta a L1 si a es false
    goto L1                 salto incondicional
    label L1                etiqueta
    halt                    fin del programa
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union

Valor = Union[int, float, bool, str]

# Clases de operando
VARIABLE = "variable"
TEMPORAL = "temporal"
CONSTANTE = "constante"
CADENA = "cadena"
ETIQUETA = "etiqueta"

# Operaciones (campo `op`)
READ = "read"
WRITE = "write"
COPIA = "="
NEG = "neg"           # menos unario: se escribe t1 = -a
NOT = "!"
CONV = "(float)"
IF_FALSE = "if_false"
GOTO = "goto"
LABEL = "label"
HALT = "halt"
BINARIAS = {"+", "-", "*", "/", "%", "^", "<", "<=", ">", ">=", "==", "!=", "&&", "||"}


@dataclass(frozen=True)
class Operando:
    """Argumento o resultado de un cuádruplo.

    `texto` es como se escribe en el código (x, t1, 5, 2.50, true, "hola", L1).
    `valor` es el valor de una constante (int, float, bool) o el contenido de una cadena.
    """
    texto: str
    clase: str
    valor: Optional[Valor] = None

    def __str__(self) -> str:
        return self.texto


def variable(nombre: str) -> Operando:
    return Operando(nombre, VARIABLE)


def temporal(numero: int) -> Operando:
    return Operando(f"t{numero}", TEMPORAL)


def etiqueta(numero: int) -> Operando:
    return Operando(f"L{numero}", ETIQUETA)


def constante(texto: str, valor: Valor) -> Operando:
    return Operando(texto, CONSTANTE, valor)


def cadena(contenido: str) -> Operando:
    return Operando(f'"{contenido}"', CADENA, contenido)


@dataclass(frozen=True)
class Cuadruplo:
    """Una instrucción. `tipo` es el tipo del resultado (o de la variable que se lee) y
    `linea` la línea del código fuente que la generó."""
    op: str
    arg1: Optional[Operando] = None
    arg2: Optional[Operando] = None
    resultado: Optional[Operando] = None
    tipo: Optional[str] = None
    linea: Optional[int] = None

    def texto(self) -> str:
        a, b, r = self.arg1, self.arg2, self.resultado
        if self.op == READ:
            return f"read {r}"
        if self.op == WRITE:
            return f"write {a}" if b is None else f"write {a}, {b}"
        if self.op == COPIA:
            return f"{r} = {a}"
        if self.op in BINARIAS:
            return f"{r} = {a} {self.op} {b}"
        if self.op == NEG:
            # Con un espacio si el operando ya empieza con '-': t2 = - -5
            return f"{r} = -{a}" if not a.texto.startswith("-") else f"{r} = - {a}"
        if self.op == NOT:
            return f"{r} = !{a}"
        if self.op == CONV:
            return f"{r} = (float) {a}"
        if self.op == IF_FALSE:
            return f"if_false {a} goto {r}"
        if self.op == GOTO:
            return f"goto {r}"
        if self.op == LABEL:
            return f"label {r}"
        if self.op == HALT:
            return "halt"
        raise ValueError(f"Operación desconocida: {self.op}")

    def to_dict(self) -> dict:
        def texto(o: Optional[Operando]) -> Optional[str]:
            return None if o is None else o.texto
        return {
            "op": self.op,
            "arg1": texto(self.arg1),
            "arg2": texto(self.arg2),
            "resultado": texto(self.resultado),
            "tipo": self.tipo,
            "linea": self.linea,
        }
