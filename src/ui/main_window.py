from PyQt6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QFileDialog,
    QMessageBox,
    QLabel,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QActionGroup, QIcon
from pathlib import Path
from qt_material import apply_stylesheet
import os
import qtawesome as qta
from src.ui.editor_widget import EditorWidget
from src.ui.file_tree import FileTree
from src.ui.output_tabs import OutputTabs
from src.core.file_manager import FileManager
from src.core.compiler_runner import CompilerRunner

class MainWindow(QMainWindow):
    """The main window of the IDE, containing all UI components."""

    def __init__(self, app=None):
        super().__init__()
        self.setWindowTitle("Liga de los Compiladores - Sin título")
        self.setGeometry(100, 100, 1200, 800)
        
        # Load and set window icon
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logoIDE.jpg')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.app = app
        self.file_manager = FileManager()
        self.compiler_runner = CompilerRunner()
        self.ignore_text_changes = False  # Flag to ignore programmatic text changes
        
        # Theme definitions: (theme_name, display_name, is_light)
        self.themes = [
            ('dark_purple.xml', 'Dark Purple', False),
            ('dark_blue.xml', 'Dark Blue', False),
            ('tokyo_night', 'Tokyo Night', False),
            ('light_blue.xml', 'Light Blue', True),
            ('light_cyan.xml', 'Light Cyan', True),
        ]
        self.current_theme = 'dark_purple.xml'

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
        """Creates QAction instances for menus and toolbars with modern icons."""
        # File actions with QtAwesome icons
        self.new_action = QAction(qta.icon('fa6s.file', color='white'), "&Nuevo", self, shortcut=QKeySequence.StandardKey.New, triggered=self._new_file)
        self.open_action = QAction(qta.icon('fa6s.folder-open', color='white'), "&Abrir...", self, shortcut=QKeySequence.StandardKey.Open, triggered=self._open_file)
        self.save_action = QAction(qta.icon('fa6s.floppy-disk', color='white'), "&Guardar", self, shortcut=QKeySequence.StandardKey.Save, triggered=self._save_file)
        self.save_as_action = QAction(qta.icon('fa6s.file-export', color='white'), "Guardar &como...", self, shortcut=QKeySequence.StandardKey.SaveAs, triggered=self._save_file_as)
        self.close_file_action = QAction(qta.icon('fa6s.xmark', color='white'), "&Cerrar", self, shortcut=QKeySequence.StandardKey.Close, triggered=self._close_file)
        self.exit_action = QAction(qta.icon('fa6s.door-open', color='white'), "Sa&lir", self, shortcut=QKeySequence.StandardKey.Quit, triggered=self.close)

        # Store file action references for icon color updates
        self.file_actions = [self.new_action, self.open_action, self.save_action, self.save_as_action, self.close_file_action, self.exit_action]

        # Compiler phase actions with QtAwesome icons
        self.lexical_action = QAction(qta.icon('fa6s.code', color='#61dafb'), "Análisis léxico", self, shortcut="F5", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_lexical_analysis))
        self.syntactic_action = QAction(qta.icon('fa6s.diagram-project', color='#61dafb'), "Análisis sintáctico", self, shortcut="F6", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_syntactic_analysis))
        self.semantic_action = QAction(qta.icon('fa6s.circle-check', color='#61dafb'), "Análisis semántico", self, shortcut="F7", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_semantic_analysis))
        self.intermediate_action = QAction(qta.icon('fa6s.terminal', color='#61dafb'), "Código intermedio", self, shortcut="F8", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_intermediate_generation))
        self.execute_action = QAction(qta.icon('fa6s.play', color='#61dafb'), "Ejecutar", self, shortcut="F9", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_execution))

        self.new_action.setToolTip("Nuevo")
        self.open_action.setToolTip("Abrir")
        self.save_action.setToolTip("Guardar")
        self.save_as_action.setToolTip("Guardar como")
        self.close_file_action.setToolTip("Cerrar")
        self.exit_action.setToolTip("Salir")
        self.lexical_action.setToolTip("Análisis léxico")
        self.syntactic_action.setToolTip("Análisis sintáctico")
        self.semantic_action.setToolTip("Análisis semántico")
        self.intermediate_action.setToolTip("Código intermedio")
        self.execute_action.setToolTip("Ejecutar")

    def _create_menus(self):
        """Creates the main menu bar."""
        file_menu = self.menuBar().addMenu("&Archivo")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.close_file_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        compile_menu = self.menuBar().addMenu("&Compilar")
        compile_menu.addAction(self.lexical_action)
        compile_menu.addAction(self.syntactic_action)
        compile_menu.addAction(self.semantic_action)
        compile_menu.addAction(self.intermediate_action)
        compile_menu.addSeparator()
        compile_menu.addAction(self.execute_action)
        
        self._create_theme_menu()

    def _create_toolbar(self):
        """Creates the toolbar with modern styling."""
        file_toolbar = self.addToolBar("Archivo")
        file_toolbar.setIconSize(QSize(20, 20))
        file_toolbar.addAction(self.new_action)
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.save_action)
        file_toolbar.addSeparator()

        compile_toolbar = self.addToolBar("Compilar")
        compile_toolbar.setIconSize(QSize(20, 20))
        compile_toolbar.addAction(self.lexical_action)
        compile_toolbar.addAction(self.syntactic_action)
        compile_toolbar.addAction(self.semantic_action)
        compile_toolbar.addAction(self.intermediate_action)
        compile_toolbar.addSeparator()
        compile_toolbar.addAction(self.execute_action)

    def _create_status_bar(self):
        """Creates the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.cursor_position_label = QLabel("Línea: 1, Columna: 1")
        self.status_bar.addPermanentWidget(self.cursor_position_label)
        self.status_bar.showMessage("Listo")

    def _connect_signals(self):
        """Connects signals from widgets to main window slots."""
        self.file_tree.file_double_clicked.connect(self._open_file_from_path)
        self.editor_widget.cursorPositionChanged.connect(self._update_status_bar)
        # Only mark as modified if not ignoring text changes
        self.editor_widget.textChanged.connect(self._on_text_changed)
        
        self.compiler_runner.compilation_started.connect(lambda: self.status_bar.showMessage("Compilando..."))
        self.compiler_runner.compilation_finished.connect(self._handle_compilation_finished)
        self.compiler_runner.compilation_error.connect(self._handle_compilation_error)
    
    def _on_text_changed(self):
        """Handle text changes, respecting the ignore flag."""
        if not self.ignore_text_changes:
            self.file_manager.mark_modified(True)

    def _update_status_bar(self):
        line = self.editor_widget.get_current_line_number()
        col = self.editor_widget.get_current_column_number()
        self.cursor_position_label.setText(f"Línea: {line}, Columna: {col}")

    def _new_file(self):
        if self._prompt_to_save():
            self.ignore_text_changes = True
            self.editor_widget.clear()
            self.file_manager.new_file()
            self.ignore_text_changes = False
            self.setWindowTitle("Liga de los Compiladores - Sin título")

    def _close_file(self):
        if not self._prompt_to_save():
            return

        self.ignore_text_changes = True
        self.editor_widget.clear()
        self.output_tabs.clear_all()
        self.file_manager.new_file()
        self.ignore_text_changes = False
        self.setWindowTitle("Liga de los Compiladores - Sin título")
        self.status_bar.showMessage("Archivo cerrado", 3000)

    def _open_file(self):
        if not self._prompt_to_save():
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo", filter="Todos los archivos (*);;Archivos de texto (*.txt)")
        if file_path:
            self._open_file_from_path(file_path)

    def _open_file_from_path(self, file_path: str):
        try:
            content = self.file_manager.open_file(file_path)
            self.ignore_text_changes = True
            self.editor_widget.set_text(content)
            self.ignore_text_changes = False
            self.file_tree.set_root_path(str(Path(file_path).parent))
            self.setWindowTitle(f"Liga de los Compiladores - {self.file_manager.get_current_file().name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo: {e}")

    def _save_file(self) -> bool:
        if not self.file_manager.get_current_file():
            return self._save_file_as()
        
        content = self.editor_widget.get_text()
        if self.file_manager.save_file(content):
            self.status_bar.showMessage("Archivo guardado.", 3000)
            self.setWindowTitle(f"Liga de los Compiladores - {self.file_manager.get_current_file().name}")
            return True
        QMessageBox.critical(self, "Error", "No se pudo guardar el archivo.")
        return False

    def _save_file_as(self) -> bool:
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo como", filter="Todos los archivos (*);;Archivos de texto (*.txt)")
        if file_path:
            content = self.editor_widget.get_text()
            if self.file_manager.save_file_as(content, file_path):
                self.file_tree.set_root_path(str(Path(file_path).parent))
                self.setWindowTitle(f"Liga de los Compiladores - {self.file_manager.get_current_file().name}")
                self.status_bar.showMessage(f"Archivo guardado como {file_path}", 3000)
                return True
            QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo en {file_path}.")
        return False

    def _prompt_to_save(self) -> bool:
        if not self.file_manager.is_modified:
            return True
        
        reply = QMessageBox.question(self, "Cambios sin guardar",
                         "Tienes cambios sin guardar. ¿Deseas guardarlos?",
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
             QMessageBox.warning(self, "Sin archivo", "Abre o guarda un archivo antes de compilar.")
             return

        self.output_tabs.clear_all()
        phase_func(str(self.file_manager.get_current_file()))

    def _handle_compilation_finished(self, results: dict):
        self.status_bar.showMessage("Compilación finalizada correctamente.", 5000)
        self.output_tabs.update_tokens(results.get("tokens", ""))
        self.output_tabs.update_ast(results.get("ast", ""))
        self.output_tabs.update_semantic(results.get("semantic", ""))
        self.output_tabs.update_intermediate_code(results.get("intermediate", ""))
        self.output_tabs.update_symbol_table(results.get("symbols", ""))
        self.output_tabs.update_errors(results.get("errors", "# Sin errores"))
        self.output_tabs.update_execution(results.get("execution", ""))

    def _handle_compilation_error(self, error_msg: str):
        self.status_bar.showMessage("La compilación falló.", 5000)
        self.output_tabs.update_errors(f"ERROR DEL COMPILADOR:\n{error_msg}")
        self.output_tabs.setCurrentWidget(self.output_tabs.tabs["errores"])

    def _create_theme_menu(self):
        """Creates a View menu with theme options."""
        view_menu = self.menuBar().addMenu("&Vista")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        
        for theme_id, display_name, is_light in self.themes:
            theme_action = QAction(display_name, self, checkable=True)
            if theme_id == self.current_theme:
                theme_action.setChecked(True)
            theme_action.triggered.connect(lambda checked, t=theme_id: self._apply_theme(t))
            theme_group.addAction(theme_action)
            view_menu.addAction(theme_action)
    
    def _update_icon_colors(self, is_light: bool):
        """Updates icon colors based on theme brightness."""
        icon_color = '#000000' if is_light else 'white'
        icons_config = [
            (self.new_action, 'fa6s.file'),
            (self.open_action, 'fa6s.folder-open'),
            (self.save_action, 'fa6s.floppy-disk'),
            (self.save_as_action, 'fa6s.file-export'),
            (self.close_file_action, 'fa6s.xmark'),
            (self.exit_action, 'fa6s.door-open'),
        ]
        
        for action, icon_name in icons_config:
            action.setIcon(qta.icon(icon_name, color=icon_color))
        
        # Also update file tree icons
        self.file_tree.set_icon_color(icon_color)

    def _apply_theme(self, theme_id: str):
        """Applies a theme dynamically to the entire app and editor."""
        if not self.app:
            return
        
        self.current_theme = theme_id
        
        # Find if it's a light theme
        is_light = next((t[2] for t in self.themes if t[0] == theme_id), False)
        
        if theme_id == 'tokyo_night':
            theme_path = os.path.join(os.path.dirname(__file__), 'themes', 'tokyo_night.xml')
            apply_stylesheet(self.app, theme=theme_path)
        else:
            apply_stylesheet(self.app, theme=theme_id, invert_secondary=is_light)
        
        # Update icon colors based on theme brightness
        self._update_icon_colors(is_light)
        
        # Also update the editor widget theme
        self.editor_widget.set_theme(theme_id)

    def closeEvent(self, event):
        if self._prompt_to_save():
            event.accept()
        else:
            event.ignore()
