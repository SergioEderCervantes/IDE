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
    """La ventana principal del IDE, que contiene todos los componentes de la interfaz."""

    def __init__(self, app=None):
        super().__init__()
        self.setWindowTitle("ArcaneIDE - Sin título")
        self.setGeometry(100, 100, 1200, 800)
        
        # Cargar e establecer el icono de la ventana
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logoIDE.jpg')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.app = app
        self.file_manager = FileManager()
        self.compiler_runner = CompilerRunner()
        self.ignore_text_changes = False  # Bandera para ignorar cambios de texto programáticos
        
        # Definiciones de tema: (nombre_tema, nombre_mostrado, es_claro)
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
        """Configura el diseño principal con divisores."""
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
        """Crea instancias de QAction para menús y barras de herramientas con iconos modernos."""
        # Acciones de archivo con iconos de QtAwesome
        self.new_action = QAction(qta.icon('fa6s.file', color='white'), "&Nuevo", self, shortcut=QKeySequence.StandardKey.New, triggered=self._new_file) # type: ignore
        self.open_action = QAction(qta.icon('fa6s.folder-open', color='white'), "&Abrir...", self, shortcut=QKeySequence.StandardKey.Open, triggered=self._open_file) # type: ignore
        self.save_action = QAction(qta.icon('fa6s.floppy-disk', color='white'), "&Guardar", self, shortcut=QKeySequence.StandardKey.Save, triggered=self._save_file) # type: ignore
        self.save_as_action = QAction(qta.icon('fa6s.file-export', color='white'), "Guardar &como...", self, shortcut=QKeySequence.StandardKey.SaveAs, triggered=self._save_file_as) # type: ignore
        self.close_file_action = QAction(qta.icon('fa6s.xmark', color='white'), "&Cerrar", self, shortcut=QKeySequence.StandardKey.Close, triggered=self._close_file) # type: ignore
        self.exit_action = QAction(qta.icon('fa6s.door-open', color='white'), "Sa&lir", self, shortcut=QKeySequence.StandardKey.Quit, triggered=self.close) # type: ignore

        # Acciones de zoom
        self.zoom_in_action = QAction(qta.icon('fa6s.magnifying-glass-plus', color='white'), "Aumentar Zoom", self, shortcut="Ctrl++", triggered=self.editor_widget.zoomIn) # type: ignore
        self.zoom_out_action = QAction(qta.icon('fa6s.magnifying-glass-minus', color='white'), "Reducir Zoom", self, shortcut="Ctrl+-", triggered=self.editor_widget.zoomOut) # type: ignore
        self.reset_zoom_action = QAction(qta.icon('fa6s.magnifying-glass', color='white'), "Restablecer Zoom", self, shortcut="Ctrl+0", triggered=lambda: self.editor_widget.zoomTo(0)) # type: ignore

        # Almacenar referencias de acciones de archivo para actualizar colores de iconos
        self.file_actions = [self.new_action, self.open_action, self.save_action, self.save_as_action, self.close_file_action, self.exit_action, self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action]

        # Acciones de fases del compilador con iconos de QtAwesome
        self.lexical_action = QAction(qta.icon('fa6s.code', color='#61dafb'), "Análisis léxico", self, shortcut="F5", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_lexical_analysis)) # type: ignore
        self.syntactic_action = QAction(qta.icon('fa6s.diagram-project', color='#61dafb'), "Análisis sintáctico", self, shortcut="F6", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_syntactic_analysis)) # type: ignore
        self.semantic_action = QAction(qta.icon('fa6s.circle-check', color='#61dafb'), "Análisis semántico", self, shortcut="F7", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_semantic_analysis)) # type: ignore
        self.intermediate_action = QAction(qta.icon('fa6s.terminal', color='#61dafb'), "Código intermedio", self, shortcut="F8", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_intermediate_generation)) # type: ignore
        self.execute_action = QAction(qta.icon('fa6s.play', color='#61dafb'), "Ejecutar", self, shortcut="F9", triggered=lambda: self._run_compiler_phase(self.compiler_runner.run_execution)) # type: ignore

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
        """Crea la barra de menú principal."""
        file_menu = self.menuBar().addMenu("&Archivo") # type: ignore
        file_menu.addAction(self.new_action) # type: ignore
        file_menu.addAction(self.open_action) # type: ignore
        file_menu.addAction(self.save_action) # type: ignore
        file_menu.addAction(self.save_as_action) # type: ignore
        file_menu.addAction(self.close_file_action) # type: ignore
        file_menu.addSeparator() # type: ignore
        file_menu.addAction(self.exit_action) # type: ignore

        compile_menu = self.menuBar().addMenu("&Compilar") # type: ignore
        compile_menu.addAction(self.lexical_action) # type: ignore
        compile_menu.addAction(self.syntactic_action) # type: ignore
        compile_menu.addAction(self.semantic_action) # type: ignore
        compile_menu.addAction(self.intermediate_action) # type: ignore
        compile_menu.addSeparator() # type: ignore
        compile_menu.addAction(self.execute_action) # type: ignore
        
        self._create_theme_menu()

    def _create_toolbar(self):
        """Crea la barra de herramientas con estilos modernos."""
        file_toolbar = self.addToolBar("Archivo")
        file_toolbar.setIconSize(QSize(20, 20) )# type: ignore
        file_toolbar.addAction(self.new_action) # type: ignore
        file_toolbar.addAction(self.open_action) # type: ignore
        file_toolbar.addAction(self.save_action) # type: ignore
        file_toolbar.addSeparator() # type: ignore
        compile_toolbar = self.addToolBar("Compilar" )# type: ignore
        compile_toolbar.setIconSize(QSize(20, 20) )# type: ignore
        compile_toolbar.addAction(self.lexical_action) # type: ignore
        compile_toolbar.addAction(self.syntactic_action) # type: ignore
        compile_toolbar.addAction(self.semantic_action) # type: ignore
        compile_toolbar.addAction(self.intermediate_action) # type: ignore
        compile_toolbar.addSeparator()# type: ignore
        compile_toolbar.addAction(self.execute_action) # type: ignore

    def _create_status_bar(self):
        """Crea la barra de estado."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.cursor_position_label = QLabel("Línea: 1, Columna: 1")
        self.status_bar.addPermanentWidget(self.cursor_position_label)
        self.status_bar.showMessage("Listo")

    def _connect_signals(self):
        """Conecta señales de widgets a espacios de la ventana principal."""
        self.file_tree.file_double_clicked.connect(self._open_file_from_path)
        self.editor_widget.cursorPositionChanged.connect(self._update_status_bar)
        # Solo marcar como modificado si no se ignoran cambios de texto
        self.editor_widget.textChanged.connect(self._on_text_changed)
        
        self.compiler_runner.compilation_started.connect(lambda: self.status_bar.showMessage("Compilando..."))
        self.compiler_runner.compilation_finished.connect(self._handle_compilation_finished)
        self.compiler_runner.compilation_error.connect(self._handle_compilation_error)
        self.compiler_runner.ast_ready.connect(self._on_ast_ready)
    
    def _on_text_changed(self):
        """Maneja cambios de texto, respetando la bandera de ignorar."""
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
            self.setWindowTitle("ArcaneIDE - Sin título")

    def _close_file(self):
        if not self._prompt_to_save():
            return

        self.ignore_text_changes = True
        self.editor_widget.clear()
        self.output_tabs.clear_all()
        self.file_manager.new_file()
        self.ignore_text_changes = False
        self.setWindowTitle("ArcaneIDE - Sin título")
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
            self.setWindowTitle(f"ArcaneIDE - {self.file_manager.get_current_file().name}") # type: ignore
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo: {e}")

    def _save_file(self) -> bool:
        if not self.file_manager.get_current_file():
            return self._save_file_as()
        
        content = self.editor_widget.get_text()
        if self.file_manager.save_file(content):
            self.status_bar.showMessage("Archivo guardado.", 3000)
            self.setWindowTitle(f"ArcaneIDE - {self.file_manager.get_current_file().name}") # type: ignore
            return True
        QMessageBox.critical(self, "Error", "No se pudo guardar el archivo.")
        return False

    def _save_file_as(self) -> bool:
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo como", filter="Todos los archivos (*);;Archivos de texto (*.txt)")
        if file_path:
            content = self.editor_widget.get_text()
            if self.file_manager.save_file_as(content, file_path):
                self.file_tree.set_root_path(str(Path(file_path).parent))
                self.setWindowTitle(f"ArcaneIDE - {self.file_manager.get_current_file().name}") # type: ignore
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
        self.output_tabs.update_tokens(results.get("lexico", ""))
        self.output_tabs.update_ast(results.get("sintactico", ""))
        self.output_tabs.update_semantic(results.get("semantico", ""))
        self.output_tabs.update_intermediate_code(results.get("codigo_intermedio", ""))
        self.output_tabs.update_symbol_table(results.get("tabla_simbolos", ""))
        self.output_tabs.update_errors(results.get("errores", "# Sin errores"))
        self.output_tabs.update_execution(results.get("ejecucion", ""))

    def _handle_compilation_error(self, error_msg: str):
        self.status_bar.showMessage("La compilación falló.", 5000)
        self.output_tabs.update_errors(f"ERROR DEL COMPILADOR:\n{error_msg}")
        self.output_tabs.setCurrentWidget(self.output_tabs.tabs["errores"])

    def _on_ast_ready(self, ast_dict: dict) -> None:
        self.ignore_text_changes = True
        self.output_tabs.set_ast(ast_dict)
        self.ignore_text_changes = False

    def _create_theme_menu(self):
        """Crea un menú Vista con opciones de tema y zoom."""
        view_menu = self.menuBar().addMenu("&Vista") # type: ignore
        
        # Submenú de temas
        theme_menu = view_menu.addMenu("&Temas") # type:ignore
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        
        for theme_id, display_name, is_light in self.themes:
            theme_action = QAction(display_name, self, checkable=True)# type: ignore
            if theme_id == self.current_theme:
                theme_action.setChecked(True)
            theme_action.triggered.connect(lambda checked, t=theme_id: self._apply_theme(t))
            theme_group.addAction(theme_action)
            theme_menu.addAction(theme_action) # type: ignore
            
        view_menu.addSeparator() # type:ignore
        view_menu.addAction(self.zoom_in_action) # type:ignore
        view_menu.addAction(self.zoom_out_action) # type:ignore
        view_menu.addAction(self.reset_zoom_action) # type:ignore
    
    def _update_icon_colors(self, is_light: bool):
        """Actualiza colores de iconos según el brillo del tema."""
        icon_color = '#000000' if is_light else 'white'
        icons_config = [
            (self.new_action, 'fa6s.file'),
            (self.open_action, 'fa6s.folder-open'),
            (self.save_action, 'fa6s.floppy-disk'),
            (self.save_as_action, 'fa6s.file-export'),
            (self.close_file_action, 'fa6s.xmark'),
            (self.exit_action, 'fa6s.door-open'),
            (self.zoom_in_action, 'fa6s.magnifying-glass-plus'),
            (self.zoom_out_action, 'fa6s.magnifying-glass-minus'),
            (self.reset_zoom_action, 'fa6s.magnifying-glass'),
        ]
        
        for action, icon_name in icons_config:
            action.setIcon(qta.icon(icon_name, color=icon_color))
        
        # También actualizar iconos del árbol de archivos
        self.file_tree.set_icon_color(icon_color)

    def _apply_theme(self, theme_id: str):
        """Aplica un tema dinámicamente a toda la aplicación y el editor."""
        if not self.app:
            return
        
        self.current_theme = theme_id
        
        # Encontrar si es un tema claro
        is_light = next((t[2] for t in self.themes if t[0] == theme_id), False)
        
        if theme_id == 'tokyo_night':
            theme_path = os.path.join(os.path.dirname(__file__), 'themes', 'tokyo_night.xml')
            apply_stylesheet(self.app, theme=theme_path)
        else:
            apply_stylesheet(self.app, theme=theme_id, invert_secondary=is_light)
        
        # Actualizar colores de iconos según el brillo del tema
        self._update_icon_colors(is_light)
        
        # También actualizar el tema del widget del editor
        self.editor_widget.set_theme(theme_id)

    def closeEvent(self, event):# type: ignore
        if self._prompt_to_save():
            event.accept()
        else:
            event.ignore()
