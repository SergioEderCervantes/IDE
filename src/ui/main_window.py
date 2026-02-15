from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QSplitter, QStatusBar
)
from PySide6.QtCore import Qt
from src.ui.editor_widget import EditorWidget
from src.ui.file_tree import FileTree
from src.ui.output_tabs import OutputTabs

class MainWindow(QMainWindow):
    """The main window of the IDE, containing all UI components."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compiler IDE")
        self.setGeometry(100, 100, 1200, 800)

        self._setup_ui()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()

    def _setup_ui(self):
        """Sets up the main layout with splitters."""
        # Main vertical splitter for editor and output
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.editor_widget = EditorWidget()
        self.output_tabs = OutputTabs()

        right_splitter.addWidget(self.editor_widget)
        right_splitter.addWidget(self.output_tabs)
        right_splitter.setSizes([600, 200]) # Initial heights

        # Main horizontal splitter for file tree and the rest
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.file_tree = FileTree()
        
        main_splitter.addWidget(self.file_tree)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([200, 1000]) # Initial widths

        self.setCentralWidget(main_splitter)

    def _create_menus(self):
        """Creates the main menu bar (placeholders for now)."""
        # File Menu
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("New")
        file_menu.addAction("Open")
        file_menu.addAction("Save")
        file_menu.addAction("Save As...")
        file_menu.addSeparator()
        file_menu.addAction("Exit")

        # Compile Menu
        compile_menu = self.menuBar().addMenu("&Compile")
        compile_menu.addAction("Lexical Analysis (F5)")
        compile_menu.addAction("Syntactic Analysis (F6)")
        compile_menu.addAction("Semantic Analysis (F7)")
        compile_menu.addAction("Generate Intermediate Code (F8)")
        compile_menu.addAction("Execute (F9)")

    def _create_toolbar(self):
        """Creates the toolbar (placeholders for now)."""
        toolbar = self.addToolBar("Compile")
        toolbar.addAction("Lexical")
        toolbar.addAction("Syntactic")
        toolbar.addAction("Semantic")
        toolbar.addAction("Intermediate")
        toolbar.addAction("Execute")

    def _create_status_bar(self):
        """Creates the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
