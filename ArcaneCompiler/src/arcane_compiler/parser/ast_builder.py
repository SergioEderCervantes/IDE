"""Conversión del árbol concreto (CST) que produce el parser al AST.

El parser genera un nodo por cada regla de la gramática (expresion, conjuncion,
comparacion, termino, factor, sent_expresion, ...). El AST conserva solo la
estructura con significado:

  - Las cadenas [operando, op, operando, ...] se vuelven nodos binarios cuyo
    tipo es el operador:  2 + 3 * 4  →  OP_PLUS(2, OP_MULTIPLY(3, 4)).
  - Los envoltorios sin significado (sent_expresion, ( expr )) desaparecen.
  - Las formas son estables: declaracion_variable siempre es [tipo, id_list]
    y sent_out siempre contiene un nodo salida.
  - Los nodos de error se conservan para que el árbol muestre dónde fallan.

El CST no se modifica: build_ast devuelve nodos nuevos.
"""
from __future__ import annotations
from .ast_nodes import ASTNode

# Nodos del CST con hijos [operando, op, operando, op, ...]
_BINARY_CONTAINERS = {
    "expresion", "conjuncion", "comparacion", "expresion_simple", "termino", "factor",
}

# Contenedores cuyo operador asocia a la derecha: 2 ^ 3 ^ 2 == 2 ^ (3 ^ 2)
_RIGHT_ASSOC_CONTAINERS = {"factor"}

# Tipos de token que actúan como operador dentro de un contenedor binario
_OPERATOR_KINDS = {
    "OP_PLUS", "OP_MINUS", "OP_MULTIPLY", "OP_DIVIDE", "OP_MODULO", "OP_POWER",
    "OP_LT", "OP_LE", "OP_GT", "OP_GE", "OP_EQ", "OP_NE",
    "OP_AND", "OP_OR", "OP_NOT",
}

# Envoltorios cuyos hijos se integran directamente en el nodo padre
_SPLICE_KINDS = {"sent_expresion"}


def build_ast(cst: ASTNode) -> ASTNode:
    """Construye el AST a partir del CST producido por Parser.parse()."""
    return _build(cst)


def _build(node: ASTNode) -> ASTNode:
    if node.kind in _BINARY_CONTAINERS:
        return _build_binary(node)
    if node.kind == "componente_grupo":
        return _build_grupo(node)
    if node.kind == "componente_not":
        return _build_not(node)
    return _copy(node, _build_children(node))


def _build_children(node: ASTNode) -> list[ASTNode]:
    children: list[ASTNode] = []
    for child in node.children:
        if child.kind in _SPLICE_KINDS:
            # x = expr ;  →  asignacion[x, expr]  (y su error de ';' si lo hubo)
            children.extend(_build(c) for c in child.children)
        else:
            children.append(_build(child))
    return children


def _build_binary(node: ASTNode) -> ASTNode:
    """[a, op1, b, op2, c] → op2(op1(a, b), c)  (o op1(a, op2(b, c)) si asocia a la derecha)."""
    ops = [c for c in node.children if c.kind in _OPERATOR_KINDS]
    operands = [_build(c) for c in node.children if c.kind not in _OPERATOR_KINDS]

    if not ops:
        # Un solo operando: el contenedor no aporta nada
        if len(operands) == 1:
            return operands[0]
        return _copy(node, operands)

    if node.kind in _RIGHT_ASSOC_CONTAINERS and len(operands) == len(ops) + 1:
        result = operands[-1]
        for i in reversed(range(len(ops))):
            result = _copy(ops[i], [operands[i], result])
        return result

    result = operands[0]
    for i, op in enumerate(ops):
        right = [operands[i + 1]] if i + 1 < len(operands) else []
        result = _copy(op, [result] + right)
    return result


def _build_grupo(node: ASTNode) -> ASTNode:
    """( expr ) → expr. Si falta ')' se conserva el grupo para mostrar el error."""
    children = [_build(c) for c in node.children]
    if len(children) == 1 and children[0].kind != "error":
        return children[0]
    return _copy(node, children)


def _build_not(node: ASTNode) -> ASTNode:
    """componente_not[OP_NOT, x] → OP_NOT(x), conservando el lexema ('!' o 'not')."""
    op = next((c for c in node.children if c.kind == "OP_NOT"), None)
    operands = [_build(c) for c in node.children if c.kind != "OP_NOT"]
    if op is None:
        return _copy(node, operands)
    return _copy(op, operands)


def _copy(node: ASTNode, children: list[ASTNode]) -> ASTNode:
    return ASTNode(
        kind=node.kind,
        value=node.value,
        line=node.line,
        col=node.col,
        children=children,
    )
