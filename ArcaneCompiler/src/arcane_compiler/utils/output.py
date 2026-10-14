import json
from typing import Optional
from ..lexer.token_type import TokenType
from ..lexer.token import Token
from ..errors import CompilerError, LEXICO, SINTACTICO, SEMANTICO
from ..semantic.analyzer import SemanticResult


def emit_section(name: str, content: str) -> None:
    print(f"==={name}===")
    print(content)
    print(f"===END_{name}===")


def format_token_table(tokens: list[Token]) -> str:
    header = f"{'LÍNEA':<7}{'COL':<6}{'TIPO':<26}{'VALOR'}"
    separator = f"{'-----':<7}{'---':<6}{'----':<26}{'-----'}"
    rows = [header, separator]
    for tok in tokens:
        if tok.type == TokenType.COMMENT_BLOCK or tok.type == TokenType.COMMENT_LINE:
            continue
        rows.append(
            f"{tok.line:<7}{tok.column:<6}{tok.type.name:<26}{tok.value!r}"
        )
    return "\n".join(rows)


def format_semantic(resultado: SemanticResult) -> str:
    """Sección SEMANTICO: el AST anotado (cada nodo con sus attrs) y la traza del recorrido."""
    return json.dumps({
        "success": not resultado.errores,
        "ast": resultado.ast.to_dict(),
        "recorrido": resultado.recorrido,
        "error_count": len(resultado.errores),
    }, indent=2, ensure_ascii=False)


def format_symbol_table(resultado: SemanticResult) -> str:
    """Sección TABLA_SIMBOLOS: lista de {nombre, tipo, direccion, declaracion, referencias}."""
    return json.dumps(resultado.tabla.to_list(), indent=2, ensure_ascii=False)


def format_errors(errores: dict[str, Optional[list[CompilerError]]], avisos: list[str]) -> str:
    """
    Serializa los errores por fase al JSON que muestra el IDE.

    Cada fase es una lista de {linea, columna, mensaje}, o null si la fase no se
    ejecutó (para distinguir "sin errores" de "no se analizó").
    """
    def por_fase(fase: str) -> Optional[list[dict]]:
        lista = errores.get(fase)
        return None if lista is None else [e.to_dict() for e in lista]

    return json.dumps({
        "lexico": por_fase(LEXICO),
        "sintactico": por_fase(SINTACTICO),
        "semantico": por_fase(SEMANTICO),
        "avisos": avisos,
    }, indent=2, ensure_ascii=False)
