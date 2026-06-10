import json
from .ast_nodes import ASTNode

# Nodos que en el CST contienen [operando, op, operando, op, ...] y se convierten en árbol binario
_BINARY_CONTAINERS = {
    "expresion", "comparacion", "expresion_simple", "termino", "factor",
}

# Tipos de token que son operadores (para detectarlos en el CST original)
_OPERATOR_KINDS = {
    "OP_PLUS", "OP_MINUS", "OP_MULTIPLY", "OP_DIVIDE", "OP_MODULO",
    "OP_POWER", "OP_INCREMENT", "OP_DECREMENT",
    "OP_LT", "OP_LE", "OP_GT", "OP_GE", "OP_EQ", "OP_NE",
    "OP_AND", "OP_OR", "OP_NOT", "OP_ASSIGN",
    "OP_SHIFT_LEFT", "OP_SHIFT_RIGHT",
}


def _transform(node: dict) -> dict:
    """Transforma recursivamente un nodo CST en representación AST."""
    kind = node.get("kind")
    raw_children = node.get("children", [])

    # ── Contenedores binarios: [operando, op, operando, op, operando ...]
    # IMPORTANTE: separar operadores ANTES de transformar para no confundir
    # nodos transformados (que pueden tener kind=OP_*) con operadores reales.
    if kind in _BINARY_CONTAINERS:
        raw_ops = [c for c in raw_children if c.get("kind") in _OPERATOR_KINDS]
        raw_operands = [c for c in raw_children if c.get("kind") not in _OPERATOR_KINDS]

        if raw_ops:
            # Transformar cada operando recursivamente
            t_operands = [_transform(c) for c in raw_operands]
            # Construir árbol binario izquierda-asociativo
            result = t_operands[0]
            for i, op in enumerate(raw_ops):
                right = t_operands[i + 1] if i + 1 < len(t_operands) else None
                result = {
                    "kind": op["kind"],
                    "value": op["value"],
                    "line": op.get("line"),
                    "col": op.get("col"),
                    "children": [result] + ([right] if right else []),
                }
            return result

        # Sin operadores: un solo hijo → colapsar, o transformar normalmente
        if len(raw_operands) == 1:
            return _transform(raw_operands[0])
        # Sin hijos o caso raro → seguir adelante al nodo normal

    # ── sent_expresion: wrapper innecesario → devolver hijo expresión
    if kind == "sent_expresion":
        useful = [c for c in raw_children if c.get("kind") != "error"]
        if useful:
            return _transform(useful[0])
        if raw_children:
            return _transform(raw_children[0])

    # ── componente_grupo: ( expr ) → el resultado es la expresión directa
    if kind == "componente_grupo":
        useful = [c for c in raw_children if c.get("kind") != "error"]
        if useful:
            return _transform(useful[0])
        if raw_children:
            return _transform(raw_children[0])

    # ── componente_not: !x → nodo OP_NOT con el operando como hijo
    if kind == "componente_not":
        operand = next((c for c in raw_children if c.get("kind") not in _OPERATOR_KINDS), None)
        if operand:
            return {
                "kind": "OP_NOT",
                "value": "!",
                "line": node.get("line"),
                "col": node.get("col"),
                "children": [_transform(operand)],
            }

    # ── salida con un solo hijo útil → colapsar
    if kind == "salida" and len(raw_children) == 1:
        return _transform(raw_children[0])

    # ── id_list con un solo id → devolver el id directamente
    if kind == "id_list" and len(raw_children) == 1:
        return _transform(raw_children[0])

    # ── Nodo normal: transformar hijos recursivamente
    return {
        "kind": kind,
        "value": node.get("value"),
        "line": node.get("line"),
        "col": node.get("col"),
        "children": [_transform(c) for c in raw_children],
    }


def _to_dict(node: ASTNode) -> dict:
    return {
        "kind": node.kind,
        "value": node.value,
        "line": node.line,
        "col": node.col,
        "children": [_to_dict(c) for c in node.children],
    }


def ast_to_json(ast: ASTNode, success: bool, errors: list[str]) -> str:
    """
    Serializa el resultado del parser al formato JSON esperado por el IDE.
    Aplica transformación CST → AST antes de serializar.
    """
    ast_dict = _transform(_to_dict(ast)) if ast is not None else None
    return json.dumps({
        "success": success,
        "ast": ast_dict,
        "error_count": len(errors),
    }, indent=2, ensure_ascii=False)
