from typing import Optional
from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QFont, QColor, QImage, QPainter
from PyQt6.QtWidgets import QToolTip, QWidget
from .arcane_lexer import ArcaneLexer
from .paleta import paleta

# Marcas de errores de compilación en el editor
_INDICADOR_ERROR = 8   # los indicadores 0-7 los reserva Scintilla para los lexers
_MARCADOR_ERROR = 1
_MARGEN_ERRORES = 0    # a la izquierda de los números de línea
_MARGEN_NUMEROS = 1
_CARACTERES_PALABRA = "_."               # además de letras y dígitos: x, suma, 32.32
_CARACTERES_OPERADOR = "+-*/%^<>=!&|"    # ==, <=, &&, >> se subrayan completos

# Llave del JSON de ERRORES → nombre de la fase en el mensaje
_FASES = {"lexico": "léxico", "sintactico": "sintáctico", "semantico": "semántico"}


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

        # Márgenes: marcas de error y números de línea
        self.setMarginType(_MARGEN_ERRORES, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(_MARGEN_ERRORES, 14)
        self.setMarginMarkerMask(_MARGEN_ERRORES, 1 << _MARCADOR_ERROR)
        self.setMarginType(_MARGEN_NUMEROS, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(_MARGEN_NUMEROS, "0000")
        self.setMarginMarkerMask(_MARGEN_NUMEROS, 0)

        # Errores de compilación: subrayado ondulado, punto en el margen y mensaje al
        # dejar el mouse sobre el subrayado
        self.indicatorDefine(QsciScintilla.IndicatorStyle.SquigglePixmapIndicator, _INDICADOR_ERROR)
        self._mensajes_error: list[str] = []
        self.SendScintilla(QsciScintilla.SCI_SETMARGINLEFT, 0, 6)  # aire entre los números y el código
        self.SendScintilla(QsciScintilla.SCI_SETMOUSEDWELLTIME, 400)
        self.SCN_DWELLSTART.connect(self._mostrar_mensaje_error)
        self.SCN_DWELLEND.connect(lambda *_: QToolTip.hideText())

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

        # Marcas de error con el rojo de la paleta (clara u oscura según el tema)
        rojo = QColor(paleta(tema_claro=theme_id.startswith('light'))["error"])
        self.setIndicatorForegroundColor(rojo, _INDICADOR_ERROR)
        self.markerDefine(_punto(rojo), _MARCADOR_ERROR)


        # Forzar re-coloreo completo del documento
        self.recolor()

    def get_text(self) -> str:
        """Retorna todo el contenido de texto del editor."""
        return self.text()

    def set_text(self, text: str):
        """Establece el contenido de texto del editor."""
        self.setText(text)
        self.recolor()


    # ─── Marcas de errores de compilación ────────────────────────────────────

    def marcar_errores(self, errores: Optional[dict]) -> None:
        """Marca en el código los errores de la sección ERRORES (las tres fases).

        Cada error con posición subraya la palabra (o el operador) donde empieza y pone
        un punto en el margen de su línea. Un error sin posición (fin de archivo) solo
        marca el margen de la última línea.
        """
        self.limpiar_errores()
        for clave, fase in _FASES.items():
            for error in (errores or {}).get(clave) or []:
                self._marcar_error(fase, error.get("linea"), error.get("columna"), error.get("mensaje", ""))

    def limpiar_errores(self) -> None:
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, _INDICADOR_ERROR)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, self.length())
        self.markerDeleteAll(_MARCADOR_ERROR)
        self._mensajes_error = []

    def _marcar_error(self, fase: str, linea: Optional[int], columna: Optional[int], mensaje: str) -> None:
        if self.lines() == 0:
            return
        ultima = self.lines() - 1
        fila = ultima if linea is None else min(max(linea - 1, 0), ultima)
        self.markerAdd(fila, _MARCADOR_ERROR)
        if linea is None:
            return

        texto = self.text(fila).rstrip("\r\n")
        inicio = min(max((columna or 1) - 1, 0), max(len(texto) - 1, 0))
        fin = _fin_del_token(texto, inicio)
        if fin <= inicio:
            return

        # Cada error es un valor distinto del indicador: así el mensaje se recupera al pasar
        # el mouse aunque el texto se haya movido al editar
        self._mensajes_error.append(f"Error {fase}: {mensaje}")
        desde = self.positionFromLineIndex(fila, inicio)
        hasta = self.positionFromLineIndex(fila, fin)
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, _INDICADOR_ERROR)
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORVALUE, len(self._mensajes_error))
        self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, desde, hasta - desde)

    def _mostrar_mensaje_error(self, posicion: int, x: int, y: int) -> None:
        if posicion < 0:
            return
        valor = self.SendScintilla(QsciScintilla.SCI_INDICATORVALUEAT, _INDICADOR_ERROR, posicion)
        if 0 < valor <= len(self._mensajes_error):
            QToolTip.showText(self.viewport().mapToGlobal(QPoint(x, y)),  # type: ignore
                              self._mensajes_error[valor - 1], self.viewport())

    # TODO: Una sola funcion que retorne las dos cosas
    def get_current_line_number(self) -> int:
        """Retorna el número de línea actual (base 1)."""
        line, _ = self.getCursorPosition()
        return line + 1

    def get_current_column_number(self) -> int:
        """Retorna el número de columna actual (base 1)."""
        _, col = self.getCursorPosition()
        return col + 1


def _punto(color: QColor) -> QImage:
    """Marcador del margen: un punto pequeño y suave (el círculo estándar de Scintilla
    ocupa toda la altura de la línea)."""
    imagen = QImage(14, 14, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(color)
    pintor.drawEllipse(QRectF(3, 3, 8, 8))
    pintor.end()
    return imagen


def _fin_del_token(texto: str, inicio: int) -> int:
    """Índice donde termina el token que empieza en `inicio`: una palabra (suma, 32.32),
    un operador de uno o más caracteres (==, &&) o, si no, un solo carácter."""
    if inicio >= len(texto):
        return inicio
    for es_parte in (lambda c: c.isalnum() or c in _CARACTERES_PALABRA,
                     lambda c: c in _CARACTERES_OPERADOR):
        fin = inicio
        while fin < len(texto) and es_parte(texto[fin]):
            fin += 1
        if fin > inicio:
            return fin
    return inicio + 1
