# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run the IDE
python -m src.main
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Architecture

This is a PyQt6-based IDE called **ArcaneIDE** for developing and testing compilers. It has a clear separation into three layers:

### `src/core/` — Business logic (no UI)
- `file_manager.py` — Tracks `current_file: Path` and `is_modified` state; handles open/save operations.
- `compiler_runner.py` — Runs `compiler/compiler.py` as a subprocess via `QProcess`. Emits `compilation_started`, `compilation_finished(dict)`, and `compilation_error(str)` signals. Parses compiler stdout using the section format `===SECTION_NAME===...===END_SECTION_NAME===`.

### `src/ui/` — Qt widgets
- `main_window.py` — `MainWindow(QMainWindow)` composes all widgets. Owns `FileManager` and `CompilerRunner`. Contains all action/menu/toolbar setup and connects signals between components.
- `editor_widget.py` — `EditorWidget(QsciScintilla)` wraps QScintilla for code editing. Supports `set_theme(theme_id)` to update colors.
- `output_tabs.py` — `OutputTabs(QTabWidget)` displays compiler output in 7 tabs (Tokens, Sintáctico, Semántico, Código Intermedio, Tabla de Símbolos, Errores, Ejecución). Tab keys in `self.tabs` dict use lowercase Spanish names.
- `file_tree.py` — File explorer tree view; emits `file_double_clicked` signal.

### `compiler/` — External compiler stub
- `compiler/compiler.py` — Called by `CompilerRunner` as `python compiler/compiler.py <source_file> <phase>`. Accepted phases: `lexical`, `syntactic`, `semantic`, `intermediate`, `execution`, `all`. **This is currently a stub** with hardcoded sample output — replace with the real compiler implementation here.

### Compiler output protocol
The compiler script must write to stdout using this exact format for each section:
```
===SECTION_NAME===
...content...
===END_SECTION_NAME===
```
Section names mapped to output tabs: `LEXICO`, `SINTACTICO`, `SEMANTICO`, `CODIGO_INTERMEDIO`, `TABLA_SIMBOLOS`, `ERRORES`, `EJECUCION`.

### Themes
Five themes are defined in `MainWindow.themes` and `EditorWidget.set_theme()`. A custom `tokyo_night` theme loads from `src/ui/themes/tokyo_night.xml`. Applying a theme updates both the `qt_material` stylesheet and the QScintilla editor colors.

### Key detail: `ignore_text_changes` flag
`MainWindow` uses `self.ignore_text_changes` to suppress `is_modified` being set when programmatically loading file content into the editor (e.g., on open). Always set this flag to `True` before calling `editor_widget.set_text()` or `editor_widget.clear()`, then restore it to `False` after.
