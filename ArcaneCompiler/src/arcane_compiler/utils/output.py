def emit_section(name: str, content: str) -> None:
    print(f"==={name}===")
    print(content)
    print(f"===END_{name}===")


def format_token_table(tokens: list) -> str:
    header = f"{'LÍNEA':<7}{'COL':<6}{'TIPO':<26}{'VALOR'}"
    separator = f"{'-----':<7}{'---':<6}{'----':<26}{'-----'}"
    rows = [header, separator]
    for tok in tokens:
        rows.append(
            f"{tok.line:<7}{tok.column:<6}{tok.type.name:<26}{tok.value!r}"
        )
    return "\n".join(rows)


def format_error_list(errors: list) -> str:
    lines = []
    for tok in errors:
        lines.append(
            f"Error léxico en línea {tok.line}, columna {tok.column}: {tok.value}"
        )
    return "\n".join(lines)
