"""Generación de código intermedio de tres direcciones (fase 4).

Recorre el AST anotado por el análisis semántico (con sus nodos CONV) y produce una lista
de cuádruplos. Sigue el esquema de traducción de intermedio.c del TINY de la materia
(Tiny_Intermedio_TM), así que un programa escrito igual da el mismo código, línea por
línea, con la misma numeración de temporales y etiquetas:

- Cada operación deja su resultado en un temporal nuevo (t1, t2, ...); los temporales no
  se reutilizan. Las constantes y las variables se usan directamente.
- Las expresiones se traducen en postorden: operando izquierdo, operando derecho y al
  final la operación (el temporal se numera después de traducir los operandos).
- if c then A else B end:
      if_false c goto L1 / A / goto L2 / label L1 / B / label L2
  Sin else: if_false c goto L1 / A / label L1. L1 se numera antes de traducir A y L2
  después, como en TINY.
- do A until c (el repeat de TINY): label L1 / A / if_false c goto L1
- No se usan los valores que calculó el análisis semántico: el código es el mismo aunque
  una expresión sea constante. La única excepción es el menos unario sobre un literal
  (-5), que se escribe directamente como la constante negativa.

Lo que TINY no tiene:
- while c A:  label L1 / if_false c goto L2 / A / goto L1 / label L2
- x++ y x--:  t1 = x + 1 / x = t1   (1.0 si x es float)
- CONV:       t1 = (float) a
- && y || se evalúan completos (sin cortocircuito), como cualquier operación binaria.
- cout << "texto" << e:  write "texto", t1
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from ..parser.ast_nodes import ASTNode
from ..semantic.constantes import valor_literal
from ..semantic.tipos import TIPO_DE_LITERAL
from . import cuadruplos as c
from .cuadruplos import Cuadruplo, Operando

_CONTENEDORES = {"programa", "lista_declaracion", "lista_sentencias", "else_body"}

_OPERADOR = {
    "OP_PLUS": "+", "OP_MINUS": "-", "OP_MULTIPLY": "*", "OP_DIVIDE": "/",
    "OP_MODULO": "%", "OP_POWER": "^",
    "OP_LT": "<", "OP_LE": "<=", "OP_GT": ">", "OP_GE": ">=",
    "OP_EQ": "==", "OP_NE": "!=",
    "OP_AND": "&&", "OP_OR": "||",
}

_ENCABEZADO = (
    "# CÓDIGO INTERMEDIO DE TRES DIRECCIONES\n"
    "# Generado desde el AST anotado por el análisis semántico.\n"
    "# Los temporales t1, t2... y las etiquetas L1, L2... son simbólicos.\n"
)


@dataclass
class IntermediateResult:
    cuadruplos: list[Cuadruplo]
    temporales: int   # cuántos temporales se usaron (t1 … tN)
    etiquetas: int    # cuántas etiquetas se usaron (L1 … LN)

    def texto(self) -> str:
        """El código en el formato del archivo .ci de TINY."""
        return _ENCABEZADO + "\n" + "\n".join(q.texto() for q in self.cuadruplos)


class IntermediateGenerator:
    def generate(self, ast: ASTNode) -> IntermediateResult:
        """`ast` es el AST anotado (SemanticResult.ast) de un programa sin errores."""
        self._codigo: list[Cuadruplo] = []
        self._temporales = 0
        self._etiquetas = 0
        self._sentencia(ast)
        self._emitir(c.HALT)
        return IntermediateResult(self._codigo, self._temporales, self._etiquetas)

    # ─── Sentencias ──────────────────────────────────────────────────────────

    def _sentencia(self, node: ASTNode) -> None:
        if node.kind in _CONTENEDORES:
            for hijo in node.children:
                self._sentencia(hijo)
            return

        manejador = {
            "asignacion": self._asignacion,
            "incremento": self._incremento,
            "seleccion": self._seleccion,
            "iteracion": self._iteracion,
            "repeticion": self._repeticion,
            "sent_in": self._sent_in,
            "sent_out": self._sent_out,
        }.get(node.kind)
        if manejador is not None:
            manejador(node)
        # KW_MAIN y las declaraciones no generan código (la tabla de símbolos ya tiene las
        # variables)

    def _asignacion(self, node: ASTNode) -> None:
        ident, expr = node.children[0], node.children[1]
        origen = self._expresion(expr)
        self._emitir(c.COPIA, origen, resultado=c.variable(ident.value),
                     tipo=ident.attrs.get("tipo"), linea=node.line)

    def _incremento(self, node: ASTNode) -> None:
        ident, op = node.children[0], node.children[1]
        tipo = ident.attrs.get("tipo")
        uno = c.constante("1.0", 1.0) if tipo == "float" else c.constante("1", 1)
        var = c.variable(ident.value)
        t = self._nuevo_temporal()
        self._emitir("+" if op.kind == "OP_INCREMENT" else "-", var, uno, t, tipo, node.line)
        self._emitir(c.COPIA, t, resultado=var, tipo=tipo, linea=node.line)

    def _seleccion(self, node: ASTNode) -> None:
        cond, entonces = node.children[0], node.children[1]
        sino = node.children[2] if len(node.children) > 2 else None

        r = self._expresion(cond)
        falso = self._nueva_etiqueta()
        self._emitir(c.IF_FALSE, r, resultado=falso, linea=node.line)
        self._sentencia(entonces)
        if sino is None:
            self._emitir(c.LABEL, resultado=falso)
            return
        fin = self._nueva_etiqueta()  # se numera después del then, como en TINY
        self._emitir(c.GOTO, resultado=fin)
        self._emitir(c.LABEL, resultado=falso)
        self._sentencia(sino)
        self._emitir(c.LABEL, resultado=fin)

    def _iteracion(self, node: ASTNode) -> None:
        cond, cuerpo = node.children[0], node.children[1]
        inicio = self._nueva_etiqueta()
        self._emitir(c.LABEL, resultado=inicio)
        r = self._expresion(cond)
        fin = self._nueva_etiqueta()
        self._emitir(c.IF_FALSE, r, resultado=fin, linea=node.line)
        self._sentencia(cuerpo)
        self._emitir(c.GOTO, resultado=inicio)
        self._emitir(c.LABEL, resultado=fin)

    def _repeticion(self, node: ASTNode) -> None:
        cuerpo, cond = node.children[0], node.children[1]
        inicio = self._nueva_etiqueta()
        self._emitir(c.LABEL, resultado=inicio)
        self._sentencia(cuerpo)
        r = self._expresion(cond)
        self._emitir(c.IF_FALSE, r, resultado=inicio, linea=cond.line or node.line)

    def _sent_in(self, node: ASTNode) -> None:
        ident = node.children[0]
        self._emitir(c.READ, resultado=c.variable(ident.value),
                     tipo=ident.attrs.get("tipo"), linea=node.line)

    def _sent_out(self, node: ASTNode) -> None:
        # Las expresiones se traducen en el orden en que aparecen; las cadenas van tal cual
        elementos = [
            c.cadena(e.value) if e.kind == "STRING_LITERAL" else self._expresion(e)
            for e in node.children[0].children
        ]
        segundo = elementos[1] if len(elementos) > 1 else None
        self._emitir(c.WRITE, elementos[0], segundo, linea=node.line)

    # ─── Expresiones ─────────────────────────────────────────────────────────

    def _expresion(self, node: ASTNode) -> Operando:
        """Traduce la expresión y devuelve dónde quedó su valor: una constante, una
        variable o el temporal de la última operación."""
        kind = node.kind
        if kind in TIPO_DE_LITERAL:
            return self._constante(node)
        if kind == "IDENTIFIER":
            return c.variable(node.value)
        if kind == "OP_NEG" and node.children[0].kind in ("INTEGER", "REAL"):
            return self._constante(node.children[0], negativa=True)
        if kind == "CONV":
            return self._operacion(c.CONV, node, node.children[0])
        if kind == "OP_NEG":
            return self._operacion(c.NEG, node, node.children[0])
        if kind == "OP_NOT":
            return self._operacion(c.NOT, node, node.children[0])
        if kind in _OPERADOR:
            return self._operacion(_OPERADOR[kind], node, node.children[0], node.children[1])
        raise ValueError(f"Nodo inesperado en una expresión: {kind}")

    def _operacion(self, op: str, node: ASTNode, *operandos: ASTNode) -> Operando:
        args = [self._expresion(o) for o in operandos]  # postorden: izquierdo, derecho
        t = self._nuevo_temporal()
        self._emitir(op, *args, resultado=t, tipo=node.attrs.get("tipo"), linea=node.line)
        return t

    def _constante(self, node: ASTNode, negativa: bool = False) -> Operando:
        """Literal → constante. Los enteros se escriben normalizados (007 → 7, como TINY);
        los reales, como están en el código fuente."""
        valor = node.attrs.get("valor")
        if valor is None:  # el análisis semántico anota todos los literales válidos
            valor = valor_literal(node.kind, node.value, permitir_minimo=negativa)
        if node.kind == "INTEGER":
            texto = str(valor)
        elif node.kind == "REAL":
            texto = node.value
        else:
            texto = "true" if valor else "false"
        if negativa:
            return c.constante("-" + texto, -valor)
        return c.constante(texto, valor)

    # ─── Emisión ─────────────────────────────────────────────────────────────

    def _nuevo_temporal(self) -> Operando:
        self._temporales += 1
        return c.temporal(self._temporales)

    def _nueva_etiqueta(self) -> Operando:
        self._etiquetas += 1
        return c.etiqueta(self._etiquetas)

    def _emitir(self, op: str, arg1: Optional[Operando] = None, arg2: Optional[Operando] = None,
                resultado: Optional[Operando] = None, tipo: Optional[str] = None,
                linea: Optional[int] = None) -> None:
        self._codigo.append(Cuadruplo(op, arg1, arg2, resultado, tipo, linea))
