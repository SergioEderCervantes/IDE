# IDE para Compiladores - Instrucciones de Implementación

## Objetivo
Desarrollar un IDE en Python usando PyQt5 que permita editar código fuente e invocar un compilador externo (por ahora un script dummy), visualizando los resultados de cada fase de compilación.

## Stack Tecnológico
- **Python 3.10+**
- **PySide6** - Framework GUI oficial de Qt
- **PyQt6-QScintilla** - Editor de texto profesional con syntax highlighting, numeración de líneas y más

> **Nota sobre mixing PySide6 + PyQt6-QScintilla:** No existe versión oficial PySide6-QScintilla, pero PyQt6-QScintilla es compatible y funciona perfectamente mezclado con PySide6 en el mismo proyecto.

---

## 🤖 Instrucciones para Gemini CLI

**Contexto de ejecución:**
- Trabajarás en un entorno con Python 3.10+ ya instalado
- El entorno virtual `.venv` estará **activo** durante toda la implementación
- Todos los comandos `python`, `pip`, etc. se ejecutan dentro del venv
- No necesitas preocuparte por activar/desactivar el venv manualmente

**Flujo de trabajo:**
1. Sigue el **Orden de Implementación** paso a paso (ver sección más abajo)
2. Después de cada componente, verifica que funciona antes de continuar
3. Usa `python src/main.py` para probar cambios en la UI
4. Usa `python compiler/compiler.py test.txt` para probar el compilador standalone

**Convenciones de código:**
- Usa type hints en todas las funciones públicas
- Docstrings solo en clases y métodos no obvios
- Imports: PySide6 para widgets principales, PyQt6.Qsci para QScintilla, luego módulos propios
- Naming: `snake_case` para funciones/variables, `PascalCase` para clases
- **IMPORTANTE:** Usa `Signal` (PySide6), NO `pyqtSignal` (PyQt). Para enums usa la forma completa: `QsciScintilla.MarginType.NumberMargin`

**Testing durante desarrollo:**
No necesitas escribir unit tests, pero sí verifica manualmente:
- Cada componente funciona aislado antes de integrarlo
- Los signals/slots se conectan correctamente
- No hay crashes en operaciones básicas

---

## Estructura del Proyecto

```
IDE/
├── pyproject.toml
├── compiler/
│   └── compiler.py          # Script dummy del compilador (independiente)
├── src/
│   ├── main.py              # Entry point
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py   # Ventana principal
│   │   ├── editor_widget.py # Panel de editor
│   │   ├── file_tree.py     # Explorador de archivos
│   │   └── output_tabs.py   # Tabs para resultados
│   ├── core/
│   │   ├── __init__.py
│   │   ├── compiler_runner.py  # Manejo de llamadas al compilador
│   │   └── file_manager.py     # Gestión de archivos
│   └── utils/
│       ├── __init__.py
│       └── constants.py      # Constantes y configuración
└── README.md
```

## Setup del Entorno

**Prerrequisitos:** Python 3.10 o superior instalado

### Configuración Inicial (la que ya esta hecha)

```bash
# 1. Crear entorno virtual
python3 -m venv .venv

# 2. Activar entorno virtual
# En Linux/Mac:
source .venv/bin/activate
# En Windows:
# .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -c "from PySide6.QtWidgets import QApplication; from PyQt6.Qsci import QsciScintilla; print('✓ Dependencias instaladas correctamente')"
```

### Archivos de Configuración

**requirements.txt:**
```
PySide6>=6.6.0
PyQt6-QScintilla>=2.14.0
```

**pyproject.toml** (opcional, para metadata):
```toml
[project]
name = "compiler-ide"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "PySide6>=6.6.0",
    "PyQt6-QScintilla>=2.14.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**IMPORTANTE para Gemini CLI:** 
- El entorno virtual `.venv` estará activo durante toda la implementación
- Todos los comandos `python` y `pip` se ejecutan dentro del venv
- No es necesario usar uv, hatch, poetry ni otros gestores

## Componentes a Implementar

### 1. Main Window (main_window.py)
**Responsabilidad:** Contenedor principal del IDE con layout y menús

**Layout:**
```
┌─────────────────────────────────────────┐
│ MenuBar: Archivo | Compilar            │
│ ToolBar: [Léxico][Sintáctico][...]     │
├─────────┬───────────────────────────────┤
│ File    │  Editor                       │
│ Tree    │  (Editor de código)           │
│ (20%)   │  (50%)                        │
│         ├───────────────────────────────┤
│         │  Output Tabs                  │
│         │  [Tokens|AST|Errores|...]     │
│         │  (30%)                        │
└─────────┴───────────────────────────────┘
```

**Menús:**
- **Archivo:**
  - Nuevo (Ctrl+N)
  - Abrir (Ctrl+O)
  - Guardar (Ctrl+S)
  - Guardar Como (Ctrl+Shift+S)
  - Cerrar
  - Salir (Ctrl+Q)

- **Compilar:**
  - Análisis Léxico (F5)
  - Análisis Sintáctico (F6)
  - Análisis Semántico (F7)
  - Generación Código Intermedio (F8)
  - Ejecución (F9)

**Toolbar:** Botones rápidos para cada fase de compilación

### 2. Editor Widget (editor_widget.py)
**Responsabilidad:** Panel de edición de código con capacidades profesionales

**Implementación base: QsciScintilla**
```python
from PyQt6.Qsci import QsciScintilla, QsciLexerPython
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QWidget

