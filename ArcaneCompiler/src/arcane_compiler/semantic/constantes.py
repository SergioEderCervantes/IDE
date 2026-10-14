"""Cálculo del atributo `valor` de expresiones constantes.

Solo se evalúan operaciones cuyos operandos tienen valor conocido en compilación
(literales y expresiones formadas por literales). Las variables no tienen valor:
dependen de la ejecución (cin, ciclos, if).

Tamaño de los tipos:
  - int:   entero de 32 bits con signo (-2147483648 a 2147483647), como en C y Java.
           Un literal fuera de rango o un resultado constante que se desborda es error.
  - float: real de doble precisión (64 bits, IEEE 754). Si un resultado constante no es
           finito (infinito, NaN) simplemente no se le asigna valor.

La aritmética entera sigue a C: la división y el residuo truncan hacia cero
(7 / 2 = 3, -7 / 2 = -3, -7 % 2 = -1).

Este módulo es la única fuente de los errores de expresiones constantes (división entre
cero, exponente negativo, desbordamiento, literal fuera de rango); el analizador solo
los reporta.
"""
from __future__ import annotations
import math
from typing import Optional, Union
from .tipos import Tipo

Valor = Union[int, float, bool]

INT_MIN = -2 ** 31
INT_MAX = 2 ** 31 - 1

_DESBORDAMIENTO = (
    "desbordamiento en expresión constante: el resultado no cabe en int "
    f"(32 bits, de {INT_MIN} a {INT_MAX})"
)


class ErrorConstante(Exception):
    """La operación o el literal constante no es válido. El mensaje es el error semántico."""


def valor_literal(kind: str, lexema: str, permitir_minimo: bool = False) -> Valor:
    """Valor de un literal.

    `permitir_minimo` acepta 2147483648 cuando el literal va precedido de '-' unario:
    el lexer lee -2147483648 como '-' aplicado a 2147483648, y el mínimo de int debe
    poder escribirse.
    """
    if kind == "INTEGER":
        limite = INT_MAX + 1 if permitir_minimo else INT_MAX
        digitos = lexema.lstrip("0") or "0"
        # Se compara la longitud antes de convertir: Python no convierte cadenas de más
        # de 4300 dígitos a int
        if len(digitos) > len(str(limite)) or int(digitos) > limite:
            mostrado = lexema if len(lexema) <= 20 else lexema[:12] + "…"
            raise ErrorConstante(
                f"constante entera fuera de rango: {mostrado} no cabe en int "
                f"(32 bits, máximo {INT_MAX})"
            )
        return int(digitos)
    if kind == "REAL":
        valor = float(lexema)
        if not math.isfinite(valor):
            raise ErrorConstante("constante real fuera de rango: no cabe en float (64 bits)")
        return valor
    if kind == "KW_TRUE":
        return True
    if kind == "KW_FALSE":
        return False
    raise ValueError(f"No es un literal: {kind}")


def error_operando_derecho(op: str, simbolo: str, tipo: Tipo, b: Valor) -> Optional[str]:
    """Errores que se detectan conociendo solo el operando derecho (constante), aunque
    el izquierdo sea una variable: x / 0, x % 0, x ^ -1 con x int."""
    if op in ("OP_DIVIDE", "OP_MODULO") and b == 0:
        return f"división entre cero en '{simbolo}'"
    if op == "OP_POWER" and tipo == Tipo.INT and b < 0:
        return ("exponente negativo en una potencia entera: el resultado no es int "
                "(usa un operando float, por ejemplo 2.0 ^ -1)")
    return None


def evaluar_binaria(op: str, simbolo: str, a: Valor, b: Valor, tipo: Tipo) -> Optional[Valor]:
    """Valor de `a <op> b`, donde `tipo` es el tipo de los operandos (ya convertidos con
    CONV int→float si hizo falta). `simbolo` es el lexema del operador, para los mensajes.

    Devuelve None si el resultado no se puede representar (float no finito, raíz de un
    negativo). Lanza ErrorConstante si la operación es inválida.
    """
    error = error_operando_derecho(op, simbolo, tipo, b)
    if error:
        raise ErrorConstante(error)

    if op == "OP_PLUS":
        return _resultado(a + b)
    if op == "OP_MINUS":
        return _resultado(a - b)
    if op == "OP_MULTIPLY":
        return _resultado(a * b)
    if op == "OP_DIVIDE":
        return _resultado(_div_entera(a, b) if tipo == Tipo.INT else a / b)
    if op == "OP_MODULO":
        return _resultado(a - b * _div_entera(a, b))
    if op == "OP_POWER":
        return _potencia_entera(a, b) if tipo == Tipo.INT else _potencia_real(a, b, simbolo)
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


def evaluar_unaria(op: str, a: Valor) -> Optional[Valor]:
    if op == "OP_NOT":
        return not a
    if op == "OP_NEG":
        return _resultado(-a)  # -(-2147483648) se desborda
    raise ValueError(f"Operador unario desconocido: {op}")


def _resultado(valor: Valor) -> Optional[Valor]:
    """Verifica que un resultado numérico sea representable en su tipo."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        if not INT_MIN <= valor <= INT_MAX:
            raise ErrorConstante(_DESBORDAMIENTO)
        return valor
    return valor if math.isfinite(valor) else None


def _div_entera(a: int, b: int) -> int:
    """División entera truncada hacia cero, como en C."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def _potencia_entera(a: int, b: int) -> int:
    """a ^ b con b >= 0. Se multiplica paso a paso y se detiene en cuanto el resultado se
    sale del rango: nunca se calculan números gigantes."""
    if a in (-1, 0, 1):
        return a ** b  # inmediato aunque b sea enorme
    resultado = 1
    for _ in range(b):
        resultado = _resultado(resultado * a)  # con |a| >= 2 se desborda en máximo 31 pasos
    return resultado


def _potencia_real(a: float, b: float, simbolo: str) -> Optional[float]:
    if a == 0 and b < 0:
        raise ErrorConstante(
            f"división entre cero en '{simbolo}': cero elevado a un exponente negativo"
        )
    try:
        resultado = a ** b
    except OverflowError:
        return None
    if isinstance(resultado, complex):  # (-8.0) ^ 0.5 no es un número real
        return None
    return _resultado(resultado)
