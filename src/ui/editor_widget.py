from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget

class EditorWidget(QsciScintilla):
    """
    Un widget de editor de código personalizado basado en QScintilla.
    """
    def __init__(self, parent: QWidget = None): # type: ignore
        super().__init__(parent)
        
        # Configuración básica
        # TODO: que se pueda cambiar el tama;o de fuente
        self.setUtf8(True)
        font = QFont("Courier New", 14)
        self.setFont(font)
        
        # Números de línea
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        
        # Otras configuraciones
        self.setIndentationGuides(True)
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)
        self.setCaretLineVisible(True)
        
        # Aplicar tema oscuro por defecto
        self.set_theme('dark_purple.xml')

    def set_theme(self, theme_id: str):
        """Aplicar colores de tema al editor."""
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
        
        self.setMarginsBackgroundColor(QColor(colors['margin_bg']))
        self.setMarginsForegroundColor(QColor(colors['margin_fg']))
        self.setPaper(QColor(colors['bg']))
        self.setColor(QColor(colors['text']))
        self.setCaretLineBackgroundColor(QColor(colors['caret_bg']))

    def get_text(self) -> str:
        """Retorna todo el contenido de texto del editor."""
        return self.text()
    
    def set_text(self, text: str):
        """Establece el contenido de texto del editor."""
        self.setText(text)
    

    # TODO: Una sola funcion que retorne las dos cosas
    def get_current_line_number(self) -> int:
        """Retorna el número de línea actual (base 1)."""
        line, _ = self.getCursorPosition()
        return line + 1
    
    def get_current_column_number(self) -> int:
        """Retorna el número de columna actual (base 1)."""
        _, col = self.getCursorPosition()
        return col + 1
