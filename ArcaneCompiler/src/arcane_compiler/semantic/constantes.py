"""Cálculo del atributo `valor` de expresiones constantes.

Solo se evalúan operaciones cuyos operandos tienen valor conocido en compilación
(literales y expresiones formadas por literales). Las variables no tienen valor:
dependen de la ejecución (cin, ciclos, if).

La aritmética entera sigue a C: la división y el residuo truncan hacia cero
(7 / 2 = 3, -7 / 2 = -3, -7 % 2 = -1).
"""
from __future__ import annotations
from typing import Optional, Union
from .tipos import Tipo

Valor = Union[int, float, bool]

# Exponente máximo que se evalúa en compilación (evita calcular números gigantes)
_MAX_EXPONENTE = 1000


class DivisionEntreCero(Exception):
    pass


class ExponenteNegativo(Exception):
    pass


def valor_literal(kind: str, lexema: str) -> Valor:
    if kind == "INTEGER":
        return int(lexema)
    if kind == "REAL":
        return float(lexema)
    if kind == "KW_TRUE":
        return True
    if kind == "KW_FALSE":
        return False
    raise ValueError(f"No es un literal: {kind}")


def evaluar_binaria(op: str, a: Valor, b: Valor, tipo: Tipo) -> Optional[Valor]:
    """Valor de `a <op> b` cuyo resultado es de tipo `tipo`.

    Los operandos ya vienen convertidos (CONV int→float aplicado). Devuelve None si el
    valor no se puede representar (p. ej. una raíz de un número negativo).
    Lanza DivisionEntreCero o ExponenteNegativo si la operación es inválida.
    """
    if op == "OP_PLUS":
        return a + b
    if op == "OP_MINUS":
        return a - b
    if op == "OP_MULTIPLY":
        return a * b
    if op == "OP_DIVIDE":
        if b == 0:
            raise DivisionEntreCero()
        return _div_entera(a, b) if tipo == Tipo.INT else a / b
    if op == "OP_MODULO":
        if b == 0:
            raise DivisionEntreCero()
        return a - b * _div_entera(a, b)
    if op == "OP_POWER":
        return _potencia(a, b, tipo)
    if op == "OP_LT":
        return a < b
    if op == "OP_LE":
        return a <= b
    if op == "OP_GT":
        return a > b
    if op == "OP_GE":
        return a >= b
    if op == "OP_EQ":
        return a == b
    if op == "OP_NE":
        return a != b
    if op == "OP_AND":
        return a and b
    if op == "OP_OR":
        return a or b
    raise ValueError(f"Operador binario desconocido: {op}")


def evaluar_unaria(op: str, a: Valor) -> Valor:
    if op == "OP_NOT":
        return not a
    if op == "OP_NEG":
        return -a
    raise ValueError(f"Operador unario desconocido: {op}")


def _div_entera(a: int, b: int) -> int:
    """División entera truncada hacia cero, como en C."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def _potencia(a: Valor, b: Valor, tipo: Tipo) -> Optional[Valor]:
    if tipo == Tipo.INT and b < 0:
        raise ExponenteNegativo()
    if abs(b) > _MAX_EXPONENTE:
        return None
    try:
        resultado = a ** b
    except (OverflowError, ZeroDivisionError):
        return None
    if isinstance(resultado, complex):  # (-8.0) ^ 0.5 no es un número real
        return None
    return resultado