class EditorWidget(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración básica
        self.setUtf8(True)
        font = QFont("Courier New", 10)
        self.setFont(font)
        
        # Numeración de líneas (built-in)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginsForegroundColor(QColor("#888888"))
        
        # Syntax highlighting (opcional - puede ser Python por defecto)
        # lexer = QsciLexerPython()
        # lexer.setFont(font)
        # self.setLexer(lexer)
        
        # Configuraciones adicionales útiles
        self.setIndentationGuides(True)
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)
```

**Características que vienen GRATIS con QsciScintilla:**
- ✅ Numeración de líneas (ya no hay que implementar custom widget)
- ✅ Syntax highlighting con lexers predefinidos
- ✅ Marcadores y breakpoints (para futuro debugging)
- ✅ Auto-indentación
- ✅ Búsqueda y reemplazo built-in
- ✅ Trackeo de posición del cursor

**API Pública:**
```python
class EditorWidget(QsciScintilla):
    def get_text(self) -> str:
        """Retorna todo el texto del editor"""
        return self.text()
    
    def set_text(self, text: str) -> None:
        """Establece el texto del editor"""
        self.setText(text)
    
    def get_current_line(self) -> int:
        """Retorna línea actual (0-indexed)"""
        line, _ = self.getCursorPosition()
        return line + 1  # Convertir a 1-indexed para mostrar
    
    def get_current_column(self) -> int:
        """Retorna columna actual (0-indexed)"""
        _, col = self.getCursorPosition()
        return col + 1  # Convertir a 1-indexed
    
    def clear_editor(self) -> None:
        """Limpia todo el contenido"""
        self.clear()
```

### 3. File Tree (file_tree.py)
**Responsabilidad:** Explorador de archivos del proyecto/directorio actual

**Implementación:**
```python
from PySide6.QtWidgets import QTreeView, QWidget, QVBoxLayout
from PySide6.QtCore import QDir, Signal
from PySide6.QtGui import QFileSystemModel

class FileTree(QWidget):
    file_double_clicked = Signal(str)  # Emite ruta del archivo
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.currentPath())
        
        # Filtros: mostrar solo archivos de texto comunes
        self.model.setNameFilters(["*.txt", "*.c", "*.cpp", "*.py", "*.java"])
        self.model.setNameFilterDisables(False)
        
        # Tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.currentPath()))
        
        # Configuración visual
        self.tree.setColumnWidth(0, 200)
        self.tree.setHeaderHidden(False)
        self.tree.hideColumn(1)  # Ocultar tamaño
        self.tree.hideColumn(2)  # Ocultar tipo
        self.tree.hideColumn(3)  # Ocultar fecha
        
        # Conectar señal de doble click
        self.tree.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.tree)
    
    def _on_double_click(self, index):
        """Maneja doble click en archivo"""
        file_path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_double_clicked.emit(file_path)
    
    def set_root_path(self, path: str):
        """Cambia el directorio raíz mostrado"""
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
```

**Uso en MainWindow:**
```python
self.file_tree = FileTree()
self.file_tree.file_double_clicked.connect(self.open_file_from_tree)
```

### 4. Output Tabs (output_tabs.py)
**Responsabilidad:** Visualización de resultados del compilador

**Tabs requeridos:**
1. **Tokens** - Resultado análisis léxico
2. **AST** - Árbol sintáctico
3. **Semántico** - Validaciones semánticas
4. **Código Intermedio** - Representación intermedia
5. **Tabla de Símbolos** - Símbolos identificados
6. **Errores** - Lista de errores (todos los tipos)
7. **Ejecución** - Salida del programa

**Implementación:**
- `QTabWidget` con 7 tabs
- Cada tab contiene un `QTextEdit` (read-only)
- Método para actualizar contenido de cada tab

**API Pública:**
```python
class OutputTabs(QTabWidget):
    def update_tokens(self, content: str) -> None
    def update_ast(self, content: str) -> None
    def update_semantic(self, content: str) -> None
    def update_intermediate(self, content: str) -> None
    def update_symbols(self, content: str) -> None
    def update_errors(self, content: str) -> None
    def update_execution(self, content: str) -> None
    def clear_all(self) -> None
