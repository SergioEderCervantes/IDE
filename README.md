# ArcaneIDE + ArcaneCompiler

A monorepo containing a PyQt6-based IDE and a from-scratch compiler for a C-like language. Both packages share a single virtual environment.

---

## Monorepo layout

```
IDE/
├── .venv/                 ← Shared virtual environment
├── ArcaneIDE/             ← IDE application (PyQt6)
│   ├── pyproject.toml
│   └── src/
│       ├── main.py
│       ├── assets/
│       ├── core/          ← Business logic (no UI)
│       ├── ui/            ← Qt widgets
│       └── utils/
└── ArcaneCompiler/        ← Compiler package
    ├── pyproject.toml
    ├── src/
    │   └── arcane_compiler/
    │       ├── main.py        ← CLI entry point
    │       ├── lexer/         ← Lexical analysis (DFA)
    │       └── utils/         ← Output protocol helpers
    └── tests/
        ├── samples/       ← .c source files for testing
        └── test_lexer.py
```

---

## Setup

> Run all commands from the repo root (`IDE/`).

```bash
# 1. Create the shared virtual environment (only once)
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# 3. Install the IDE
pip install -e "ArcaneIDE/"

# 4. Install the compiler (+ dev dependencies for tests)
pip install -e "ArcaneCompiler/[dev]"
```

---

## Running the IDE

```bash
# From the repo root, with the venv active:
cd ArcaneIDE
python -m src.main
```

The IDE window appears. Open any `.c` file with the file explorer on the left, then use the toolbar or function keys to trigger compilation phases. Results appear in the tabbed panel at the bottom right.

| Key | Action |
|-----|--------|
| F5  | Lexical analysis |
| F6  | Syntactic analysis |
| F7  | Semantic analysis |
| F8  | Intermediate code generation |
| F9  | Execution |

---

## Using the compiler standalone (without the IDE)

The compiler is installed as the `arcane-compiler` command inside the shared `.venv`.

### Syntax

```
arcane-compiler <source_file> <phase>
```

Valid phases: `lexical`, `syntactic`, `semantic`, `intermediate`, `execution`, `all`.

### Examples

```bash
# Activate the venv first
source .venv/bin/activate

# Run lexical analysis on a source file
arcane-compiler ArcaneCompiler/tests/samples/valid_full.c lexical

# Run all phases at once
arcane-compiler my_program.c all

# Pipe the token table to a file
arcane-compiler my_program.c lexical > output.txt
```

### Output format

Every phase writes to stdout using this protocol — one section per compiler stage:

```
===LEXICO===
LÍNEA  COL   TIPO                      VALOR
-----  ---   ----                      -----
1      1     KW_INT                    'int'
...
===END_LEXICO===
===ERRORES===
Error léxico en línea 3, columna 7: Carácter inválido: '@'
===END_ERRORES===
```

The IDE reads this same stdout and distributes each section to its corresponding output tab.

### Phases currently implemented

| Phase flag | Status | Output section(s) |
|------------|--------|-------------------|
| `lexical`  | Implemented | `LEXICO`, `ERRORES` |
| `syntactic` | Pending | `SINTACTICO` |
| `semantic`  | Pending | `SEMANTICO` |
| `intermediate` | Pending | `CODIGO_INTERMEDIO`, `TABLA_SIMBOLOS` |
| `execution` | Pending | `EJECUCION` |
| `all` | Partial | All sections (lexical complete) |

---

## Running tests

```bash
# From the repo root, with the venv active:
.venv/bin/pytest ArcaneCompiler/tests/ -v
```

---

## Features

- **Code editor** — QScintilla with line numbers, syntax highlighting, auto-indent.
- **File explorer** — tree view, double-click to open.
- **5 compilation phases** — triggered from toolbar or F5–F9.
- **7 output tabs** — Tokens, Sintáctico, Semántico, Código Intermedio, Tabla de Símbolos, Errores, Ejecución.
- **Themes** — 5 built-in themes including Tokyo Night.
- **File management** — New, Open, Save, Save As, unsaved-changes prompt.
- **Standalone compiler CLI** — `arcane-compiler` works independently of the IDE.

---

## Language supported

The compiler targets a C-like teaching language with:

- Types: `int`, `float`
- Control flow: `if`/`else`, `while`, `do`/`while`, `switch`/`case`/`end`
- I/O: `cin >>`, `cout <<`
- Operators: arithmetic (`+ - * / % ^`), relational (`< <= > >= == !=`), logical (`&& || !` / `and or not`), increment/decrement (`++ --`)
- Literals: integers, reals, strings, characters
- Comments: line (`//`) and block (`/* */`)
