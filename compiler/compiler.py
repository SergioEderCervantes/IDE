#!/usr/bin/env python3
import sys


def _configure_io_encoding() -> None:
    """Ensure process output can emit Unicode consistently across platforms."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def main():
    _configure_io_encoding()

    if len(sys.argv) < 2:
        print("Uso: compiler.py <archivo_fuente> [fase]", file=sys.stderr)
        sys.exit(1)
    
    source_file = sys.argv[1]
    phase = sys.argv[2].lower() if len(sys.argv) > 2 else "all"

    phase_titles = {
        "lexical": "Análisis Léxico",
        "syntactic": "Análisis Sintáctico",
        "semantic": "Análisis Semántico",
        "intermediate": "Generación de Código Intermedio",
        "execution": "Ejecución",
        "all": "Compilación Completa",
    }

    selected_title = phase_titles.get(phase, "Compilación Completa")
    
    # Simular salida estructurada
    if phase in ("all", "lexical"):
        print(f"Fase solicitada: {selected_title}")
    print("===TOKENS===")
    print("INT: 'int' (línea 1, col 0)")
    print("IDENTIFIER: 'x' (línea 1, col 4)")
    print("ASSIGN: '=' (línea 1, col 6)")
    print("NUMBER: '5' (línea 1, col 8)")
    print("===END_TOKENS===")
    
    if phase in ("all", "syntactic"):
        print(f"Fase solicitada: {selected_title}")
    print("===AST===")
    print("Program")
    print("  └─ VarDeclaration")
    print("      ├─ Type: int")
    print("      ├─ Name: x")
    print("      └─ Value: 5")
    print("===END_AST===")
    
    if phase in ("all", "semantic"):
        print(f"Fase solicitada: {selected_title}")
    print("===SEMANTIC===")
    print("✓ Sin errores semánticos")
    print("===END_SEMANTIC===")
    
    if phase in ("all", "intermediate"):
        print(f"Fase solicitada: {selected_title}")
    print("===INTERMEDIATE===")
    print("t1 = 5")
    print("x = t1")
    print("===END_INTERMEDIATE===")
    
    print("===SYMBOLS===")
    print("x | int | global | línea 1")
    print("===END_SYMBOLS===")
    
    print("===ERRORS===")
    print("# Sin errores")
    print("===END_ERRORS===")
    
    if phase in ("all", "execution"):
        print(f"Fase solicitada: {selected_title}")
    print("===EXECUTION===")
    print("Hello World from Compiler!")
    print("===END_EXECUTION===")

if __name__ == "__main__":
    main()
