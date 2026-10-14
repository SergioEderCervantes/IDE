"""Tipos del lenguaje y reglas de compatibilidad (GRAMATICA.md, sección 8).

Las funciones de este módulo solo deciden tipos: el tipo resultante, si algún
operando necesita la conversión implícita int → float y, si la combinación no es
válida, el mensaje de error. El recorrido del AST está en analyzer.py.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Tipo(str, Enum):
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    # Tipo interno de una expresión con error: evita reportar errores en cascada
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


NUMERICOS = {Tipo.INT, Tipo.FLOAT}

# Palabra reservada de una declaración → tipo declarado
TIPO_DE_DECLARACION = {"KW_INT": Tipo.INT, "KW_FLOAT": Tipo.FLOAT, "KW_BOOL": Tipo.BOOL}

# Literal → tipo
TIPO_DE_LITERAL = {
    "INTEGER": Tipo.INT,
    "REAL": Tipo.FLOAT,
    "KW_TRUE": Tipo.BOOL,
    "KW_FALSE": Tipo.BOOL,
}

# Operadores agrupados por regla
ARITMETICOS = {"OP_PLUS", "OP_MINUS", "OP_MULTIPLY", "OP_DIVIDE", "OP_POWER"}
MODULO = {"OP_MODULO"}
RELACIONALES = {"OP_LT", "OP_LE", "OP_GT", "OP_GE"}
IGUALDAD = {"OP_EQ", "OP_NE"}
LOGICOS = {"OP_AND", "OP_OR"}
OPERADORES_BINARIOS = ARITMETICOS | MODULO | RELACIONALES | IGUALDAD | LOGICOS

NEGACION_LOGICA = {"OP_NOT"}
NUMERICOS_UNARIOS = {"OP_NEG", "OP_INCREMENT", "OP_DECREMENT"}
OPERADORES_UNARIOS = NEGACION_LOGICA | NUMERICOS_UNARIOS


@dataclass(frozen=True)
class Resultado:
    """Resultado de verificar una operación o asignación.

    convertir_izq / convertir_der indican qué operando lleva el nodo CONV int→float.
    """
    tipo: Tipo
    error: Optional[str] = None
    convertir_izq: bool = False
    convertir_der: bool = False


def _promover(izq: Tipo, der: Tipo, tipo_resultado: Optional[Tipo] = None) -> Resultado:
    """Dos números: si alguno es float, el otro (int) se convierte a float."""
    comun = Tipo.FLOAT if Tipo.FLOAT in (izq, der) else Tipo.INT
    return Resultado(
        tipo=tipo_resultado or comun,
        convertir_izq=(comun == Tipo.FLOAT and izq == Tipo.INT),
        convertir_der=(comun == Tipo.FLOAT and der == Tipo.INT),
    )


def operacion_binaria(op: str, simbolo: str, izq: Tipo, der: Tipo) -> Resultado:
    """Tipo de `izq <op> der`. `op` es el tipo de nodo (OP_PLUS, ...) y `simbolo` el lexema."""
    if Tipo.ERROR in (izq, der):
        return Resultado(Tipo.ERROR)

    numericos = izq in NUMERICOS and der in NUMERICOS

    if op in ARITMETICOS:
        if numericos:
            return _promover(izq, der)
        return _uso_indebido(simbolo, izq, der)

    if op in MODULO:
        if izq == Tipo.INT and der == Tipo.INT:
            return Resultado(Tipo.INT)
        return Resultado(
            Tipo.ERROR,
            f"uso indebido del operador '{simbolo}': solo se aplica a int, "
            f"se recibió {izq} y {der}",
        )

    if op in RELACIONALES:
        if numericos:
            return _promover(izq, der, Tipo.BOOL)
        return _uso_indebido(simbolo, izq, der)

    if op in IGUALDAD:
        if numericos:
            return _promover(izq, der, Tipo.BOOL)
        if izq == Tipo.BOOL and der == Tipo.BOOL:
            return Resultado(Tipo.BOOL)
        return Resultado(
            Tipo.ERROR,
            f"incompatibilidad de tipos: no se puede comparar {izq} con {der} usando '{simbolo}'",
        )

    if op in LOGICOS:
        if izq == Tipo.BOOL and der == Tipo.BOOL:
            return Resultado(Tipo.BOOL)
        return _uso_indebido(simbolo, izq, der)

    raise ValueError(f"Operador binario desconocido: {op}")


def operacion_unaria(op: str, simbolo: str, operando: Tipo) -> Resultado:
    """Tipo de `!x`, `-x`, `x++`, `x--`."""
    if operando == Tipo.ERROR:
        return Resultado(Tipo.ERROR)

    if op in NEGACION_LOGICA:
        if operando == Tipo.BOOL:
            return Resultado(Tipo.BOOL)
        return Resultado(
            Tipo.ERROR,
            f"uso indebido del operador '{simbolo}': solo se aplica a bool, se recibió {operando}",
        )

    if op in NUMERICOS_UNARIOS:
        if operando in NUMERICOS:
            return Resultado(operando)
        return Resultado(
            Tipo.ERROR,
            f"uso indebido del operador '{simbolo}': solo se aplica a int o float, "
            f"se recibió {operando}",
        )

    raise ValueError(f"Operador unario desconocido: {op}")


def asignacion(nombre: str, destino: Tipo, origen: Tipo) -> Resultado:
    """¿Se puede asignar un valor de tipo `origen` a la variable `nombre` de tipo `destino`?"""
    if Tipo.ERROR in (destino, origen) or destino == origen:
        return Resultado(destino)

    if destino == Tipo.FLOAT and origen == Tipo.INT:
        return Resultado(destino, convertir_der=True)

    if destino == Tipo.INT and origen == Tipo.FLOAT:
        return Resultado(
            Tipo.ERROR,
            f"conversión no válida: no se puede asignar un valor float a '{nombre}' (int) "
            f"porque se perderían los decimales",
        )

    return Resultado(
        Tipo.ERROR,
        f"inconsistencia de tipos en la asignación: no se puede asignar un valor {origen} "
        f"a '{nombre}' ({destino})",
    )


def condicion(estructura: str, tipo: Tipo) -> Optional[str]:
    """Mensaje de error si la condición de `estructura` (if, while, until) no es bool."""
    if tipo in (Tipo.BOOL, Tipo.ERROR):
        return None
    return f"la condición de '{estructura}' debe ser bool, se obtuvo {tipo}"


def _uso_indebido(simbolo: str, izq: Tipo, der: Tipo) -> Resultado:
    return Resultado(
        Tipo.ERROR,
        f"uso indebido del operador '{simbolo}': no se puede aplicar a {izq} y {der}",
    )
