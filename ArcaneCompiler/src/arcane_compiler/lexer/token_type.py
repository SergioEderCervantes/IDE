from enum import Enum, auto


class TokenType(Enum):
    # Literales numéricos
    INTEGER = auto()
    REAL = auto()

    # Identificadores
    IDENTIFIER = auto()

    # Palabras reservadas
    KW_IF = auto()
    KW_ELSE = auto()
    KW_END = auto()
    KW_DO = auto()
    KW_WHILE = auto()
    KW_SWITCH = auto()
    KW_CASE = auto()
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_MAIN = auto()
    KW_CIN = auto()
    KW_COUT = auto()

    # Comentarios
    COMMENT_LINE = auto()
    COMMENT_BLOCK = auto()

    # Operadores aritméticos
    OP_PLUS = auto()
    OP_MINUS = auto()
    OP_MULTIPLY = auto()
    OP_DIVIDE = auto()
    OP_MODULO = auto()
    OP_POWER = auto()
    OP_INCREMENT = auto()
    OP_DECREMENT = auto()

    # Operadores relacionales
    OP_LT = auto()
    OP_LE = auto()
    OP_GT = auto()
    OP_GE = auto()
    OP_SHIFT_LEFT = auto()
    OP_SHIFT_RIGHT = auto()
    OP_NE = auto()
    OP_EQ = auto()

    # Operadores lógicos
    OP_AND = auto()
    OP_OR = auto()
    OP_NOT = auto()

    # Asignación
    OP_ASSIGN = auto()

    # Símbolos
    SYM_LPAREN = auto()
    SYM_RPAREN = auto()
    SYM_LBRACE = auto()
    SYM_RBRACE = auto()
    SYM_COMMA = auto()
    SYM_SEMICOLON = auto()
    SYM_COLON = auto()

    # Literales de cadena y carácter
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()

    # Error
    ERROR = auto()
