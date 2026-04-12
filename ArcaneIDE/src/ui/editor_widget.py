from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget
from .arcane_lexer import ArcaneLexer

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

        # Instanciar y asignar el lexer de highlighting
        self._arcane_lexer = ArcaneLexer(self)
        self.setLexer(self._arcane_lexer)

        # Aplicar tema oscuro por defecto
        self.set_theme('dark_purple.xml')

    def set_theme(self, theme_id: str):
        """Aplicar colores de tema al editor."""
        themes = {
            'dark_purple.xml': {
                'bg': '#1e1e2e',        'text': '#cdd6f4',
                'margin_bg': '#2d2d44', 'margin_fg': '#888888',
                'caret_bg': '#313244',
                'number': '#f9e2af',    'identifier': '#cdd6f4',
                'comment': '#585b70',   'keyword': '#cba6f7',
                'op_arith': '#89dceb',  'op_rellog': '#89b4fa',
                'op_assign': '#89b4fa', 'symbol': '#bac2de',
                'string': '#a6e3a1',    'error': '#f38ba8',
            },
            'dark_blue.xml': {
                'bg': '#0d1117',        'text': '#c9d1d9',
                'margin_bg': '#161b22', 'margin_fg': '#6e7681',
                'caret_bg': '#21262d',
                'number': '#79c0ff',    'identifier': '#c9d1d9',
                'comment': '#8b949e',   'keyword': '#ff7b72',
                'op_arith': '#ffa657',  'op_rellog': '#79c0ff',
                'op_assign': '#ff7b72', 'symbol': '#c9d1d9',
                'string': '#a5d6ff',    'error': '#ff7b72',
            },
            'tokyo_night': {
                'bg': '#1a1b26',        'text': '#c0caf5',
                'margin_bg': '#1f202e', 'margin_fg': '#565f89',
                'caret_bg': '#2a2b35',
                'number': '#ff9e64',    'identifier': '#c0caf5',
                'comment': '#565f89',   'keyword': '#bb9af7',
                'op_arith': '#7dcfff',  'op_rellog': '#2ac3de',
                'op_assign': '#89ddff', 'symbol': '#89ddff',
                'string': '#9ece6a',    'error': '#f7768e',
            },
            'light_blue.xml': {
                'bg': '#ffffff',        'text': '#1f1f1f',
                'margin_bg': '#f3f3f3', 'margin_fg': '#666666',
                'caret_bg': '#eeeeee',
                'number': '#098658',    'identifier': '#1f1f1f',
                'comment': '#008000',   'keyword': '#0000ff',
                'op_arith': '#000000',  'op_rellog': '#0000ff',
                'op_assign': '#000000', 'symbol': '#333333',
                'string': '#a31515',    'error': '#ff0000',
            },
            'light_cyan.xml': {
                'bg': '#fafafa',        'text': '#2c2c2c',
                'margin_bg': '#e8f4f8', 'margin_fg': '#666666',
                'caret_bg': '#ddeeff',
                'number': '#0e6251',    'identifier': '#2c2c2c',
                'comment': '#006400',   'keyword': '#00008b',
                'op_arith': '#8b0000',  'op_rellog': '#00008b',
                'op_assign': '#8b0000', 'symbol': '#555555',
                'string': '#8b0000',    'error': '#ff0000',
            },
        }

        colors = themes.get(theme_id, themes['dark_purple.xml'])

        # Colores de tokens → lexer
        self._arcane_lexer.apply_theme(colors)

        # Fondo del viewport (área vacía más allá del texto)
        self.setPaper(QColor(colors['bg']))

        # Colores de UI del editor
        self.setMarginsBackgroundColor(QColor(colors['margin_bg']))
        self.setMarginsForegroundColor(QColor(colors['margin_fg']))
        self.setCaretLineBackgroundColor(QColor(colors['caret_bg']))
        self.setCaretForegroundColor(QColor('#ffffff'))
        

        # Forzar re-coloreo completo del documento
        self.recolor()

    def get_text(self) -> str:
        """Retorna todo el contenido de texto del editor."""
        return self.text()

    def set_text(self, text: str):
        """Establece el contenido de texto del editor."""
        self.setText(text)
        self.recolor()


    # TODO: Una sola funcion que retorne las dos cosas
    def get_current_line_number(self) -> int:
        """Retorna el número de línea actual (base 1)."""
        line, _ = self.getCursorPosition()
        return line + 1

    def get_current_column_number(self) -> int:
        """Retorna el número de columna actual (base 1)."""
        _, col = self.getCursorPosition()
        return col + 1
