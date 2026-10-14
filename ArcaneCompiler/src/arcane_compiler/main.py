"""Punto de entrada de la CLI: arcane-compiler <archivo> <fase>.

Las fases forman un pipeline: cada una ejecuta las anteriores y se detiene si
una fase previa encontró errores.

    léxico ──(sin errores)──► sintáctico ──(sin errores)──► semántico ...

El código de salida es 0 siempre que el compilador termine, aunque el programa
tenga errores (esos errores son el resultado del análisis). Solo es 1 cuando la
invocación es inválida (argumentos, fase o archivo); el motivo va a stderr.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from arcane_compiler.errors import CompilerError, LEXICO, SINTACTICO, SEMANTICO
from arcane_compiler.lexer.lexer import Lexer
from arcane_compiler.lexer.token import Token
from arcane_compiler.parser.ast_builder import build_ast
from arcane_compiler.parser.ast_nodes import ASTNode
from arcane_compiler.parser.ast_serializer import ast_to_json
from arcane_compiler.parser.parser import Parser
from arcane_compiler.semantic.analyzer import SemanticAnalyzer, SemanticResult
from arcane_compiler.utils.output import (
    emit_section, format_errors, format_semantic, format_symbol_table, format_token_table,
)

# Fases en orden de ejecución
PHASES = ["lexical", "syntactic", "semantic", "intermediate", "execution"]
VALID_PHASES = set(PHASES) | {"all"}

# El análisis es recursivo (una llamada por nivel de anidamiento). Con este límite caben
# ~500 paréntesis anidados o expresiones de ~1000 términos; más allá se reporta este error
# en lugar de terminar con un traceback.
_LIMITE_RECURSION = 10_000
_ANIDAMIENTO_EXCESIVO = (
    "el programa tiene expresiones anidadas demasiado profundas para analizarse; "
    "divide la expresión en partes más pequeñas"
)

# Fases aún no implementadas
_PHASE_TITLES = {
    "intermediate": "generación de código intermedio",
    "execution": "ejecución",
}


@dataclass
class CompilationResult:
    """Lo que produjo cada fase. None = la fase no se ejecutó."""
    tokens: Optional[list[Token]] = None
    ast: Optional[ASTNode] = None
    semantico: Optional[SemanticResult] = None
    errores: dict[str, Optional[list[CompilerError]]] = field(
        default_factory=lambda: {LEXICO: None, SINTACTICO: None, SEMANTICO: None}
    )
    avisos: list[str] = field(default_factory=list)


def _requested_phases(phase: str) -> list[str]:
    """'syntactic' → ['lexical', 'syntactic']; 'all' → todas."""
    if phase == "all":
        return list(PHASES)
    return PHASES[: PHASES.index(phase) + 1]


def compile_source(source: str, phase: str) -> CompilationResult:
    """Ejecuta el pipeline hasta `phase` y devuelve lo que produjo cada fase."""
    requested = _requested_phases(phase)
    result = CompilationResult()

    # ── Fase 1: análisis léxico
    tokens, lex_errors = Lexer(source).tokenize()
    result.tokens = tokens
    result.errores[LEXICO] = [
        CompilerError(LEXICO, tok.value, tok.line, tok.column) for tok in lex_errors
    ]

    if "syntactic" not in requested:
        return result
    if result.errores[LEXICO]:
        result.avisos.append(
            "El análisis sintáctico no se ejecutó: corrige primero los errores léxicos."
        )
        return result

    # ── Fase 2: análisis sintáctico
    try:
        parser = Parser(tokens)
        result.ast = build_ast(parser.parse())
        result.errores[SINTACTICO] = parser.diagnostics
    except RecursionError:
        result.ast = None
        result.errores[SINTACTICO] = [CompilerError(SINTACTICO, _ANIDAMIENTO_EXCESIVO)]

    if "semantic" not in requested:
        return result
    if result.errores[SINTACTICO]:
        result.avisos.append(
            "El análisis semántico no se ejecutó: corrige primero los errores sintácticos."
        )
        return result

    # ── Fase 3: análisis semántico (sobre una copia del AST; result.ast queda sin anotar)
    try:
        result.semantico = SemanticAnalyzer().analyze(result.ast)
        result.errores[SEMANTICO] = result.semantico.errores
    except RecursionError:
        result.semantico = None
        result.errores[SEMANTICO] = [CompilerError(SEMANTICO, _ANIDAMIENTO_EXCESIVO)]

    # ── Fases 4 y 5: pendientes de implementar
    if phase in _PHASE_TITLES:
        if result.errores[SEMANTICO]:
            result.avisos.append(
                f"La fase de {_PHASE_TITLES[phase]} no se ejecutó: "
                "corrige primero los errores semánticos."
            )
        else:
            result.avisos.append(f"La fase de {_PHASE_TITLES[phase]} aún no está implementada.")
    return result


def emit_result(result: CompilationResult) -> None:
    """Escribe el resultado en stdout con el protocolo de secciones que lee el IDE."""
    tokens = format_token_table(result.tokens) if result.tokens is not None else ""

    sintactico = ""
    if result.errores[SINTACTICO] is not None:
        errores = result.errores[SINTACTICO]
        sintactico = ast_to_json(result.ast, not errores, [str(e) for e in errores])

    semantico = format_semantic(result.semantico) if result.semantico else ""
    tabla = format_symbol_table(result.semantico) if result.semantico else ""

    emit_section("LEXICO", tokens)
    emit_section("SINTACTICO", sintactico)
    emit_section("SEMANTICO", semantico)
    emit_section("CODIGO_INTERMEDIO", "")
    emit_section("TABLA_SIMBOLOS", tabla)
    emit_section("ERRORES", format_errors(result.errores, result.avisos))
    emit_section("EJECUCION", "")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 3:
        print("Uso: arcane-compiler <archivo> <fase>", file=sys.stderr)
        sys.exit(1)

    source_file = sys.argv[1]
    phase = sys.argv[2]

    if phase not in VALID_PHASES:
        print(f"Fase inválida: {phase}. Fases válidas: {', '.join(sorted(VALID_PHASES))}", file=sys.stderr)
        sys.exit(1)

    path = Path(source_file)
    if not path.is_file():
        print(f"El archivo no existe: {source_file}", file=sys.stderr)
        sys.exit(1)

    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"El archivo no está en UTF-8: {source_file}", file=sys.stderr)
        sys.exit(1)

    sys.setrecursionlimit(max(sys.getrecursionlimit(), _LIMITE_RECURSION))
    resultado = compile_source(source, phase)
    try:
        emit_result(resultado)
    except RecursionError:  # el AST cupo en el análisis pero no al convertirlo a JSON
        print(f"Error: {_ANIDAMIENTO_EXCESIVO}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
