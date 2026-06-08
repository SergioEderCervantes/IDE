import sys
import json
from pathlib import Path

from arcane_compiler.utils.output import emit_section, format_token_table, format_error_list

VALID_PHASES = {"lexical", "syntactic", "semantic", "intermediate", "execution", "all"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 3:
        print("Uso: arcane-compiler <archivo> <fase>", file=sys.stderr)
        sys.exit(1)

    source_file = sys.argv[1]
    phase = sys.argv[2]

    if not Path(source_file).exists():
        emit_section("ERRORES", f"El archivo no existe: {source_file}")
        sys.exit(1)

    if phase not in VALID_PHASES:
        print(f"Fase inválida: {phase}. Fases válidas: {', '.join(sorted(VALID_PHASES))}", file=sys.stderr)
        sys.exit(1)

    if phase in ("lexical", "all"):
        from arcane_compiler.lexer.lexer import Lexer

        source = Path(source_file).read_text(encoding="utf-8")
        lexer = Lexer(source)
        tokens, lex_errors = lexer.tokenize()

        emit_section("LEXICO", format_token_table(tokens))
        emit_section("SINTACTICO", "")
        emit_section("SEMANTICO", "")
        emit_section("CODIGO_INTERMEDIO", "")
        emit_section("TABLA_SIMBOLOS", "")
        emit_section("ERRORES", format_error_list(lex_errors))
        emit_section("EJECUCION", "")

    elif phase == "syntactic":
        from arcane_compiler.lexer.lexer import Lexer
        from arcane_compiler.parser.parser import Parser
        from arcane_compiler.parser.ast_serializer import ast_to_json

        source = Path(source_file).read_text(encoding="utf-8")
        lexer = Lexer(source)
        tokens, lex_errors = lexer.tokenize()

        if lex_errors:
            emit_section("LEXICO", format_token_table(tokens))
            emit_section("SINTACTICO", json.dumps({"success": False, "ast": None, "error_count": 0}))
            emit_section("SEMANTICO", "")
            emit_section("CODIGO_INTERMEDIO", "")
            emit_section("TABLA_SIMBOLOS", "")
            emit_section(
                "ERRORES",
                "BLOQUEADO: Elimina todos los errores léxicos antes del análisis sintáctico.\n"
                + format_error_list(lex_errors),
            )
            emit_section("EJECUCION", "")
            sys.exit(1)

        parser = Parser(tokens)
        ast = parser.parse()
        parse_errors = parser.errors
        success = len(parse_errors) == 0

        emit_section("LEXICO", format_token_table(tokens))
        emit_section("SINTACTICO", ast_to_json(ast, success, parse_errors))
        emit_section("SEMANTICO", "")
        emit_section("CODIGO_INTERMEDIO", "")
        emit_section("TABLA_SIMBOLOS", "")
        emit_section("ERRORES", "\n".join(parse_errors) if parse_errors else "")
        emit_section("EJECUCION", "")

    else:
        emit_section("LEXICO", "")
        emit_section("SINTACTICO", "")
        emit_section("SEMANTICO", "")
        emit_section("CODIGO_INTERMEDIO", "")
        emit_section("TABLA_SIMBOLOS", "")
        emit_section("ERRORES", "")
        emit_section("EJECUCION", "")


if __name__ == "__main__":
    main()
