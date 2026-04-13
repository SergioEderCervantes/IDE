from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtGui import QColor
from arcane_compiler.lexer.lexer import Lexer
from arcane_compiler.lexer.token_type import TokenType


def _build_line_offsets(text: str) -> list[int]:
    """Retorna una lista donde el índice i contiene el offset de byte
    donde empieza la línea i+1 en el texto."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == '\n':
            offsets.append(i + 1)
    return offsets


def _token_byte_length(token, full_text: str, line_offsets: list[int]) -> int:
    """Calcula cuántos bytes ocupa el token en el source original.
    Para STRING_LITERAL y CHAR_LITERAL agrega 2 (las comillas).
    Para COMMENT_BLOCK el value ya incluye /* y */ así que usar len directo.
    Para ERROR el value es un mensaje, no el texto fuente: se determina la
    longitud real según el tipo de error.
    Para el resto usar len(token.value).
    """
    if token.type == TokenType.ERROR:
        if token.value.startswith("Carácter inválido:"):
            return 1  
        if token.value.startswith("Número inválido:"):
            inner = token.value.split("'")[1]
            return len(inner.encode("utf-8"))
        # Tokens no cerrados (string, char, block comment): colorear hasta el final
        token_start = line_offsets[token.line - 1] + (token.column - 1)
        return len(full_text.encode("utf-8")) - token_start
    if token.type in (TokenType.STRING_LITERAL, TokenType.CHAR_LITERAL):
        return len(token.value) + 2  # +2 por las comillas delimitadoras
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
        TokenType.KW_WHILE:       STYLE_KEYWORD,
        TokenType.KW_SWITCH:      STYLE_KEYWORD,
        TokenType.KW_CASE:        STYLE_KEYWORD,
        TokenType.KW_INT:         STYLE_KEYWORD,
        TokenType.KW_FLOAT:       STYLE_KEYWORD,
        TokenType.KW_MAIN:        STYLE_KEYWORD,
        TokenType.KW_CIN:         STYLE_KEYWORD,
        TokenType.KW_COUT:        STYLE_KEYWORD,
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

        full_text = editor.text()

        self.startStyling(0)

        if not full_text.strip():
            self.setStyling(len(full_text.encode("utf-8")), self.STYLE_DEFAULT)
            return

        lexer = Lexer(full_text)
        tokens, errors = lexer.tokenize()

        all_tokens = sorted(tokens + errors, key=lambda t: (t.line, t.column))

        line_offsets = _build_line_offsets(full_text)

        total_bytes = len(full_text.encode("utf-8"))
        current_byte_pos = 0
        for token in all_tokens:
            token_start = line_offsets[token.line - 1] + (token.column - 1)

            # Skip tokens already covered by a previous spanning token
            # (e.g. an unclosed-string ERROR that consumed to end-of-document)
            if token_start < current_byte_pos:
                continue

            token_byte_len = _token_byte_length(token, full_text, line_offsets)
            # Clamp so we never exceed document length
            token_byte_len = min(token_byte_len, total_bytes - token_start)

            if token_start > current_byte_pos:
                gap = token_start - current_byte_pos
                self.setStyling(gap, self.STYLE_DEFAULT)

            style = self.TOKEN_TYPE_TO_STYLE.get(token.type, self.STYLE_DEFAULT)
            self.setStyling(token_byte_len, style)
            current_byte_pos = token_start + token_byte_len

            if current_byte_pos >= total_bytes:
                break

        remaining = total_bytes - current_byte_pos
        if remaining > 0:
            self.setStyling(remaining, self.STYLE_DEFAULT)

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
