"""Analizador semántico: recorre el AST, construye la tabla de símbolos, calcula y
propaga atributos, verifica tipos y reporta errores (GRAMATICA.md, secciones 6 a 9).

El AST original no se modifica: se anota una copia. En la copia, cada nodo guarda sus
atributos en `node.attrs`:

  - dtype  (heredado)     tipo declarado, baja de la declaración a cada identificador
  - dir                   dirección asignada en la tabla de símbolos (memloc)
  - tipo   (sintetizado)  tipo de literales, identificadores y expresiones
  - valor  (sintetizado)  en expresiones cuyo valor se conoce en compilación

Las conversiones implícitas int → float se insertan como nodos explícitos CONV.

Valores de las variables: el analizador recuerda el último valor conocido de cada
variable (`self._valores`), así `y = 2 + 3; z = y + 7;` da z = 12 y el valor sube por la
expresión hasta la asignación. Solo se guarda un valor cuando es seguro en cualquier
ejecución:
  - cin >> x, o asignar una expresión sin valor, deja a x sin valor
  - después de un if/else solo quedan los valores iguales en ambas ramas
  - en un ciclo, las variables que se asignan en el cuerpo no tienen valor (cambian en
    cada vuelta)
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Optional

from ..errors import CompilerError, SEMANTICO
from ..parser.ast_nodes import ASTNode
from . import tipos
from .constantes import (
    ErrorConstante, error_operando_derecho, evaluar_binaria, evaluar_unaria, valor_literal,
)
from .symbol_table import SymbolTable
from .tipos import Tipo

# Nodos que solo agrupan sentencias o declaraciones
_CONTENEDORES = {"programa", "lista_declaracion", "lista_sentencias", "else_body"}


@dataclass
class SemanticResult:
    ast: ASTNode                   # copia anotada del AST
    tabla: SymbolTable
    errores: list[CompilerError]
    recorrido: list[dict]          # traza: {linea, accion, detalle}


class SemanticAnalyzer:
    def analyze(self, ast: ASTNode) -> SemanticResult:
        self._tabla = SymbolTable()
        self._errores: list[CompilerError] = []
        self._recorrido: list[dict] = []
        self._valores: dict[str, object] = {}  # nombre → último valor conocido

        anotado = copy.deepcopy(ast)
        self._traza(anotado.line, "inicio", "tabla de símbolos vacía, memloc = 0")
        self._sentencia(anotado)
        self._traza(
            None, "fin",
            f"{len(self._tabla)} símbolo(s) en la tabla, {len(self._errores)} error(es) semántico(s)",
        )
        return SemanticResult(anotado, self._tabla, self._errores, self._recorrido)

    # ─── Declaraciones y sentencias ──────────────────────────────────────────

    def _sentencia(self, node: ASTNode) -> None:
        if node.kind in _CONTENEDORES:
            for hijo in node.children:
                self._sentencia(hijo)
            return

        manejador = {
            "declaracion_variable": self._declaracion,
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
        # KW_MAIN y nodos de error (no llegan aquí si hubo errores sintácticos) se ignoran

    def _declaracion(self, node: ASTNode) -> None:
        """declaracion_variable → tipo id_list ;   id_list.dtype = tipo.tipo (heredado)"""
        nodo_tipo, id_list = node.children[0], node.children[1]
        dtype = tipos.TIPO_DE_DECLARACION.get(nodo_tipo.kind)
        if dtype is None:
            return
        nodo_tipo.attrs["tipo"] = dtype.value
        id_list.attrs["dtype"] = dtype.value

        for ident in id_list.children:
            ident.attrs["dtype"] = dtype.value
            simbolo = self._tabla.insert(ident.value, dtype, ident.line)
            if simbolo is None:
                previo = self._tabla.lookup(ident.value)
                self._error(
                    ident,
                    f"declaración duplicada: '{ident.value}' ya fue declarada en la línea "
                    f"{previo.declaracion}",
                )
                self._traza(ident.line, "insertar", f"{ident.value}: ya existe en la tabla ✗")
                continue
            ident.attrs["dir"] = simbolo.direccion
            self._traza(
                ident.line, "insertar",
                f"{ident.value}: {dtype} (dtype heredado de '{nodo_tipo.value}'), "
                f"dirección {simbolo.direccion}",
            )

    def _asignacion(self, node: ASTNode) -> None:
        ident = node.children[0]
        destino = self._identificador(ident)

        if len(node.children) < 2:
            self._error(node, f"asignación sin expresión: falta el valor que se asigna a '{ident.value}'")
            return

        origen = self._expresion(node.children[1])
        r = tipos.asignacion(ident.value, destino, origen)
        if r.convertir_der:
            node.children[1] = self._convertir(node.children[1])

        expr = node.children[1]
        valor = f" (valor {_formato(expr.attrs['valor'])})" if "valor" in expr.attrs else ""
        if r.error:
            self._error(node, r.error)
            veredicto = "✗"
        elif r.convertir_der:
            veredicto = "✓ con conversión int → float"
        else:
            veredicto = "✓"
        if Tipo.ERROR not in (destino, origen):
            node.attrs["verificacion"] = f"{destino} ← {origen} {veredicto}"
            self._traza(node.line, "asignación", f"{ident.value} ({destino}) ← {origen}{valor} {veredicto}")

        # El valor sube de la expresión a la asignación y queda guardado en la variable
        if destino != Tipo.ERROR and not r.error and "valor" in expr.attrs:
            self._asignar_valor(node, ident, expr.attrs["valor"])
        else:
            self._valores.pop(ident.value, None)

    def _incremento(self, node: ASTNode) -> None:
        ident, op = node.children[0], node.children[1]
        t = self._identificador(ident)
        r = tipos.operacion_unaria(op.kind, op.value, t)
        if r.error:
            self._error(op, r.error)
        node.attrs["tipo"] = r.tipo.value

        actual = self._valores.pop(ident.value, None)
        if r.error or actual is None:
            return
        uno = 1 if t == Tipo.INT else 1.0
        operador = "OP_PLUS" if op.kind == "OP_INCREMENT" else "OP_MINUS"
        try:
            nuevo = evaluar_binaria(operador, op.value, actual, uno, t)
        except ErrorConstante as e:
            self._error_constante(node, str(e))
            return
        if nuevo is not None:
            self._asignar_valor(node, ident, nuevo)

    def _seleccion(self, node: ASTNode) -> None:
        self._condicion("if", node, node.children[0])
        antes = dict(self._valores)
        self._sentencia(node.children[1])
        rama_then = self._valores
        self._valores = dict(antes)
        for hijo in node.children[2:]:  # else (si lo hay; sin else, la rama es "antes")
            self._sentencia(hijo)
        # Solo se conserva el valor de las variables que valen lo mismo en ambas ramas
        self._valores = {
            nombre: v for nombre, v in rama_then.items()
            if nombre in self._valores and _mismo_valor(v, self._valores[nombre])
        }

    def _iteracion(self, node: ASTNode) -> None:
        self._olvidar_en_ciclo(node, node.children[1])
        al_evaluar_condicion = dict(self._valores)
        self._condicion("while", node, node.children[0])
        self._sentencia(node.children[1])
        # Se sale del ciclo cuando la condición es falsa: mismo estado que al evaluarla
        self._valores = al_evaluar_condicion

    def _repeticion(self, node: ASTNode) -> None:
        # El cuerpo va antes que la condición en el código fuente
        self._olvidar_en_ciclo(node, node.children[0])
        self._sentencia(node.children[0])
        self._condicion("until", node, node.children[1])

    def _olvidar_en_ciclo(self, ciclo: ASTNode, cuerpo: ASTNode) -> None:
        """Las variables asignadas en el cuerpo cambian en cada vuelta: pierden su valor."""
        olvidadas = [n for n in _asignadas(cuerpo) if self._valores.pop(n, None) is not None]
        if olvidadas:
            self._traza(ciclo.line, "valores", f"sin valor dentro del ciclo: {', '.join(olvidadas)}")

    def _condicion(self, estructura: str, node: ASTNode, cond: ASTNode) -> None:
        t = self._expresion(cond)
        error = tipos.condicion(estructura, t)
        if error:
            self._error(cond, error)
        if t != Tipo.ERROR:
            veredicto = "✗" if error else "✓"
            node.attrs["verificacion"] = f"condición {t} {veredicto}"
            self._traza(cond.line, "condición", f"{estructura}: {t} {veredicto}")

    def _sent_in(self, node: ASTNode) -> None:
        self._identificador(node.children[0])
        self._valores.pop(node.children[0].value, None)  # el valor se lee al ejecutar

    def _sent_out(self, node: ASTNode) -> None:
        salida = node.children[0]
        for elemento in salida.children:
            if elemento.kind != "STRING_LITERAL":
                self._expresion(elemento)

    # ─── Expresiones ─────────────────────────────────────────────────────────

    def _expresion(self, node: ASTNode) -> Tipo:
        """Calcula y anota el tipo (y el valor si es constante). Devuelve el tipo."""
        if node.kind in tipos.TIPO_DE_LITERAL:
            return self._literal(node)

        if node.kind == "IDENTIFIER":
            t = self._identificador(node)
            if t != Tipo.ERROR and node.value in self._valores:
                node.attrs["valor"] = self._valores[node.value]
            return t

        if node.kind in tipos.OPERADORES_UNARIOS and len(node.children) == 1:
            return self._unaria(node)

        if node.kind in tipos.OPERADORES_BINARIOS and len(node.children) == 2:
            return self._binaria(node)

        # Nodo de error u otra forma que solo aparece con errores sintácticos
        node.attrs["tipo"] = Tipo.ERROR.value
        return Tipo.ERROR

    def _literal(self, node: ASTNode, permitir_minimo: bool = False) -> Tipo:
        """Literal: tipo según su clase y valor = el literal (si está en el rango del tipo)."""
        tipo = tipos.TIPO_DE_LITERAL[node.kind]
        node.attrs["tipo"] = tipo.value
        try:
            node.attrs["valor"] = valor_literal(node.kind, node.value, permitir_minimo)
        except ErrorConstante as e:
            self._error(node, str(e))
        return tipo

    def _unaria(self, node: ASTNode) -> Tipo:
        operando = node.children[0]
        if node.kind == "OP_NEG" and operando.kind == "INTEGER":
            t = self._literal(operando, permitir_minimo=True)  # -2147483648
        else:
            t = self._expresion(operando)
        r = tipos.operacion_unaria(node.kind, node.value, t)
        if r.error:
            self._error(node, r.error)
        node.attrs["tipo"] = r.tipo.value
        if r.tipo != Tipo.ERROR and "valor" in operando.attrs:
            try:
                valor = evaluar_unaria(node.kind, operando.attrs["valor"])
            except ErrorConstante as e:
                return self._error_constante(node, str(e))
            if valor is not None:
                node.attrs["valor"] = valor
        return r.tipo

    def _binaria(self, node: ASTNode) -> Tipo:
        ti = self._expresion(node.children[0])
        td = self._expresion(node.children[1])
        r = tipos.operacion_binaria(node.kind, node.value, ti, td)
        if r.error:
            self._error(node, r.error)
        if r.convertir_izq:
            node.children[0] = self._convertir(node.children[0])
        if r.convertir_der:
            node.children[1] = self._convertir(node.children[1])
        node.attrs["tipo"] = r.tipo.value

        if r.tipo == Tipo.ERROR:
            return r.tipo

        # El tipo de los operandos (no el del resultado) decide la aritmética: en
        # 7 / 2 > 3 la división es entera aunque la comparación dé bool.
        izq, der = node.children
        tipo_operandos = Tipo(izq.attrs["tipo"])

        # Basta con que el operando derecho sea constante: x / 0 y x ^ -1 se detectan aunque
        # x sea una variable
        if "valor" in der.attrs:
            error = error_operando_derecho(node.kind, node.value, tipo_operandos, der.attrs["valor"])
            if error:
                return self._error_constante(node, error)

        if "valor" in izq.attrs and "valor" in der.attrs:
            try:
                valor = evaluar_binaria(node.kind, node.value, izq.attrs["valor"],
                                        der.attrs["valor"], tipo_operandos)
            except ErrorConstante as e:
                return self._error_constante(node, str(e))
            if valor is not None:
                node.attrs["valor"] = valor
        return r.tipo

    def _error_constante(self, node: ASTNode, mensaje: str) -> Tipo:
        """Expresión constante inválida (división entre cero, desbordamiento, ...)."""
        self._error(node, mensaje)
        node.attrs["tipo"] = Tipo.ERROR.value
        return Tipo.ERROR

    def _identificador(self, ident: ASTNode) -> Tipo:
        """Uso de un identificador: búsqueda en la tabla de símbolos."""
        simbolo = self._tabla.lookup(ident.value)
        if simbolo is None:
            self._error(ident, f"identificador no declarado: '{ident.value}'")
            self._traza(ident.line, "buscar", f"{ident.value} → no está en la tabla ✗")
            ident.attrs["tipo"] = Tipo.ERROR.value
            return Tipo.ERROR
        self._tabla.add_reference(ident.value, ident.line)
        ident.attrs["tipo"] = simbolo.tipo.value
        ident.attrs["dir"] = simbolo.direccion
        self._traza(ident.line, "buscar", f"{ident.value} → {simbolo.tipo}, dirección {simbolo.direccion}")
        return simbolo.tipo

    def _asignar_valor(self, node: ASTNode, ident: ASTNode, valor) -> None:
        """Guarda el nuevo valor de la variable y lo anota en la sentencia y en su destino."""
        self._valores[ident.value] = valor
        ident.attrs["valor"] = valor
        node.attrs["valor"] = valor
        self._traza(node.line, "valores", f"{ident.value} = {_formato(valor)}")

    def _convertir(self, node: ASTNode) -> ASTNode:
        """Envuelve `node` (int) en un nodo explícito CONV int→float."""
        conv = ASTNode(kind="CONV", value="int→float", line=node.line, col=node.col, children=[node])
        conv.attrs["tipo"] = Tipo.FLOAT.value
        if "valor" in node.attrs:
            conv.attrs["valor"] = float(node.attrs["valor"])
        self._traza(node.line, "conversión", f"{_describir(node)}: int → float")
        return conv

    # ─── Registro ────────────────────────────────────────────────────────────

    def _error(self, node: ASTNode, mensaje: str) -> None:
        self._errores.append(CompilerError(SEMANTICO, mensaje, node.line, node.col))

    def _traza(self, linea: Optional[int], accion: str, detalle: str) -> None:
        self._recorrido.append({"linea": linea, "accion": accion, "detalle": detalle})


def _asignadas(node: ASTNode) -> list[str]:
    """Variables que se modifican (asignación, ++/--, cin) dentro de `node`, sin repetir."""
    nombres: list[str] = []
    pendientes = [node]
    while pendientes:  # iterativo: el anidamiento puede ser muy profundo
        actual = pendientes.pop()
        if actual.kind in ("asignacion", "incremento", "sent_in") and actual.children:
            nombre = actual.children[0].value
            if nombre not in nombres:
                nombres.append(nombre)
        pendientes.extend(reversed(actual.children))
    return nombres


def _mismo_valor(a, b) -> bool:
    return type(a) is type(b) and a == b


def _describir(node: ASTNode) -> str:
    """Texto corto de un nodo para la traza: el lexema o el operador."""
    if node.children:
        return f"expresión '{node.value}' (col {node.col})"
    return f"'{node.value}' (col {node.col})"


def _formato(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    return str(valor)
