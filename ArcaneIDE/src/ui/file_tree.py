from PyQt6.QtWidgets import QTreeView, QWidget, QVBoxLayout, QFileIconProvider
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QDir, pyqtSignal, QStandardPaths, Qt
import qtawesome as qta
from pathlib import Path


class CustomFileIconProvider(QFileIconProvider):
    """Proveedor de iconos personalizado que usa iconos de QtAwesome"""
    
    def __init__(self):
        super().__init__()
        self.icon_color = 'white'
        self._icon_cache = {}  # Caché: (tipo_archivo, color) -> QIcon
    
    def icon(self, file_info): # type: ignore
        """Devuelve iconos personalizados de QtAwesome basados en el tipo de archivo."""
        is_dir = file_info.isDir()
        icon_key = ('folder' if is_dir else 'file', self.icon_color)
        
        # Devuelve icono en caché si está disponible
        if icon_key in self._icon_cache:
            return self._icon_cache[icon_key]
        
        # Genera y cachea nuevo icono
        icon_name = 'fa6s.folder' if is_dir else 'fa6s.file'
        new_icon = qta.icon(icon_name, color=self.icon_color)
        self._icon_cache[icon_key] = new_icon
        return new_icon
    
    def set_icon_color(self, color: str):
        """Actualiza el color del icono e invalida el caché del color anterior."""
        if self.icon_color != color:
            self.icon_color = color
            self._icon_cache.clear()


class FileTree(QWidget):
    """
    Widget que muestra una vista de árbol del sistema de archivos.
    Emite una señal cuando se hace doble clic en un archivo.
    """
    file_double_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        
        # Diseño
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Modelo del sistema de archivos
        self.model = QFileSystemModel()
        self.icon_provider = CustomFileIconProvider()
        self.model.setIconProvider(self.icon_provider)
        _samples = Path(__file__).parents[3] / "ArcaneCompiler" / "tests" / "samples"
        if _samples.exists():
            initial_root = str(_samples)
        else:
            _desktop = Path(QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DesktopLocation))
            initial_root = str(_desktop) if _desktop.exists() else QDir.homePath()
        self.model.setRootPath(initial_root)
        
        # Filtros
        # self.model.setNameFilters(["*.txt", "*.c", "*.cpp", "*.java"])
        # self.model.setNameFilterDisables(False) # Mostrar solo archivos filtrados
        
        # Vista de árbol
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(initial_root)))
        
        # Configuración visual
        self.tree.setColumnWidth(0, 250)
        self.tree.setHeaderHidden(True)
        self.tree.hideColumn(1)
        self.tree.hideColumn(2)
        self.tree.hideColumn(3)
        
        # Conectar señal de doble clic
        self.tree.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.tree)
    
    def _on_double_click(self, index):
        """Maneja el doble clic en un archivo."""
        file_path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_double_clicked.emit(file_path)
    
    def set_root_path(self, path: str):
        """Cambia el directorio raíz mostrado en el árbol."""
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
    
    def set_icon_color(self, color: str):
        """Actualiza el color del icono para cambio de tema"""
        # Solo actualizar si el color cambió realmente
        if self.icon_provider.icon_color != color:
            # Crear un proveedor de icono nuevo con el color actualizado
            self.icon_provider = CustomFileIconProvider()
            self.icon_provider.set_icon_color(color)
            # Reasignar para forzar a Qt a invalidar su caché
            self.model.setIconProvider(self.icon_provider)
            # Activar un redibujado
            self.tree.viewport().repaint() # type: ignore
