from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget

class EditorWidget(QsciScintilla):
    """
    A custom code editor widget based on QScintilla
    with line numbers, basic styling and dynamic theming.
    """
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        # Basic setup
        self.setUtf8(True)
        font = QFont("Courier New", 10)
        self.setFont(font)
        
        # Line numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        
        # Other settings
        self.setIndentationGuides(True)
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)
        
        # For a better look
        self.setCaretLineVisible(True)
        
        # Apply default dark theme
        self.set_theme('dark_purple.xml')

    def set_theme(self, theme_id: str):
        """Apply theme colors to the editor."""
        # Define theme color schemes: (bg, text, margin_bg, margin_fg, caret_bg)
        themes = {
            'dark_purple.xml': {
                'bg': '#1e1e2e',
                'text': '#e0e0e0',
                'margin_bg': '#2d2d44',
                'margin_fg': '#888888',
                'caret_bg': '#404050',
            },
            'dark_blue.xml': {
                'bg': '#0d1117',
                'text': '#c9d1d9',
                'margin_bg': '#161b22',
                'margin_fg': '#6e7681',
                'caret_bg': '#21262d',
            },
            'tokyo_night': {
                'bg': '#1a1b26',
                'text': '#c0caf5',
                'margin_bg': '#1f202e',
                'margin_fg': '#565f89',
                'caret_bg': '#2a2b35',
            },
            'light_blue.xml': {
                'bg': '#ffffff',
                'text': '#000000',
                'margin_bg': '#f3f3f3',
                'margin_fg': '#666666',
                'caret_bg': '#eeeeee',
            },
            'light_cyan.xml': {
                'bg': '#ffffff',
                'text': '#000000',
                'margin_bg': '#f3f3f3',
                'margin_fg': '#666666',
                'caret_bg': '#eeeeee',
            },
        }
        
        colors = themes.get(theme_id, themes['dark_purple.xml'])
        
        # Apply colors
        self.setMarginsBackgroundColor(QColor(colors['margin_bg']))
        self.setMarginsForegroundColor(QColor(colors['margin_fg']))
        self.setPaper(QColor(colors['bg']))
        self.setColor(QColor(colors['text']))
        self.setCaretLineBackgroundColor(QColor(colors['caret_bg']))

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
