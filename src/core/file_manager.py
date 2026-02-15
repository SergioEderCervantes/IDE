from pathlib import Path
from typing import Optional

class FileManager:
    """Manages file operations like opening, saving, and tracking file state."""

    def __init__(self):
        self.current_file: Optional[Path] = None
        self.is_modified: bool = False

    def new_file(self) -> None:
        """Resets the current file state to represent a new, unsaved file."""
        self.current_file = None
        self.is_modified = False

    def open_file(self, filepath: str) -> str:
        """
        Opens a file, reads its content, and sets it as the current file.

        Args:
            filepath: The path to the file to open.

        Returns:
            The content of the file.
        
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.current_file = path
        self.is_modified = False
        return content

    def save_file(self, content: str) -> bool:
        """
        Saves the content to the current file.
        
        It will fail if no file is currently open (i.e., `current_file` is None).

        Args:
            content: The text content to save.

        Returns:
            True if the file was saved successfully, False otherwise.
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
        Saves the content to a new file location and sets it as the current file.

        Args:
            content: The text content to save.
            filepath: The new path for the file.

        Returns:
            True if the file was saved successfully, False otherwise.
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
        """Returns the Path object of the current file."""
        return self.current_file

    def mark_modified(self, modified: bool = True) -> None:
        """Marks the current file as modified."""
        self.is_modified = modified

