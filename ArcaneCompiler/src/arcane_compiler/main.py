import sys
from pathlib import Path

from arcane_compiler.utils.output import emit_section, format_token_table, format_error_list

VALID_PHASES = {"lexical", "syntactic", "semantic", "intermediate", "execution", "all"}


def main() -> None:
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
        tokens, errors = lexer.tokenize()

        emit_section("LEXICO", format_token_table(tokens))
        emit_section("SINTACTICO", "")
        emit_section("SEMANTICO", "")
        emit_section("CODIGO_INTERMEDIO", "")
        emit_section("TABLA_SIMBOLOS", "")
        emit_section("ERRORES", format_error_list(errors))
        emit_section("EJECUCION", "")
    else:
        # TODO: implement other phases
        emit_section("LEXICO", "")
        emit_section("SINTACTICO", "")
        emit_section("SEMANTICO", "")
        emit_section("CODIGO_INTERMEDIO", "")
        emit_section("TABLA_SIMBOLOS", "")
        emit_section("ERRORES", "")
        emit_section("EJECUCION", "")


if __name__ == "__main__":
    main()