```

### 5. Compiler Runner (compiler_runner.py)
**Responsabilidad:** Invocar el compilador externo y capturar resultados

**Funcionamiento:**
- Usa `QProcess` para llamadas asíncronas
- No bloquea la UI durante compilación
- Captura stdout/stderr del compilador
- Parsea la salida del compilador según formato definido

**Formato de comunicación compilador → IDE:**
El compilador dummy debe imprimir en stdout con formato estructurado:

```
===TOKENS===
<contenido de tokens>
===END_TOKENS===
===AST===
<contenido del árbol>
===AST_END===
===ERRORS===
[LEXICO] Línea 5: Token inválido '@@'
[SINTACTICO] Línea 10: Se esperaba ';'
===ERRORS_END===
```

**API Pública:**
```python
from PySide6.QtCore import QObject, QProcess, Signal

class CompilerRunner(QObject):
    # Signals
    compilation_started = Signal()
    compilation_finished = Signal(dict)  # dict con resultados parseados
    compilation_error = Signal(str)
    
    def run_lexical_analysis(self, source_file: str) -> None
    def run_syntactic_analysis(self, source_file: str) -> None
    def run_semantic_analysis(self, source_file: str) -> None
    def run_intermediate_generation(self, source_file: str) -> None
    def run_execution(self, source_file: str) -> None
```

### 6. File Manager (file_manager.py)
**Responsabilidad:** Gestión de archivos (nuevo, abrir, guardar)

**API Pública:**
```python
class FileManager:
    def __init__(self):
        self.current_file: Optional[Path] = None
        self.is_modified: bool = False
    
    def new_file(self) -> None
    def open_file(self, filepath: Optional[str] = None) -> Optional[str]
    def save_file(self, content: str) -> bool
    def save_file_as(self, content: str, filepath: Optional[str] = None) -> bool
    def get_current_file(self) -> Optional[Path]
    def mark_modified(self, modified: bool = True) -> None
```

### 7. Compiler Dummy (compiler/compiler.py)
**Script independiente** que simula el compilador

**Por ahora:** Script simple que imprime salida estructurada

```python
#!/usr/bin/env python3
import sys

def main():
    if len(sys.argv) < 2:
        print("Uso: compiler.py <archivo_fuente>", file=sys.stderr)
        sys.exit(1)
    
    source_file = sys.argv[1]
    
    # Simular salida estructurada
    print("===TOKENS===")
    print("INT: 'int' (línea 1, col 0)")
    print("IDENTIFIER: 'x' (línea 1, col 4)")
    print("ASSIGN: '=' (línea 1, col 6)")
    print("NUMBER: '5' (línea 1, col 8)")
    print("===END_TOKENS===")
    
    print("===AST===")
    print("Program")
    print("  └─ VarDeclaration")
    print("      ├─ Type: int")
    print("      ├─ Name: x")
    print("      └─ Value: 5")
    print("===END_AST===")
    
    print("===SEMANTIC===")
    print("✓ Sin errores semánticos")
    print("===END_SEMANTIC===")
    
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
    
    print("===EXECUTION===")
    print("Hello World from Compiler!")
    print("===END_EXECUTION===")

if __name__ == "__main__":
    main()
```

**Invocación desde IDE:**
```bash
python compiler/compiler.py <archivo_con_codigo.txt>
```

## Flujo de Trabajo

### 1. Inicio de la aplicación
1. Usuario ejecuta `python src/main.py`
2. Se crea `MainWindow` con todos los widgets
3. Se muestra editor vacío, file tree apuntando a directorio actual
4. Tabs de output vacíos

### 2. Edición de código
1. Usuario escribe código en `EditorWidget`
2. Status bar muestra línea:columna actual
3. File manager marca documento como modificado
4. Título de ventana muestra "*" si hay cambios sin guardar

### 3. Compilación (ejemplo: Análisis Léxico)
1. Usuario presiona F5 o click en botón "Léxico"
2. Si hay cambios sin guardar:
   - Mostrar diálogo: "¿Guardar cambios antes de compilar?"
3. `MainWindow` llama a `compiler_runner.run_lexical_analysis(file_path)`
4. `CompilerRunner`:
   - Crea `QProcess`
   - Ejecuta: `python compiler/compiler.py --phase=lexical <file>`
   - Emite señal `compilation_started`
5. Durante compilación:
   - Cursor muestra "busy"
   - Status bar: "Compilando..."
6. Al terminar:
   - `CompilerRunner` parsea stdout
   - Emite señal `compilation_finished` con dict de resultados
7. `MainWindow` recibe resultados:
   - Actualiza tabs correspondientes via `OutputTabs`
   - Muestra tab activo (ej: "Tokens")
   - Status bar: "Compilación terminada"

### 4. Visualización de errores
1. Si hay errores, el tab "Errores" muestra lista
2. Formato: `[TIPO] Línea X: Descripción`
3. (Opcional v2) Click en error → saltar a línea en editor

## Consideraciones de Implementación

### Threading y Asincronía
- **NO** usar threads manualmente
- `QProcess` ya es asíncrono y thread-safe
- Usar signals/slots de Qt para comunicación entre componentes

### Manejo de Estado
- `FileManager` mantiene estado del archivo actual
- `MainWindow` coordina entre componentes
- No duplicar estado entre widgets

### Extensibilidad Futura
- `CompilerRunner` usa patrón Strategy para diferentes fases
- Fácil agregar nuevas fases de compilación
- Format de comunicación extensible con nuevos bloques `===SECTION===`

### Errores y Edge Cases
- Validar que existe `compiler/compiler.py` al inicio
- Manejar timeout en compilación (30 segundos)
- Validar formato de salida del compilador
- Guardar archivo antes de compilar si es necesario
- Prevenir compilación múltiple simultánea

## Ejecución de la Aplicación

### Desde la raíz del proyecto:

```bash
# Asegurarse que el venv está activo
source .venv/bin/activate  # o .venv\Scripts\activate en Windows

