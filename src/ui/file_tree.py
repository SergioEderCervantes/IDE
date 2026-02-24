from PyQt6.QtWidgets import QTreeView, QWidget, QVBoxLayout, QFileIconProvider
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QDir, pyqtSignal, QStandardPaths, Qt
import qtawesome as qta


class CustomFileIconProvider(QFileIconProvider):
    """Custom icon provider that uses QtAwesome icons for folders and files with caching."""
    
    def __init__(self):
        super().__init__()
        self.icon_color = 'white'
        self._icon_cache = {}  # Cache: (file_type, color) -> QIcon
    
    def icon(self, file_info):
        """Return custom QtAwesome icons based on file type (cached)."""
        is_dir = file_info.isDir()
        icon_key = ('folder' if is_dir else 'file', self.icon_color)
        
        # Return cached icon if available
        if icon_key in self._icon_cache:
            return self._icon_cache[icon_key]
        
        # Generate and cache new icon
        icon_name = 'fa6s.folder' if is_dir else 'fa6s.file'
        new_icon = qta.icon(icon_name, color=self.icon_color)
        self._icon_cache[icon_key] = new_icon
        return new_icon
    
    def set_icon_color(self, color: str):
        """Update the icon color and invalidate cache for old color."""
        if self.icon_color != color:
            self.icon_color = color
            # Clear cache for old color - new color icons will be cached on demand
            self._icon_cache.clear()


class FileTree(QWidget):
    """
    A widget that displays a file system tree view.
    Emits a signal when a file is double-clicked.
    """
    file_double_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # File system model
        self.model = QFileSystemModel()
        self.icon_provider = CustomFileIconProvider()
        self.model.setIconProvider(self.icon_provider)
        initial_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if not initial_root:
            initial_root = QDir.homePath()
        self.model.setRootPath(initial_root)
        
        # Filters: show only source-like files for compiler inputs
        self.model.setNameFilters(["*.txt", "*.c", "*.cpp", "*.java"])
        self.model.setNameFilterDisables(False) # Show only filtered files
        
        # Tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(initial_root))
        
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
    
    def set_icon_color(self, color: str):
        """Updates the icon color for theme switching"""
        # Only update if color actually changed
        if self.icon_provider.icon_color != color:
            # Create a fresh icon provider with the new color
            self.icon_provider = CustomFileIconProvider()
            self.icon_provider.set_icon_color(color)
            # Reassign to force Qt to invalidate its cache
            self.model.setIconProvider(self.icon_provider)
            # Trigger a redraw
            self.tree.viewport().repaint()
