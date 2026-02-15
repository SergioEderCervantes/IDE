# Compiler IDE

A simple, lightweight IDE for developing and testing compilers, built with Python and PyQt6.

This project provides a basic but functional Integrated Development Environment (IDE) featuring a code editor with syntax highlighting, a file system explorer, and an interface to run a compiler and visualize its output through various stages.

## Features

- **Code Editor**: A professional code editor based on QScintilla with features like:
  - Line numbering
  - Syntax highlighting (currently generic, can be extended)
  - Auto-indentation
- **File System Explorer**: A tree view to browse and open files from the project directory.
- **Compiler Integration**: A simple interface to run an external compiler script.
  - Toolbar buttons and shortcuts (F5-F9) to trigger different compilation phases.
- **Tabbed Output**: View the output of each compilation phase in separate tabs:
  - Tokens, AST, Semantic Analysis, Intermediate Code, Symbol Table, Errors, and Execution output.
- **File Management**: Standard file operations:
  - New, Open, Save, Save As...
  - Prompts for unsaved changes.

## Setup and Installation

This project is built using Python and PyQt6.

### 1. Prerequisites
- Python 3.10 or higher
- `pip` for installing packages

### 2. Environment Setup

It is highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
# .venv\\Scripts\\activate
```

### 3. Install Dependencies

Install the required packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## How to Run

Once the dependencies are installed and the virtual environment is active, run the application with the following command from the project's root directory:

```bash
python -m src.main
```

The IDE window should appear.

## How to Use

1.  Use the file explorer on the left to navigate and double-click a file to open it in the editor.
2.  Use the "File" menu or the toolbar icons (Ctrl+N, Ctrl+O, Ctrl+S) to manage files.
3.  Write your code in the editor.
4.  Use the "Compile" menu, the toolbar icons, or the function keys (F5-F9) to run the compiler on the currently active file.
5.  The results of the compilation will appear in the tabs at the bottom right.