# Ejecutar el IDE
python src/main.py
```

### Testing básico sin GUI (opcional):

```bash
# Probar el compilador dummy standalone
python compiler/compiler.py test_file.txt

# Probar FileManager
python -m src.core.file_manager

# Probar CompilerRunner (si tiene métodos de prueba)
python -m src.core.compiler_runner
```

## Orden de Implementación Sugerido

**Fase 0: Setup (15 min)**
1. Crear estructura de carpetas
2. Crear `requirements.txt` con PySide6 y PyQt6-QScintilla
3. Crear venv: `python3 -m venv .venv`
4. Activar venv: `source .venv/bin/activate`
5. Instalar deps: `pip install -r requirements.txt`
6. Verificar: `python -c "from PySide6.QtWidgets import QApplication; from PyQt6.Qsci import QsciScintilla; print('OK')"`
7. Crear archivos `__init__.py` en todos los paquetes

**Fase 1: Compilador Dummy (20 min)**
7. Crear `compiler/compiler.py` funcional
8. Probar desde terminal: `python compiler/compiler.py test.txt`
9. Verificar que imprime formato estructurado correcto

**Fase 2: Core Logic (30 min)**
10. Implementar `FileManager` - sin GUI, solo lógica de archivos
11. Implementar `CompilerRunner` - QProcess + parsing de salida

**Fase 3: UI Básica (45 min)**
12. Crear `main.py` - entry point básico
13. Crear `MainWindow` - shell con QSplitter y layout
14. Crear `EditorWidget` - QsciScintilla configurado
15. Crear `FileTree` - QTreeView + QFileSystemModel
16. Crear `OutputTabs` - QTabWidget con 7 tabs

**Fase 4: Integración (30 min)**
17. Conectar señales/slots entre componentes
18. Implementar menús (Archivo, Compilar)
19. Implementar toolbar con botones
20. Implementar status bar (línea:columna)

**Fase 5: Testing & Polish (20 min)**
21. Probar flujo completo: abrir → editar → compilar → ver resultados
22. Verificar shortcuts funcionan
23. Agregar íconos básicos si es necesario
24. Escribir README.md con instrucciones de uso

**Total estimado: ~2.5 horas** para MVP funcional

## Criterios de Éxito MVP

- ✅ Puede crear, abrir, editar y guardar archivos
- ✅ Menús y shortcuts funcionan (Ctrl+N, Ctrl+O, Ctrl+S, F5-F9)
- ✅ File tree muestra archivos del directorio
- ✅ Editor usa QsciScintilla con numeración de líneas visible
- ✅ Status bar muestra línea:columna en tiempo real
- ✅ Botones de compilación invocan el compiler.py con QProcess
- ✅ Resultados aparecen en tabs correspondientes parseados correctamente
- ✅ No crashea en operaciones básicas
- ✅ Compilador funciona standalone: `python compiler/compiler.py archivo.txt`
- ✅ Ventana es redimensionable y paneles ajustan proporcionalmente

## Notas Importantes

- **Simplicidad primero:** No optimizar prematuramente
- **Modularidad:** Cada componente puede evolucionar independientemente
- **Testabilidad:** FileManager y CompilerRunner deben poder testearse sin GUI
- **No reinventar:** Usar widgets estándar de Qt cuando sea posible
- **El compilador es black box:** El IDE solo consume su salida estructurada

## Siguiente Fase (Futuro)
- Syntax highlighting personalizado
- Autocompletado
- Click en error → ir a línea
- Configuración de rutas y parámetros
- Temas de color
- Múltiples archivos abiertos (tabs en editor)