from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtGui import QColor
from arcane_compiler.lexer.lexer import Lexer
from arcane_compiler.lexer.token_type import TokenType


# El Lexer da línea y columna en caracteres; QScintilla mide posiciones en bytes UTF-8.
# Todo se calcula en caracteres y se convierte a bytes al final (con acentos o ñ cada
# letra ocupa 2 bytes y, sin la conversión, los colores se recorrían).

def _inicios_de_linea(texto: str) -> list[int]:
    """Carácter donde empieza cada línea: el índice i corresponde a la línea i + 1."""
    inicios = [0]
    for i, ch in enumerate(texto):
        if ch == "\n":
            inicios.append(i + 1)
    return inicios


def _bytes_hasta(texto: str) -> list[int]:
    """bytes_hasta[i] = bytes UTF-8 que ocupan los primeros i caracteres del texto."""
    acumulado = [0]
    total = 0
    for ch in texto:
        codigo = ord(ch)
        total += 1 if codigo < 0x80 else 2 if codigo < 0x800 else 3 if codigo < 0x10000 else 4
        acumulado.append(total)
    return acumulado


def _longitud(token, texto: str, inicio: int) -> int:
    """Caracteres que ocupa el token en el texto, a partir de su posición `inicio`.
    En un ERROR el value es el mensaje, no el texto fuente."""
    if token.type == TokenType.ERROR:
        if token.value.startswith("Carácter inválido:"):
            return 1
        if token.value.startswith("Comentario de bloque no cerrado"):
            return len(texto) - inicio  # llega al final del archivo
        # Cadena o carácter sin cerrar: el Lexer se detiene al final de la línea
        fin_de_linea = texto.find("\n", inicio)
        return (len(texto) if fin_de_linea == -1 else fin_de_linea) - inicio
    if token.type in (TokenType.STRING_LITERAL, TokenType.CHAR_LITERAL):
        return len(token.value) + 2  # las comillas
    return len(token.value)


