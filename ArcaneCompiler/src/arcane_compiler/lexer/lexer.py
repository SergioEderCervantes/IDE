from .token import Token
from .token_type import TokenType

RESERVED: dict[str, TokenType] = {
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "end": TokenType.KW_END,
    "do": TokenType.KW_DO,
    "while": TokenType.KW_WHILE,
    "switch": TokenType.KW_SWITCH,
    "case": TokenType.KW_CASE,
    "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT,
    "main": TokenType.KW_MAIN,
    "cin": TokenType.KW_CIN,
    "cout": TokenType.KW_COUT,
    "and": TokenType.OP_AND,
    "or": TokenType.OP_OR,
    "not": TokenType.OP_NOT,
}


class Lexer:
    def __init__(self, source: str) -> None:
        self._source = source
        self._pos = 0
        self._line = 1
        self._col = 1

    def tokenize(self) -> tuple[list[Token], list[Token]]:
        tokens: list[Token] = []
        errors: list[Token] = []
        while self._pos < len(self._source):
            tok = self._next_token()
            if tok is None:
                break
            if tok.type == TokenType.ERROR:
                errors.append(tok)
            else:
                tokens.append(tok)
        return tokens, errors

    def _peek(self, offset: int = 0) -> str | None:
        idx = self._pos + offset
        if idx < len(self._source):
            return self._source[idx]
        return None

    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _next_token(self) -> Token | None:
        if self._pos >= len(self._source):
            return None

        ch = self._peek()

        # 1. Whitespace
        if ch in (" ", "\t", "\r", "\n"):
            self._advance()
            return self._next_token()

        start_line = self._line
        start_col = self._col

        # 2. Block comment
        if ch == "/" and self._peek(1) == "*":
            return self._read_block_comment(start_line, start_col)

        # 3. Line comment
        if ch == "/" and self._peek(1) == "/":
            return self._read_line_comment(start_line, start_col)

        # 4. Numbers
        if ch is not None and ch.isdigit():
            return self._read_number(start_line, start_col)

        # 5. Identifiers and keywords
        if ch is not None and (ch.isalpha() or ch == "_"):
            return self._read_identifier(start_line, start_col)

        # 6. Strings
        if ch == '"':
            return self._read_string(start_line, start_col)

        # 7. Chars
        if ch == "'":
            return self._read_char(start_line, start_col)

        # 8. Operators and symbols (maximal munch)
        ch2 = (self._peek(0) or "") + (self._peek(1) or "")

        two_char_ops = {
            "++": TokenType.OP_INCREMENT,
            "--": TokenType.OP_DECREMENT,
            "<=": TokenType.OP_LE,
            ">=": TokenType.OP_GE,
            "!=": TokenType.OP_NE,
            "==": TokenType.OP_EQ,
            "&&": TokenType.OP_AND,
            "||": TokenType.OP_OR,
            "<<": TokenType.OP_SHIFT_LEFT,
            ">>": TokenType.OP_SHIFT_RIGHT,
        }
        if ch2 in two_char_ops:
            self._advance()
            self._advance()
            return Token(two_char_ops[ch2], ch2, start_line, start_col)

        one_char_ops = {
            "+": TokenType.OP_PLUS,
            "-": TokenType.OP_MINUS,
            "*": TokenType.OP_MULTIPLY,
            "/": TokenType.OP_DIVIDE,
            "%": TokenType.OP_MODULO,
            "^": TokenType.OP_POWER,
            "<": TokenType.OP_LT,
            ">": TokenType.OP_GT,
            "!": TokenType.OP_NOT,
            "=": TokenType.OP_ASSIGN,
            "(": TokenType.SYM_LPAREN,
            ")": TokenType.SYM_RPAREN,
            "{": TokenType.SYM_LBRACE,
            "}": TokenType.SYM_RBRACE,
            ",": TokenType.SYM_COMMA,
            ";": TokenType.SYM_SEMICOLON,
            ":": TokenType.SYM_COLON,
        }
        if ch in one_char_ops:
            self._advance()
            return Token(one_char_ops[ch], ch, start_line, start_col)

        # 9. Invalid character
        self._advance()
        return Token(TokenType.ERROR, f"Carácter inválido: '{ch}'", start_line, start_col)

    def _read_block_comment(self, start_line: int, start_col: int) -> Token:
        buf = ""
        buf += self._advance()  # /
        buf += self._advance()  # *
        while self._pos < len(self._source):
            ch = self._advance()
            buf += ch
            if ch == "*" and self._peek() == "/":
                buf += self._advance()  # /
                return Token(TokenType.COMMENT_BLOCK, buf, start_line, start_col)
        return Token(TokenType.ERROR, "Comentario de bloque no cerrado", start_line, start_col)

    def _read_line_comment(self, start_line: int, start_col: int) -> Token:
        buf = ""
        buf += self._advance()  # /
        buf += self._advance()  # /
        while self._pos < len(self._source) and self._peek() != "\n":
            buf += self._advance()
        return Token(TokenType.COMMENT_LINE, buf, start_line, start_col)

    def _read_number(self, start_line: int, start_col: int) -> Token:
        buf = ""
        while self._pos < len(self._source) and self._peek().isdigit():
            buf += self._advance()
        # Check for real number
        if self._peek() == "." and self._peek(1) is not None and self._peek(1).isdigit():
            buf += self._advance()  # '.'
            while self._pos < len(self._source) and self._peek().isdigit():
                buf += self._advance()
            return Token(TokenType.REAL, buf, start_line, start_col)
        return Token(TokenType.INTEGER, buf, start_line, start_col)

    def _read_identifier(self, start_line: int, start_col: int) -> Token:
        buf = ""
        while self._pos < len(self._source) and (self._peek().isalnum() or self._peek() == "_"):
            buf += self._advance()
        token_type = RESERVED.get(buf, TokenType.IDENTIFIER)
        return Token(token_type, buf, start_line, start_col)

    def _read_string(self, start_line: int, start_col: int) -> Token:
        self._advance()  # "
        buf = ""
        while self._pos < len(self._source):
            ch = self._peek()
            if ch == "\n" or ch is None:
                return Token(TokenType.ERROR, "Cadena de texto no cerrada", start_line, start_col)
            self._advance()
            if ch == '"':
                return Token(TokenType.STRING_LITERAL, buf, start_line, start_col)
            buf += ch
        return Token(TokenType.ERROR, "Cadena de texto no cerrada", start_line, start_col)

    def _read_char(self, start_line: int, start_col: int) -> Token:
        self._advance()  # consume opening '
        buf = ""
        while self._pos < len(self._source):
            ch = self._peek()
            if ch == "\n" or ch is None:
                return Token(TokenType.ERROR, "Carácter literal no cerrado", start_line, start_col)
            self._advance()
            if ch == "'":
                return Token(TokenType.CHAR_LITERAL, buf, start_line, start_col)
            buf += ch
        return Token(TokenType.ERROR, "Carácter literal no cerrado", start_line, start_col)
