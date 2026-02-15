from PySide6.QtWidgets import QTreeView, QWidget, QVBoxLayout, QFileSystemModel
from PySide6.QtCore import QDir, Signal

class FileTree(QWidget):
    """
    A widget that displays a file system tree view.
    Emits a signal when a file is double-clicked.
    """
    file_double_clicked = Signal(str)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.currentPath())
        
        # Filters: show only common source code files
        self.model.setNameFilters(["*.txt", "*.c", "*.cpp", "*.py", "*.java", "*.md"])
        self.model.setNameFilterDisables(False) # Show only filtered files
        
        # Tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.currentPath()))
        
        # Visual settings
        self.tree.setColumnWidth(0, 250)
        self.tree.setHeaderHidden(True)
        self.tree.hideColumn(1)
        self.tree.hideColumn(2)
        self.tree.hideColumn(3)
        
        # Connect double-click signal
        self.tree.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.tree)
    
    def _on_double_click(self, index):
        """Handle double-click on a file."""
        file_path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_double_clicked.emit(file_path)
    
    def set_root_path(self, path: str):
        """Changes the root directory displayed in the tree."""
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
