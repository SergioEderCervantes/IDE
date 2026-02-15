from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QSplitter, QStatusBar, QFileDialog, QMessageBox, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from src.ui.editor_widget import EditorWidget
from src.ui.file_tree import FileTree
from src.ui.output_tabs import OutputTabs
from src.core.file_manager import FileManager
from src.core.compiler_runner import CompilerRunner

class MainWindow(QMainWindow):
    """The main window of the IDE, containing all UI components."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compiler IDE - Untitled")
        self.setGeometry(100, 100, 1200, 800)

        self.file_manager = FileManager()
        self.compiler_runner = CompilerRunner()

        self._setup_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()
        self._connect_signals()

    def _setup_ui(self):
        """Sets up the main layout with splitters."""
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor_widget = EditorWidget()
        self.output_tabs = OutputTabs()
        right_splitter.addWidget(self.editor_widget)
        right_splitter.addWidget(self.output_tabs)
        right_splitter.setSizes([600, 200])

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.file_tree = FileTree()
        main_splitter.addWidget(self.file_tree)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([250, 950])

        self.setCentralWidget(main_splitter)

    def _create_actions(self):
        """Creates QAction instances for menus and toolbars."""
        style = self.style()
        self.new_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon), "&New", self, shortcut=QKeySequence.StandardKey.New, triggered=self._new_file)
        self.open_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "&Open...", self, shortcut=QKeySequence.StandardKey.Open, triggered=self._open_file)
        self.save_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "&Save", self, shortcut=QKeySequence.StandardKey.Save, triggered=self._save_file)
        self.save_as_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save &As...", self, shortcut=QKeySequence.StandardKey.SaveAs, triggered=self._save_file_as)
        self.exit_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "E&xit", self, shortcut=QKeySequence.StandardKey.Quit, triggered=self.close)

        self.lexical_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight), "Lexical Analysis", self, shortcut="F5", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_lexical_analysis))
        self.syntactic_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight), "Syntactic Analysis", self, shortcut="F6", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_syntactic_analysis))
        self.semantic_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight), "Semantic Analysis", self, shortcut="F7", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_semantic_analysis))
        self.intermediate_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight), "Intermediate Code", self, shortcut="F8", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_intermediate_generation))
        self.execute_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Execute", self, shortcut="F9", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_execution))

    def _create_menus(self):
        """Creates the main menu bar."""
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        compile_menu = self.menuBar().addMenu("&Compile")
        compile_menu.addAction(self.lexical_action)
        compile_menu.addAction(self.syntactic_action)
        compile_menu.addAction(self.semantic_action)
        compile_menu.addAction(self.intermediate_action)
        compile_menu.addSeparator()
        compile_menu.addAction(self.execute_action)

    def _create_toolbar(self):
        """Creates the toolbar."""
        file_toolbar = self.addToolBar("File")
        file_toolbar.addAction(self.new_action)
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.save_action)

        compile_toolbar = self.addToolBar("Compile")
        compile_toolbar.addAction(self.lexical_action)
        compile_toolbar.addAction(self.syntactic_action)
        compile_toolbar.addAction(self.semantic_action)
        compile_toolbar.addAction(self.intermediate_action)
        compile_toolbar.addAction(self.execute_action)

    def _create_status_bar(self):
        """Creates the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _connect_signals(self):
        """Connects signals from widgets to main window slots."""
        self.file_tree.file_double_clicked.connect(self._open_file_from_path)
        self.editor_widget.cursorPositionChanged.connect(self._update_status_bar)
        self.editor_widget.textChanged.connect(lambda: self.file_manager.mark_modified(True))
        
        self.compiler_runner.compilation_started.connect(lambda: self.status_bar.showMessage("Compiling..."))
        self.compiler_runner.compilation_finished.connect(self._handle_compilation_finished)
        self.compiler_runner.compilation_error.connect(self._handle_compilation_error)

    def _update_status_bar(self):
        line = self.editor_widget.get_current_line_number()
        col = self.editor_widget.get_current_column_number()
        self.status_bar.showMessage(f"Line: {line}, Column: {col}")

    def _new_file(self):
        if self._prompt_to_save():
            self.editor_widget.clear()
            self.file_manager.new_file()
            self.setWindowTitle("Compiler IDE - Untitled")

    def _open_file(self):
        if not self._prompt_to_save():
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", filter="All Files (*);;Text Files (*.txt)")
        if file_path:
            self._open_file_from_path(file_path)

    def _open_file_from_path(self, file_path: str):
        try:
            content = self.file_manager.open_file(file_path)
            self.editor_widget.set_text(content)
            self.setWindowTitle(f"Compiler IDE - {self.file_manager.get_current_file().name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file: {e}")

    def _save_file(self) -> bool:
        if not self.file_manager.get_current_file():
            return self._save_file_as()
        
        content = self.editor_widget.get_text()
        if self.file_manager.save_file(content):
            self.status_bar.showMessage(f"File saved.", 3000)
            self.setWindowTitle(f"Compiler IDE - {self.file_manager.get_current_file().name}")
            return True
        QMessageBox.critical(self, "Error", "Could not save file.")
        return False

    def _save_file_as(self) -> bool:
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", filter="All Files (*);;Text Files (*.txt)")
        if file_path:
            content = self.editor_widget.get_text()
            if self.file_manager.save_file_as(content, file_path):
                self.setWindowTitle(f"Compiler IDE - {self.file_manager.get_current_file().name}")
                self.status_bar.showMessage(f"File saved as {file_path}", 3000)
                return True
            QMessageBox.critical(self, "Error", f"Could not save file to {file_path}.")
        return False

    def _prompt_to_save(self) -> bool:
        if not self.file_manager.is_modified:
            return True
        
        reply = QMessageBox.question(self, "Unsaved Changes",
                                     "You have unsaved changes. Do you want to save them?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        
        if reply == QMessageBox.StandardButton.Save:
            return self._save_file()
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def _run_compiler_phase(self, phase_func):
        if self.file_manager.is_modified or not self.file_manager.get_current_file():
            if not self._prompt_to_save():
                return
        
        if not self.file_manager.get_current_file():
             QMessageBox.warning(self, "No File", "Please open or save a file before compiling.")
             return

        self.output_tabs.clear_all()
        phase_func(str(self.file_manager.get_current_file()))

    def _handle_compilation_finished(self, results: dict):
        self.status_bar.showMessage("Compilation finished successfully.", 5000)
        self.output_tabs.update_tokens(results.get("tokens", ""))
        self.output_tabs.update_ast(results.get("ast", ""))
        self.output_tabs.update_semantic(results.get("semantic", ""))
        self.output_tabs.update_intermediate_code(results.get("intermediate", ""))
        self.output_tabs.update_symbol_table(results.get("symbols", ""))
        self.output_tabs.update_errors(results.get("errors", "# No errors"))
        self.output_tabs.update_execution(results.get("execution", ""))

    def _handle_compilation_error(self, error_msg: str):
        self.status_bar.showMessage("Compilation failed.", 5000)
        self.output_tabs.update_errors(f"COMPILER ERROR:\n{error_msg}")
        self.output_tabs.setCurrentWidget(self.output_tabs.tabs["errores"])

    def closeEvent(self, event):
        if self._prompt_to_save():
            event.accept()
        else:
            event.ignore()
