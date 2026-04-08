from pathlib import Path
from typing import Optional

class FileManager:
    """Gestiona operaciones de archivo como abrir, guardar y rastrear el estado del archivo."""

    def __init__(self):
        self.current_file: Optional[Path] = None
        self.is_modified: bool = False

    def new_file(self) -> None:
        """Reinicia el estado del archivo actual para representar un archivo nuevo sin guardar."""
        self.current_file = None
        self.is_modified = False

    def open_file(self, filepath: str) -> str:
        """
        Abre un archivo, lee su contenido y lo establece como archivo actual.

        Args:
            filepath: La ruta del archivo a abrir.

        Returns:
            El contenido del archivo.
        
        Raises:
            FileNotFoundError: Si el archivo no existe.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.current_file = path
        self.is_modified = False
        return content

    def save_file(self, content: str) -> bool:
        """
        Guarda el contenido en el archivo actual.
        
        Fallará si no hay un archivo abierto (es decir, `current_file` es None).

        Args:
            content: El contenido de texto a guardar.

        Returns:
            True si el archivo se guardó exitosamente, False en caso contrario.
        """
        if not self.current_file:
            return False

        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.is_modified = False
            return True
        except IOError:
            return False

    def save_file_as(self, content: str, filepath: str) -> bool:
        """
        Guarda el contenido en una nueva ubicación de archivo y lo establece como archivo actual.

        Args:
            content: El contenido de texto a guardar.
            filepath: La nueva ruta del archivo.

        Returns:
            True si el archivo se guardó exitosamente, False en caso contrario.
        """
        try:
            path = Path(filepath)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.current_file = path
            self.is_modified = False
            return True
        except IOError:
            return False

    def get_current_file(self) -> Optional[Path]:
        """Devuelve el objeto Path del archivo actual."""
        return self.current_file

    def mark_modified(self, modified: bool = True) -> None:
        """Marca el archivo actual como modificado."""
        self.is_modified = modified
