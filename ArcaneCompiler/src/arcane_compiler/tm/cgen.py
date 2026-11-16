"""Generación de código para la máquina TM: el equivalente de cgen.h y cgen.c del TINY de la
materia (entrega final).

Recorre el AST anotado por el análisis semántico: el mismo árbol del que sale el código de
tres direcciones (.ci). Son dos caminos paralelos; la TM no lee el .ci. Las direcciones de
las variables salen de la tabla de símbolos (st_lookup en TINY).

Sigue el esquema de cgen.c, así que un programa de TINY escrito en nuestro lenguaje da el
mismo .tm que el tiny.exe de la maestra, línea por línea:

- Una constante se carga con LDC y una variable con LD desde su dirección (base gp).
- Una operación binaria evalúa el operando izquierdo, lo guarda en un temporal en el tope
  de la memoria (base mp), evalúa el derecho en ac, recupera el izquierdo en ac1 y opera:
  ac = ac1 op ac.
- Una comparación resta los operandos y salta según el signo para dejar 1 o 0 en ac.
- if:     condición / JEQ al else / then / LDA al final / else. Los dos saltos se apartan
          con emit_skip y se completan con emit_backup cuando se conoce su destino.
- repeat: cuerpo / condición / JEQ de regreso al cuerpo (nuestro do … until).

Lo que TINY no tiene (la tabla completa está en GRAMATICA.md §12):
- <=, >, >=, != con JLE, JGT, JGE, JNE (mismo esquema que < y ==).
- % y ^ no existen en la TM: % se calcula como izq - (izq / der) * der y ^ con un ciclo
  de multiplicaciones. Usan el registro 2 (ac2), que TINY deja libre.
- &&, || y ! dejan 1 o 0 en ac comparando con cero; se evalúan completos, sin cortocircuito.
- -x es 0 - x; un literal negativo (-5) se carga directo con LDC.
- while:  condición / JEQ a la salida / cuerpo / LDA de regreso a la condición.
- x++ / x--: LD, LDA ac,±1(ac), ST.
- true y false son 1 y 0.

Reales (float). TM/tm.c está extendido: registros y memoria son reales, LDC acepta
decimales, INR lee un real y DIVR divide sin truncar. Por eso:
- Un literal real se carga con LDC (LDC 0,7.59(0)).
- La división entre floats es DIVR; entre ints sigue siendo DIV, que trunca.
- cin de una variable float es INR; de int o bool, IN (solo acepta enteros).
- CONV (int → float) no genera instrucciones: el valor ya es el mismo número.
- ^ con resultado float acepta exponente negativo: al final calcula 1 / resultado.

Lo que la TM no puede hacer, y por eso se informa en lugar de generarse:
- ^ con exponente float (2.0 ^ 0.5): el ciclo solo sabe multiplicar un número entero de
  veces. Es un error de generación.
- OUT solo imprime números: el texto de un cout se omite con un aviso.
- El simulador tiene 1024 direcciones de instrucciones y 1024 de datos.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from ..errors import CompilerError, GENERACION
from ..parser.ast_nodes import ASTNode
from ..semantic.constantes import valor_literal
from ..semantic.symbol_table import SymbolTable
from .code import AC, AC1, AC2, AC3, DADDR_SIZE, GP, IADDR_SIZE, MP, PC, Emisor, Instruccion

_CONTENEDORES = {"programa", "lista_declaracion", "lista_sentencias", "else_body"}

# Operadores que la TM tiene como instrucción
_ARITMETICOS = {
    "OP_PLUS": ("ADD", "+"), "OP_MINUS": ("SUB", "-"),
    "OP_MULTIPLY": ("MUL", "*"), "OP_DIVIDE": ("DIV", "/"),
}
# Comparaciones: ac = izq - der y se salta según el signo del resultado
_COMPARACIONES = {
    "OP_LT": ("JLT", "<"), "OP_LE": ("JLE", "<="), "OP_GT": ("JGT", ">"),
    "OP_GE": ("JGE", ">="), "OP_EQ": ("JEQ", "=="), "OP_NE": ("JNE", "!="),
}
_BINARIOS = set(_ARITMETICOS) | set(_COMPARACIONES) | {"OP_MODULO", "OP_POWER", "OP_AND", "OP_OR"}


@dataclass
class TMResult:
    lineas: list[str] = field(default_factory=list)                  # el archivo .tm
    instrucciones: list[Instruccion] = field(default_factory=list)   # ordenadas por dirección
    errores: list[CompilerError] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def texto(self) -> str:
        """El contenido del archivo .tm ('' si hubo errores)."""
        return "\n".join(self.lineas) + "\n" if self.lineas else ""


class TMGenerator:
    def generate(self, ast: ASTNode, tabla: SymbolTable, archivo: str = "programa.tm") -> TMResult:
        """`ast` es el AST anotado de un programa sin errores semánticos y `tabla` su tabla
        de símbolos. `archivo` solo se escribe en el comentario del encabezado."""
        self._tabla = tabla
        self._e = Emisor()
        self._tmp_offset = 0   # siguiente temporal libre, relativo a mp (tmpOffset)
        self._temporales = 0   # cuántos temporales llegan a estar ocupados a la vez
        self._avisos: list[str] = []
        self._errores: list[CompilerError] = []

        e = self._e
        e.emit_comment("TINY Compilation to TM Code")
        e.emit_comment(f"File: {archivo}")
        e.emit_comment("Standard prelude:")
        e.emit_rm("LD", MP, 0, AC, "load maxaddress from location 0")
        e.emit_rm("ST", AC, 0, AC, "clear location 0")
        e.emit_comment("End of standard prelude.")
        self._cgen(ast)
        e.emit_comment("End of execution.")
        e.emit_ro("HALT", 0, 0, 0, "")

        errores = self._errores + self._limites()
        if errores:
            return TMResult(errores=errores, avisos=self._avisos)
        instrucciones = [e.instrucciones[d] for d in sorted(e.instrucciones)]
        return TMResult(list(e.lineas), instrucciones, [], self._avisos)

    # ─── Sentencias (genStmt) ────────────────────────────────────────────────

    def _cgen(self, node: ASTNode) -> None:
        if node.kind in _CONTENEDORES:  # las sentencias hermanas (sibling en TINY)
            for hijo in node.children:
                self._cgen(hijo)
            return
        manejador = {
            "seleccion": self._if,
            "repeticion": self._repeat,
            "iteracion": self._while,
            "asignacion": self._assign,
            "incremento": self._incremento,
            "sent_in": self._read,
            "sent_out": self._write,
        }.get(node.kind)
        if manejador is not None:
            manejador(node)
        # KW_MAIN y las declaraciones no generan código: la tabla ya tiene las direcciones

    def _if(self, node: ASTNode) -> None:
        """IfK."""
        e = self._e
        cond, entonces = node.children[0], node.children[1]
        sino = node.children[2] if len(node.children) > 2 else None
        e.emit_comment("-> if")
        self._exp(cond)
        salto_else = e.emit_skip(1)
        e.emit_comment("if: jump to else belongs here")
        self._cgen(entonces)
        salto_fin = e.emit_skip(1)
        e.emit_comment("if: jump to end belongs here")
        actual = e.emit_skip(0)
        e.emit_backup(salto_else)
        e.emit_rm_abs("JEQ", AC, actual, "if: jmp to else")
        e.emit_restore()
        if sino is not None:
            self._cgen(sino)
        actual = e.emit_skip(0)
        e.emit_backup(salto_fin)
        e.emit_rm_abs("LDA", PC, actual, "jmp to end")
        e.emit_restore()
        e.emit_comment("<- if")

    def _repeat(self, node: ASTNode) -> None:
        """RepeatK: do … until c repite el cuerpo mientras c sea falsa (0)."""
        e = self._e
        cuerpo, cond = node.children[0], node.children[1]
        e.emit_comment("-> repeat")
        inicio = e.emit_skip(0)
        e.emit_comment("repeat: jump after body comes back here")
        self._cgen(cuerpo)
        self._exp(cond)
        e.emit_rm_abs("JEQ", AC, inicio, "repeat: jmp back to body")
        e.emit_comment("<- repeat")

    def _while(self, node: ASTNode) -> None:
        """No existe en TINY: se evalúa la condición antes de cada vuelta."""
        e = self._e
        cond, cuerpo = node.children[0], node.children[1]
        e.emit_comment("-> while")
        inicio = e.emit_skip(0)
        e.emit_comment("while: aquí regresa al final de cada vuelta")
        self._exp(cond)
        salto_salida = e.emit_skip(1)
        e.emit_comment("while: el salto de salida va aquí")
        self._cgen(cuerpo)
        e.emit_rm_abs("LDA", PC, inicio, "while: regresa a la condición")
        actual = e.emit_skip(0)
        e.emit_backup(salto_salida)
        e.emit_rm_abs("JEQ", AC, actual, "while: sale si la condición es falsa")
        e.emit_restore()
        e.emit_comment("<- while")

    def _assign(self, node: ASTNode) -> None:
        """AssignK."""
        e = self._e
        ident, expr = node.children[0], node.children[1]
        e.emit_comment("-> assign")
        self._exp(expr)
        e.emit_rm("ST", AC, self._st_lookup(ident), GP, "assign: store value")
        e.emit_comment("<- assign")

    def _incremento(self, node: ASTNode) -> None:
        """x++ / x--: no existe en TINY. LDA ac,1(ac) calcula ac + 1 sin otra constante."""
        e = self._e
        ident, op = node.children[0], node.children[1]
        signo, paso = ("+", 1) if op.kind == "OP_INCREMENT" else ("-", -1)
        loc = self._st_lookup(ident)
        e.emit_comment(f"-> {signo}{signo}")
        e.emit_rm("LD", AC, loc, GP, "load id value")
        e.emit_rm("LDA", AC, paso, AC, f"{signo}{signo}: ac = ac {signo} 1")
        e.emit_rm("ST", AC, loc, GP, f"{signo}{signo}: store value")
        e.emit_comment(f"<- {signo}{signo}")

    def _read(self, node: ASTNode) -> None:
        """ReadK. Una variable float se lee con INR (extensión); IN solo acepta enteros."""
        e = self._e
        ident = node.children[0]
        if ident.attrs.get("tipo") == "float":
            e.emit_ro("INR", AC, 0, 0, "read real value")
        else:
            e.emit_ro("IN", AC, 0, 0, "read integer value")
        e.emit_rm("ST", AC, self._st_lookup(ident), GP, "read: store value")

    def _write(self, node: ASTNode) -> None:
        """WriteK, una vez por cada expresión del cout."""
        e = self._e
        for elemento in node.children[0].children:
            if elemento.kind == "STRING_LITERAL":
                e.emit_comment(f'cout: se omite el texto "{elemento.value}" (OUT solo imprime números)')
                self._avisos.append(
                    f'Línea {elemento.line}: la TM solo imprime números, así que se omitió '
                    f'el texto "{elemento.value}" del cout.'
                )
                continue
            self._exp(elemento)
            e.emit_ro("OUT", AC, 0, 0, "write ac")

    # ─── Expresiones (genExp): el resultado queda en ac ─────────────────────────

    def _exp(self, node: ASTNode) -> None:
        e = self._e
        kind = node.kind
        if kind in ("INTEGER", "REAL", "KW_TRUE", "KW_FALSE") or (
                kind == "OP_NEG" and node.children[0].kind in ("INTEGER", "REAL")):
            e.emit_comment("-> Const")
            e.emit_rm("LDC", AC, _constante(node), 0, "load const")
            e.emit_comment("<- Const")
        elif kind == "CONV":
            # int → float: en la TM extendida un entero ya es un número real
            self._exp(node.children[0])
            e.emit_comment("CONV int -> float: el valor no cambia")
        elif kind == "IDENTIFIER":
            e.emit_comment("-> Id")
            e.emit_rm("LD", AC, self._st_lookup(node), GP, "load id value")
            e.emit_comment("<- Id")
        elif kind == "OP_NEG":
            e.emit_comment("-> Op")
            self._exp(node.children[0])
            e.emit_rm("LDC", AC1, 0, 0, "op - unario: ac1 = 0")
            e.emit_ro("SUB", AC, AC1, AC, "op - unario: ac = 0 - ac")
            e.emit_comment("<- Op")
        elif kind == "OP_NOT":
            e.emit_comment("-> Op")
            self._exp(node.children[0])
            e.emit_rm("JEQ", AC, 2, PC, "op !: br if false")
            e.emit_rm("LDC", AC, 0, AC, "true case: !ac = 0")
            e.emit_rm("LDA", PC, 1, PC, "unconditional jmp")
            e.emit_rm("LDC", AC, 1, AC, "false case: !ac = 1")
            e.emit_comment("<- Op")
        elif kind in _BINARIOS:
            self._op(node)
        else:
            raise ValueError(f"Nodo inesperado en una expresión: {kind}")

    def _op(self, node: ASTNode) -> None:
        """OpK: ac1 = operando izquierdo, ac = operando derecho, ac = ac1 op ac."""
        e = self._e
        izq, der = node.children[0], node.children[1]
        kind = node.kind
        e.emit_comment("-> Op")
        self._exp(izq)
        e.emit_rm("ST", AC, self._push(), MP, "op: push left")
        self._exp(der)
        e.emit_rm("LD", AC1, self._pop(), MP, "op: load left")

        if kind in _ARITMETICOS:
            instruccion, simbolo = _ARITMETICOS[kind]
            if kind == "OP_DIVIDE" and node.attrs.get("tipo") == "float":
                instruccion = "DIVR"  # extensión: división real (DIV trunca)
            e.emit_ro(instruccion, AC, AC1, AC, f"op {simbolo}")
        elif kind in _COMPARACIONES:
            salto, simbolo = _COMPARACIONES[kind]
            e.emit_ro("SUB", AC, AC1, AC, f"op {simbolo}")
            e.emit_rm(salto, AC, 2, PC, "br if true")
            e.emit_rm("LDC", AC, 0, AC, "false case")
            e.emit_rm("LDA", PC, 1, PC, "unconditional jmp")
            e.emit_rm("LDC", AC, 1, AC, "true case")
        elif kind == "OP_MODULO":
            # izq % der = izq - (izq / der) * der   (trunca hacia cero, como C)
            e.emit_ro("DIV", AC2, AC1, AC, "op %: ac2 = izq / der")
            e.emit_ro("MUL", AC2, AC2, AC, "op %: ac2 = ac2 * der")
            e.emit_ro("SUB", AC, AC1, AC2, "op %: ac = izq - ac2")
        elif kind == "OP_POWER":
            self._potencia(node)
        elif kind == "OP_AND":
            e.emit_rm("JEQ", AC1, 3, PC, "op &&: izq falso")
            e.emit_rm("JEQ", AC, 2, PC, "op &&: der falso")
            e.emit_rm("LDC", AC, 1, AC, "true case")
            e.emit_rm("LDA", PC, 1, PC, "unconditional jmp")
            e.emit_rm("LDC", AC, 0, AC, "false case")
        elif kind == "OP_OR":
            e.emit_rm("JNE", AC1, 3, PC, "op ||: izq verdadero")
            e.emit_rm("JNE", AC, 2, PC, "op ||: der verdadero")
            e.emit_rm("LDC", AC, 0, AC, "false case")
            e.emit_rm("LDA", PC, 1, PC, "unconditional jmp")
            e.emit_rm("LDC", AC, 1, AC, "true case")
        e.emit_comment("<- Op")

    def _potencia(self, node: ASTNode) -> None:
        """ac = ac1 ^ ac con un ciclo de multiplicaciones (la TM no tiene potencia).

        Entero: ac2 = 1; mientras ac > 0: ac2 = ac2 * base, ac = ac - 1; ac = ac2. Con
        exponente negativo da 1 (con una constante negativa el semántico ya da error).
        Real: además se guarda el exponente en ac3, el ciclo usa su valor absoluto y, si era
        negativo, el resultado es 1 / ac2 (2.0 ^ -1 = 0.5)."""
        e = self._e
        exponente = node.children[1]
        real = node.attrs.get("tipo") == "float"
        if exponente.attrs.get("tipo") == "float" and exponente.kind != "CONV":
            self._errores.append(CompilerError(
                GENERACION,
                "la TM solo calcula potencias con exponente entero: el ciclo de "
                "multiplicaciones no puede elevar a un exponente float",
                exponente.line, exponente.col,
            ))
        if real:
            e.emit_rm("LDA", AC3, 0, AC, "op ^: ac3 = exponente")
            e.emit_rm("JGE", AC, 2, PC, "op ^: exponente >= 0")
            e.emit_rm("LDC", AC2, 0, 0, "op ^: ac2 = 0")
            e.emit_ro("SUB", AC, AC2, AC, "op ^: exponente = -exponente")
        e.emit_rm("LDC", AC2, 1, 0, "op ^: ac2 = 1")
        e.emit_rm("JLE", AC, 3, PC, "op ^: sale si el exponente <= 0")
        e.emit_ro("MUL", AC2, AC2, AC1, "op ^: ac2 = ac2 * base")
        e.emit_rm("LDA", AC, -1, AC, "op ^: exponente - 1")
        e.emit_rm("LDA", PC, -4, PC, "op ^: regresa a la prueba")
        if real:
            e.emit_rm("JGE", AC3, 2, PC, "op ^: exponente original >= 0")
            e.emit_rm("LDC", AC, 1, 0, "op ^: ac = 1")
            e.emit_ro("DIVR", AC2, AC, AC2, "op ^: ac2 = 1 / ac2")
        e.emit_rm("LDA", AC, 0, AC2, "op ^: ac = ac2")

    # ─── Memoria ─────────────────────────────────────────────────────────────

    def _st_lookup(self, ident: ASTNode) -> int:
        """Dirección de la variable (desplazamiento respecto de gp)."""
        return self._tabla.lookup(ident.value).direccion

    def _push(self) -> int:
        """Temporal para guardar un operando izquierdo (tmpOffset--)."""
        offset = self._tmp_offset
        self._tmp_offset -= 1
        self._temporales = max(self._temporales, 1 - offset)
        return offset

    def _pop(self) -> int:
        """Temporal del operando izquierdo que se guardó al último (++tmpOffset)."""
        self._tmp_offset += 1
        return self._tmp_offset

    def _limites(self) -> list[CompilerError]:
        errores = []
        if self._e.total > IADDR_SIZE:
            errores.append(CompilerError(
                GENERACION,
                f"el programa necesita {self._e.total} instrucciones TM y el simulador solo "
                f"tiene {IADDR_SIZE} direcciones de instrucciones",
            ))
        # Las variables ocupan 0, 1, 2… y los temporales bajan desde DADDR_SIZE - 1
        variables, temporales = len(self._tabla), self._temporales
        if variables + temporales > DADDR_SIZE:
            errores.append(CompilerError(
                GENERACION,
                f"el programa necesita {variables} variables y {temporales} temporales y la "
                f"memoria de datos de la TM solo tiene {DADDR_SIZE} posiciones",
            ))
        return errores


def _constante(node: ASTNode) -> int | str:
    """Valor de un literal para LDC: true = 1, false = 0, -5 = constante negativa. Un real
    se escribe como en el código fuente (7.59), que es lo que lee el tm.c extendido."""
    if node.kind == "KW_TRUE":
        return 1
    if node.kind == "KW_FALSE":
        return 0
    negativo = node.kind == "OP_NEG"
    literal = node.children[0] if negativo else node
    if literal.kind == "REAL":
        return ("-" if negativo else "") + literal.value
    valor = literal.attrs.get("valor")
    if valor is None:
        valor = valor_literal(literal.kind, literal.value, permitir_minimo=negativo)
    return -valor if negativo else valor