class ArcaneLexer(QsciLexerCustom):
    STYLE_DEFAULT    = 0
    STYLE_NUMBER     = 1
    STYLE_IDENTIFIER = 2
    STYLE_COMMENT    = 3
    STYLE_KEYWORD    = 4
    STYLE_OP_ARITH   = 5
    STYLE_OP_RELLOG  = 6
    STYLE_OP_ASSIGN  = 7
    STYLE_SYMBOL     = 8
    STYLE_STRING     = 9
    STYLE_ERROR      = 10

    TOKEN_TYPE_TO_STYLE: dict = {
        TokenType.INTEGER:        STYLE_NUMBER,
        TokenType.REAL:           STYLE_NUMBER,
        TokenType.IDENTIFIER:     STYLE_IDENTIFIER,
        TokenType.COMMENT_LINE:   STYLE_COMMENT,
        TokenType.COMMENT_BLOCK:  STYLE_COMMENT,
        TokenType.KW_IF:          STYLE_KEYWORD,
        TokenType.KW_ELSE:        STYLE_KEYWORD,
        TokenType.KW_END:         STYLE_KEYWORD,
        TokenType.KW_DO:          STYLE_KEYWORD,
        TokenType.KW_UNTIL:       STYLE_KEYWORD,
        TokenType.KW_WHILE:       STYLE_KEYWORD,
        TokenType.KW_SWITCH:      STYLE_KEYWORD,
        TokenType.KW_CASE:        STYLE_KEYWORD,
        TokenType.KW_INT:         STYLE_KEYWORD,
        TokenType.KW_FLOAT:       STYLE_KEYWORD,
        TokenType.KW_MAIN:        STYLE_KEYWORD,
        TokenType.KW_CIN:         STYLE_KEYWORD,
        TokenType.KW_COUT:        STYLE_KEYWORD,
        TokenType.KW_THEN:        STYLE_KEYWORD,
        TokenType.KW_BOOL:        STYLE_KEYWORD,
        TokenType.KW_TRUE:        STYLE_KEYWORD,
        TokenType.KW_FALSE:       STYLE_KEYWORD,
        TokenType.OP_PLUS:        STYLE_OP_ARITH,
        TokenType.OP_MINUS:       STYLE_OP_ARITH,
        TokenType.OP_MULTIPLY:    STYLE_OP_ARITH,
        TokenType.OP_DIVIDE:      STYLE_OP_ARITH,
        TokenType.OP_MODULO:      STYLE_OP_ARITH,
        TokenType.OP_POWER:       STYLE_OP_ARITH,
        TokenType.OP_INCREMENT:   STYLE_OP_ARITH,
        TokenType.OP_DECREMENT:   STYLE_OP_ARITH,
        TokenType.OP_LT:          STYLE_OP_RELLOG,
        TokenType.OP_LE:          STYLE_OP_RELLOG,
        TokenType.OP_GT:          STYLE_OP_RELLOG,
        TokenType.OP_GE:          STYLE_OP_RELLOG,
        TokenType.OP_NE:          STYLE_OP_RELLOG,
        TokenType.OP_EQ:          STYLE_OP_RELLOG,
        TokenType.OP_AND:         STYLE_OP_RELLOG,
        TokenType.OP_OR:          STYLE_OP_RELLOG,
        TokenType.OP_NOT:         STYLE_OP_RELLOG,
        TokenType.OP_SHIFT_LEFT:  STYLE_OP_RELLOG,
        TokenType.OP_SHIFT_RIGHT: STYLE_OP_RELLOG,
        TokenType.OP_ASSIGN:      STYLE_OP_ASSIGN,
        TokenType.SYM_LPAREN:     STYLE_SYMBOL,
        TokenType.SYM_RPAREN:     STYLE_SYMBOL,
        TokenType.SYM_LBRACE:     STYLE_SYMBOL,
        TokenType.SYM_RBRACE:     STYLE_SYMBOL,
        TokenType.SYM_COMMA:      STYLE_SYMBOL,
        TokenType.SYM_SEMICOLON:  STYLE_SYMBOL,
        TokenType.SYM_COLON:      STYLE_SYMBOL,
        TokenType.STRING_LITERAL: STYLE_STRING,
        TokenType.CHAR_LITERAL:   STYLE_STRING,
        TokenType.ERROR:          STYLE_ERROR,
    }

    _STYLE_NAMES = {
        0:  "Default",
        1:  "Número",
        2:  "Identificador",
        3:  "Comentario",
        4:  "Palabra reservada",
        5:  "Operador aritmético",
        6:  "Operador relacional/lógico",
        7:  "Asignación",
        8:  "Símbolo",
        9:  "Cadena/Carácter",
        10: "Error léxico",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_colors: dict = {}

    def language(self) -> str:
        return "Arcane"

    def description(self, style: int) -> str:
        return self._STYLE_NAMES.get(style, "")

    def styleText(self, start: int, end: int) -> None:
        editor = self.editor()
        if editor is None:
            return

        texto = editor.text()
        en_bytes = _bytes_hasta(texto)
        total = en_bytes[-1]

        self.startStyling(0)

        if not texto.strip():
            self.setStyling(total, self.STYLE_DEFAULT)
            return

        tokens, errores = Lexer(texto).tokenize()
        inicios = _inicios_de_linea(texto)

        actual = 0  # carácter hasta donde ya se aplicó estilo
        for token in sorted(tokens + errores, key=lambda t: (t.line, t.column)):
            inicio = inicios[token.line - 1] + token.column - 1
            if inicio < actual:  # ya cubierto (p. ej. por un comentario sin cerrar)
                continue
            fin = min(inicio + _longitud(token, texto, inicio), len(texto))
            if inicio > actual:
                self.setStyling(en_bytes[inicio] - en_bytes[actual], self.STYLE_DEFAULT)
            estilo = self.TOKEN_TYPE_TO_STYLE.get(token.type, self.STYLE_DEFAULT)
            self.setStyling(en_bytes[fin] - en_bytes[inicio], estilo)
            actual = fin
            if actual >= len(texto):
                break

        if total > en_bytes[actual]:
            self.setStyling(total - en_bytes[actual], self.STYLE_DEFAULT)

    def apply_theme(self, theme_colors: dict) -> None:
        self._theme_colors = theme_colors
        bg = theme_colors.get('bg', '#1e1e2e')
        text_color = theme_colors.get('text', '#e0e0e0')

        # Fondo/color por defecto para áreas que QScintilla no estiló explícitamente
        self.setDefaultPaper(QColor(bg))
        self.setDefaultColor(QColor(text_color))

        font = self.font(self.STYLE_DEFAULT)

        style_color_map = {
            self.STYLE_DEFAULT:    theme_colors.get('text', '#e0e0e0'),
            self.STYLE_NUMBER:     theme_colors.get('number', '#f9e2af'),
            self.STYLE_IDENTIFIER: theme_colors.get('identifier', '#cdd6f4'),
            self.STYLE_COMMENT:    theme_colors.get('comment', '#6c7086'),
            self.STYLE_KEYWORD:    theme_colors.get('keyword', '#cba6f7'),
            self.STYLE_OP_ARITH:   theme_colors.get('op_arith', '#89dceb'),
            self.STYLE_OP_RELLOG:  theme_colors.get('op_rellog', '#89b4fa'),
            self.STYLE_OP_ASSIGN:  theme_colors.get('op_assign', '#89b4fa'),
            self.STYLE_SYMBOL:     theme_colors.get('symbol', '#bac2de'),
            self.STYLE_STRING:     theme_colors.get('string', '#a6e3a1'),
            self.STYLE_ERROR:      theme_colors.get('error', '#f38ba8'),
        }

        for style_id, hex_color in style_color_map.items():
            self.setColor(QColor(hex_color), style_id)
            self.setPaper(QColor(theme_colors.get('bg', '#1e1e2e')), style_id)
            self.setFont(font, style_id)
