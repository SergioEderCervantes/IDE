"""Punto de entrada de la CLI: arcane-compiler <archivo> <fase>.

Las fases forman un pipeline: cada una ejecuta las anteriores y se detiene si
una fase previa encontró errores.

    léxico ──(sin errores)──► sintáctico ──(sin errores)──► semántico ...

El código de salida es 0 siempre que el compilador termine, aunque el programa
tenga errores (esos errores son el resultado del análisis). Solo es 1 cuando la
invocación es inválida (argumentos, fase o archivo); el motivo va a stderr.

Con las fases intermediate, execution y all se escriben junto al archivo fuente, como
el tiny.exe de la materia, programa.ci (tres direcciones) y programa.tm (código para el
simulador TM). Si no se pudieron generar, se borran los de una compilación anterior para
que nunca quede código viejo que parezca del programa actual. La ejecución la hace el
simulador TM (tm.exe) con el .tm; el IDE lo lanza.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from arcane_compiler.errors import CompilerError, GENERACION, LEXICO, SINTACTICO, SEMANTICO
from arcane_compiler.intermediate.generator import IntermediateGenerator, IntermediateResult
from arcane_compiler.lexer.lexer import Lexer
from arcane_compiler.lexer.token import Token
from arcane_compiler.parser.ast_builder import build_ast
from arcane_compiler.parser.ast_nodes import ASTNode
from arcane_compiler.parser.ast_serializer import ast_to_json
from arcane_compiler.parser.parser import Parser
from arcane_compiler.semantic.analyzer import SemanticAnalyzer, SemanticResult
from arcane_compiler.tm.cgen import TMGenerator, TMResult
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

# Nombres de las fases 4 y 5 para los avisos
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
    intermedio: Optional[IntermediateResult] = None   # .ci
    tm: Optional[TMResult] = None                     # .tm (None si no se pudo generar)
    errores: dict[str, Optional[list[CompilerError]]] = field(
        default_factory=lambda: {LEXICO: None, SINTACTICO: None, SEMANTICO: None, GENERACION: None}
    )
    avisos: list[str] = field(default_factory=list)


def _requested_phases(phase: str) -> list[str]:
    """'syntactic' → ['lexical', 'syntactic']; 'all' → todas."""
    if phase == "all":
        return list(PHASES)
    return PHASES[: PHASES.index(phase) + 1]


def compile_source(source: str, phase: str, archivo_tm: str = "programa.tm") -> CompilationResult:
    """Ejecuta el pipeline hasta `phase` y devuelve lo que produjo cada fase.

    `archivo_tm` solo se escribe en el comentario del encabezado del código TM."""
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

    if "intermediate" not in requested:
        return result
    if result.errores[SEMANTICO]:
        if phase in _PHASE_TITLES:  # con 'all' no se avisa
            result.avisos.append(
                f"La fase de {_PHASE_TITLES[phase]} no se ejecutó: "
                "corrige primero los errores semánticos."
            )
        return result

    # ── Fase 4: dos caminos paralelos desde el mismo AST anotado, como en el TINY de la
    # materia: el código de tres direcciones (.ci) y el código para la máquina TM (.tm)
    try:
        ast_anotado, tabla = result.semantico.ast, result.semantico.tabla
        result.intermedio = IntermediateGenerator().generate(ast_anotado)
        tm = TMGenerator().generate(ast_anotado, tabla, archivo_tm)
    except RecursionError:
        result.avisos.append(
            "La fase de generación de código intermedio no se ejecutó: " + _ANIDAMIENTO_EXCESIVO + "."
        )
        return result
    result.errores[GENERACION] = tm.errores
    result.avisos.extend(tm.avisos)
    if not tm.errores:
        result.tm = tm
    elif phase == "execution":
        result.avisos.append(
            "El programa no se puede ejecutar: no se generó el código TM (revisa los errores de generación)."
        )

    # ── Fase 5: la ejecución la hace el simulador TM con el archivo .tm (lo lanza el IDE)
    return result


def ruta_salida(fuente: Path, extension: str) -> Path:
    """programa.txt → programa.tm. Si el fuente ya tiene esa extensión (.tm o .ci) se agrega
    otra, para no escribir encima del programa."""
    if fuente.suffix.lower() in (".tm", ".ci"):
        return fuente.with_name(fuente.name + extension)
    return fuente.with_suffix(extension)


def escribir_salidas(fuente: Path, result: CompilationResult) -> Optional[Path]:
    """Escribe el .ci y el .tm junto al archivo fuente y devuelve la ruta del .tm.

    El que no se generó se borra: si quedara el de una compilación anterior, el simulador
    ejecutaría código de otro programa. Devuelve None si no hay .tm."""
    salidas = (
        (ruta_salida(fuente, ".ci"), result.intermedio.texto() + "\n" if result.intermedio else ""),
        (ruta_salida(fuente, ".tm"), result.tm.texto() if result.tm else ""),
    )
    for ruta, contenido in salidas:
        if contenido:
            ruta.write_text(contenido, encoding="utf-8")
        else:
            ruta.unlink(missing_ok=True)
    return salidas[1][0] if result.tm else None


def emit_result(result: CompilationResult, ejecucion: str = "") -> None:
    """Escribe el resultado en stdout con el protocolo de secciones que lee el IDE.

    `ejecucion` es la ruta del .tm que el IDE debe cargar en el simulador TM."""
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
    emit_section("CODIGO_INTERMEDIO", result.intermedio.texto() if result.intermedio else "")
    emit_section("CODIGO_TM", result.tm.texto() if result.tm else "")
    emit_section("TABLA_SIMBOLOS", tabla)
    emit_section("ERRORES", format_errors(result.errores, result.avisos))
    emit_section("EJECUCION", ejecucion)


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
    resultado = compile_source(source, phase, ruta_salida(path, ".tm").name)
    ejecucion = ""
    if phase in ("intermediate", "execution", "all"):
        try:
            ruta_tm = escribir_salidas(path, resultado)
        except OSError as e:
            ruta_tm = None
            resultado.avisos.append(f"No se pudieron escribir los archivos .ci y .tm: {e}")
        if ruta_tm is not None and phase in ("execution", "all"):
            ejecucion = str(ruta_tm.resolve())
    try:
        emit_result(resultado, ejecucion)
    except RecursionError:  # el AST cupo en el análisis pero no al convertirlo a JSON
        print(f"Error: {_ANIDAMIENTO_EXCESIVO}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
