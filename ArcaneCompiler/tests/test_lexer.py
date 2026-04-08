import unittest
from pathlib import Path

from arcane_compiler.lexer.token_type import TokenType
from arcane_compiler.lexer.token import Token
from arcane_compiler.lexer.lexer import Lexer


class TestTokenImports(unittest.TestCase):
    def test_token_type_instantiation(self):
        tt = TokenType.INTEGER
        self.assertEqual(tt, TokenType.INTEGER)

    def test_token_instantiation(self):
        tok = Token(type=TokenType.INTEGER, value="42", line=1, column=1)
        self.assertEqual(tok.type, TokenType.INTEGER)
        self.assertEqual(tok.value, "42")
        self.assertEqual(tok.line, 1)
        self.assertEqual(tok.column, 1)


class TestLexer(unittest.TestCase):
    def test_integer_token(self):
        tokens, errors = Lexer("42").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.INTEGER)
        self.assertEqual(tokens[0].value, "42")
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[0].column, 1)

    def test_real_token(self):
        tokens, errors = Lexer("3.14").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.REAL)

    def test_identifier(self):
        tokens, errors = Lexer("myVar123").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)

    def test_reserved_words(self):
        tokens, errors = Lexer("if else while int float").tokenize()
        self.assertEqual(len(tokens), 5)
        self.assertEqual(errors, [])
        expected = [TokenType.KW_IF, TokenType.KW_ELSE, TokenType.KW_WHILE,
                    TokenType.KW_INT, TokenType.KW_FLOAT]
        for tok, expected_type in zip(tokens, expected):
            self.assertEqual(tok.type, expected_type)

    def test_operators_compound(self):
        tokens, errors = Lexer("++ -- <= >= != == && ||").tokenize()
        self.assertEqual(len(tokens), 8)
        expected = [
            TokenType.OP_INCREMENT, TokenType.OP_DECREMENT,
            TokenType.OP_LE, TokenType.OP_GE,
            TokenType.OP_NE, TokenType.OP_EQ,
            TokenType.OP_AND, TokenType.OP_OR,
        ]
        for tok, expected_type in zip(tokens, expected):
            self.assertEqual(tok.type, expected_type)

    def test_comment_line(self):
        tokens, errors = Lexer("// comentario\n").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.COMMENT_LINE)
        self.assertEqual(errors, [])

    def test_comment_block(self):
        tokens, errors = Lexer("/* bloque */").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.COMMENT_BLOCK)
        self.assertEqual(errors, [])

    def test_comment_block_unclosed(self):
        tokens, errors = Lexer("/* sin cerrar").tokenize()
        self.assertEqual(len(tokens), 0)
        self.assertEqual(len(errors), 1)

    def test_string_literal(self):
        tokens, errors = Lexer('"hola mundo"').tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.STRING_LITERAL)
        self.assertEqual(tokens[0].value, "hola mundo")

    def test_char_literal(self):
        tokens, errors = Lexer("'A'").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.CHAR_LITERAL)
        self.assertEqual(tokens[0].value, "A")

    def test_invalid_char(self):
        tokens, errors = Lexer("@").tokenize()
        self.assertEqual(len(tokens), 0)
        self.assertEqual(len(errors), 1)

    def test_error_recovery(self):
        tokens, errors = Lexer("int @ x").tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.KW_INT, types)
        self.assertIn(TokenType.IDENTIFIER, types)
        self.assertEqual(len(errors), 1)

    def test_line_column_tracking(self):
        tokens, errors = Lexer("int\nx").tokenize()
        x_tok = next(t for t in tokens if t.type == TokenType.IDENTIFIER)
        self.assertEqual(x_tok.line, 2)
        self.assertEqual(x_tok.column, 1)

    def test_full_sample(self):
        sample = Path(__file__).parent / "samples" / "valid_full.c"
        source = sample.read_text(encoding="utf-8")
        tokens, errors = Lexer(source).tokenize()
        self.assertEqual(len(errors), 0)
        self.assertGreater(len(tokens), 30)

    def test_error_sample(self):
        sample = Path(__file__).parent / "samples" / "errors.c"
        source = sample.read_text(encoding="utf-8")
        tokens, errors = Lexer(source).tokenize()
        self.assertGreaterEqual(len(errors), 3)


if __name__ == "__main__":
    unittest.main()
