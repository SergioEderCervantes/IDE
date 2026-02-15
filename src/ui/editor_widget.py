from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget # Keep this import for parent type hints if needed, but not for inheritance

class EditorWidget(QsciScintilla): # Inherit directly from QsciScintilla
    """
    A custom code editor widget based on QScintilla
    with line numbers and basic styling.
    """
    def __init__(self, parent: QWidget = None): # parent should be QWidget from PyQt6
        super().__init__(parent)
        
        # Basic setup
        self.setUtf8(True)
        font = QFont("Courier New", 10)
        self.setFont(font) # This should now work as QFont is from PyQt6
        
        # Line numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginsForegroundColor(QColor("#888888")) # This should be fine
        
        # Other settings
        self.setIndentationGuides(True)
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)
        
        # For a better look
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#f0f0f0"))

    def get_text(self) -> str:
        """Returns the entire text content of the editor."""
        return self.text()
    
    def set_text(self, text: str):
        """Sets the text content of the editor."""
        self.setText(text)
    
    def get_current_line_number(self) -> int:
        """Returns the current line number (1-indexed)."""
        line, _ = self.getCursorPosition()
        return line + 1
    
    def get_current_column_number(self) -> int:
        """Returns the current column number (1-indexed)."""
        _, col = self.getCursorPosition()
        return col + 1
    
    def clear_editor(self):
        """Clears all text from the editor."""
        self.clear()
