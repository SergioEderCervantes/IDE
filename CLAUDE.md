# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the IDE

```bash
# From ArcaneIDE/
source .venv/bin/activate
python -m src.main
```

## Running the compiler standalone

```bash
source .venv/bin/activate
arcane-compiler <source_file> <phase>
# e.g.:
arcane-compiler ArcaneCompiler/tests/samples/valid_full.c lexical
```

## Running tests

```bash
.venv/bin/pytest ArcaneCompiler/tests/ -v
```

## Setup (first time)

```bash
# From repo root (IDE/)
python3 -m venv .venv
source .venv/bin/activate
pip install -e "ArcaneIDE/"
pip install -e "ArcaneCompiler/[dev]"
```

Both packages share the single `.venv` at the repo root. Never create a new venv inside a subpackage.

## Repository layout

```
IDE/
├── .venv/                    ← Shared virtual environment
├── ArcaneIDE/
│   ├── pyproject.toml
│   └── src/
│       ├── main.py
│       ├── assets/           ← logoIDE.jpg
│       ├── core/             ← Business logic (no UI)
│       ├── ui/               ← Qt widgets
│       └── utils/            ← Shared constants
└── ArcaneCompiler/
    ├── pyproject.toml
    ├── src/
    │   └── arcane_compiler/
    │       ├── main.py           ← CLI entry point
    │       ├── lexer/
    │       │   ├── token_type.py ← TokenType enum
    │       │   ├── token.py      ← Token dataclass
    │       │   └── lexer.py      ← Lexer class (DFA, char-by-char)
    │       └── utils/
    │           └── output.py     ← emit_section / format_token_table / format_error_list
    └── tests/
        ├── samples/              ← valid_full.c, errors.c, edge_cases.c
        └── test_lexer.py         ← 17 unit tests (unittest)
```

## Architecture

### ArcaneIDE — PyQt6 IDE

#### `src/core/` — Business logic (no UI)
- `file_manager.py` — Tracks `current_file: Path` and `is_modified`; handles open/save.
- `compiler_runner.py` — Launches `arcane-compiler` as a subprocess via `QProcess`. Resolves the binary as `Path(sys.executable).parent / "arcane-compiler"` (same `.venv` bin). Emits `compilation_started`, `compilation_finished(dict)`, `compilation_error(str)`. Parses stdout with the section protocol.

#### `src/ui/` — Qt widgets
- `main_window.py` — `MainWindow(QMainWindow)` composes all widgets; owns `FileManager` and `CompilerRunner`; all menus/toolbar/signal wiring.
- `editor_widget.py` — `EditorWidget(QsciScintilla)`; supports `set_theme(theme_id)`.
- `output_tabs.py` — `OutputTabs(QTabWidget)` with 7 tabs. Dict keys are lowercase Spanish: `lexico`, `sintactico`, `semantico`, `codigo_intermedio`, `tabla_simbolos`, `errores`, `ejecucion`.
- `file_tree.py` — File explorer; emits `file_double_clicked`.
- `themes/tokyo_night.xml` — Custom QScintilla theme.

#### `src/utils/`
- `constants.py` — `OUTPUT_TAB_NAMES` list (the 7 tab labels).

#### Key detail: `ignore_text_changes` flag
`MainWindow.ignore_text_changes` suppresses `is_modified` when programmatically loading content. Always set to `True` before `editor_widget.set_text()` / `editor_widget.clear()`, restore to `False` after.

---

### ArcaneCompiler — Compiler package

#### Compiler output protocol
stdout must use this format for every section:
```
===SECTION_NAME===
...content...
===END_SECTION_NAME===
```
Section names: `LEXICO`, `SINTACTICO`, `SEMANTICO`, `CODIGO_INTERMEDIO`, `TABLA_SIMBOLOS`, `ERRORES`, `EJECUCION`.

#### `arcane_compiler/lexer/lexer.py` — DFA rules (in priority order)
1. Whitespace — skip; `\n` increments `_line`, resets `_col`.
2. Block comment `/* */` — `COMMENT_BLOCK`; unclosed → `ERROR`.
3. Line comment `//` — `COMMENT_LINE`.
4. Digits → `INTEGER` or `REAL` (if `digit '.' digit`).
5. Letter/`_` → identifier; checked against `RESERVED` map → keyword or `IDENTIFIER`.
6. `"..."` → `STRING_LITERAL` (no multiline).
7. `'...'` → `CHAR_LITERAL`.
8. Two-char operators (maximal munch first): `++ -- <= >= != == && || << >>`.
9. One-char operators/symbols: `+ - * / % ^ < > ! = ( ) { } , ; :`.
10. Anything else → `ERROR` (lexer continues, no halt).

**No `re` module in the DFA.** Character-by-character only.

#### `arcane_compiler/utils/output.py`
- `emit_section(name, content)` — prints `===NAME===\ncontent\n===END_NAME===`.
- `format_token_table(tokens)` — fixed-width table with columns `LÍNEA COL TIPO VALOR`.
- `format_error_list(errors)` — one line per error token: `Error léxico en línea L, columna C: <message>`.

#### CLI entry point (`arcane_compiler/main.py`)
- Args: `arcane-compiler <source_file> <phase>`.
- Valid phases: `lexical syntactic semantic intermediate execution all`.
- Missing args or bad phase → stderr + exit 1.
- File not found → emits `ERRORES` section + exit 1.
- Phase `lexical`/`all`: runs `Lexer`, emits `LEXICO` and `ERRORES`; all other sections emitted empty.

#### Themes (IDE)
Five themes in `MainWindow.themes` and `EditorWidget.set_theme()`. Tokyo Night loads from `src/ui/themes/tokyo_night.xml`. Applying a theme updates both `qt_material` stylesheet and QScintilla editor colors.
