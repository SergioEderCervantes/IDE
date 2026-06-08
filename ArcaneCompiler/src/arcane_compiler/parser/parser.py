from __future__ import annotations
from typing import Optional
from ..lexer.token import Token
from ..lexer.token_type import TokenType
from .ast_nodes import ASTNode


# Tokens que nunca forman parte de la gramática (ignorar silenciosamente)
_SKIP_TYPES = {TokenType.COMMENT_LINE, TokenType.COMMENT_BLOCK}

# FIRST sets para decisiones de bifurcación
_FIRST_TIPO = {TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_BOOL}
_FIRST_SENTENCIA = {
    TokenType.KW_IF, TokenType.KW_WHILE, TokenType.KW_DO,
    TokenType.KW_CIN, TokenType.KW_COUT, TokenType.IDENTIFIER,
}
_FIRST_DECLARACION = _FIRST_TIPO | _FIRST_SENTENCIA
_FIRST_COMPONENTE = {
    TokenType.SYM_LPAREN,
    TokenType.INTEGER, TokenType.REAL,
    TokenType.IDENTIFIER,
    TokenType.KW_TRUE, TokenType.KW_FALSE,
    TokenType.OP_AND, TokenType.OP_OR, TokenType.OP_NOT,
}
_REL_OPS = {
    TokenType.OP_LT, TokenType.OP_LE,
    TokenType.OP_GT, TokenType.OP_GE,
    TokenType.OP_EQ, TokenType.OP_NE,
}
_SUMA_OPS = {
    TokenType.OP_PLUS, TokenType.OP_MINUS,
    TokenType.OP_INCREMENT, TokenType.OP_DECREMENT,
}
_MULT_OPS = {
    TokenType.OP_MULTIPLY, TokenType.OP_DIVIDE, TokenType.OP_MODULO,
}
# Tokens de sincronización para recuperación de errores
_SYNC_EXPRESION = {TokenType.SYM_SEMICOLON, TokenType.SYM_RPAREN, TokenType.KW_END}
_SYNC_SENTENCIA = {
    TokenType.SYM_SEMICOLON, TokenType.KW_END,
    TokenType.KW_WHILE, TokenType.KW_IF, TokenType.KW_DO,
    TokenType.KW_CIN, TokenType.KW_COUT,
}
_SYNC_DECLARACION = _FIRST_TIPO | {TokenType.SYM_RBRACE}


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        # Filtrar comentarios
        self._tokens: list[Token] = [
            t for t in tokens if t.type not in _SKIP_TYPES
        ]
        self._pos: int = 0
        self._errors: list[str] = []

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    # ─── Primitivas de acceso a tokens ───────────────────────────────────────

    def _current(self) -> Optional[Token]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _peek(self, offset: int = 1) -> Optional[Token]:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return None

    def _is_at_end(self) -> bool:
        return self._pos >= len(self._tokens)

    def _current_is(self, *types: TokenType) -> bool:
        tok = self._current()
        return tok is not None and tok.type in types

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, ttype: TokenType, msg: str = "") -> Optional[Token]:
        """
        Consume el token actual si es del tipo esperado.
        Si no, registra error y retorna None (sin avanzar).
        """
        tok = self._current()
        if tok is not None and tok.type == ttype:
            return self._advance()
        if not msg:
            msg = f"se esperaba '{ttype.name}'"
        if tok is not None:
            full_msg = (
                f"Error sintáctico en línea {tok.line}, col {tok.column}: "
                f"{msg}, se encontró '{tok.value}' ({tok.type.name})"
            )
        else:
            full_msg = f"Error sintáctico: fin de archivo inesperado, {msg}"
        self._errors.append(full_msg)
        return None

    def _sync_to(self, sync_set: set[TokenType]) -> None:
        """Panic mode: avanza hasta encontrar un token de sincronización."""
        while not self._is_at_end():
            if self._current().type in sync_set:
                return
            self._advance()

    def _make_token_node(self, token: Token) -> ASTNode:
        return ASTNode(
            kind=token.type.name,
            value=token.value,
            line=token.line,
            col=token.column,
        )

    # ─── Punto de entrada ────────────────────────────────────────────────────

    def parse(self) -> ASTNode:
        """Parsea el programa completo. Retorna la raíz del AST."""
        node = self._parse_programa()
        if not self._is_at_end():
            tok = self._current()
            self._errors.append(
                f"Error sintáctico en línea {tok.line}, col {tok.column}: "
                f"tokens inesperados después del fin del programa"
            )
        return node

    # ─── Reglas gramaticales ─────────────────────────────────────────────────

    def _parse_programa(self) -> ASTNode:
        node = ASTNode(kind="programa")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        main_tok = self._expect(TokenType.KW_MAIN, "se esperaba 'main'")
        if main_tok:
            node.add(self._make_token_node(main_tok))

        self._expect(TokenType.SYM_LBRACE, "se esperaba '{'")

        lista = self._parse_lista_declaracion()
        node.add(lista)

        self._expect(TokenType.SYM_RBRACE, "se esperaba '}'")
        return node

    def _parse_lista_declaracion(self) -> ASTNode:
        node = ASTNode(kind="lista_declaracion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        while not self._is_at_end() and self._current_is(*_FIRST_DECLARACION):
            if self._current_is(TokenType.SYM_RBRACE):
                break
            decl = self._parse_declaracion()
            if decl:
                node.add(decl)

        return node

    def _parse_declaracion(self) -> Optional[ASTNode]:
        if self._current_is(*_FIRST_TIPO):
            return self._parse_declaracion_variable()
        elif self._current_is(*_FIRST_SENTENCIA):
            return self._parse_sentencia()
        else:
            tok = self._current()
            if tok:
                self._errors.append(
                    f"Error sintáctico en línea {tok.line}, col {tok.column}: "
                    f"declaración inesperada con '{tok.value}' ({tok.type.name})"
                )
                self._advance()
            return None

    def _parse_declaracion_variable(self) -> ASTNode:
        node = ASTNode(kind="declaracion_variable")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        tipo = self._parse_tipo()
        node.add(tipo)

        id_list = self._parse_id_list()
        node.add(id_list)

        self._expect(TokenType.SYM_SEMICOLON, "se esperaba ';' al final de declaración")
        return node

    def _parse_tipo(self) -> ASTNode:
        tok = self._current()
        if self._current_is(TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_BOOL):
            return self._make_token_node(self._advance())
        self._errors.append(
            f"Error sintáctico en línea {tok.line}, col {tok.column}: "
            f"se esperaba tipo (int/float/bool)"
        )
        return ASTNode(kind="tipo_error", line=tok.line if tok else None)

    def _parse_id_list(self) -> ASTNode:
        node = ASTNode(kind="id_list")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        first = self._expect(TokenType.IDENTIFIER, "se esperaba identificador")
        if first:
            node.add(self._make_token_node(first))

        while self._current_is(TokenType.SYM_COMMA):
            self._advance()  # consume ','
            nxt = self._expect(TokenType.IDENTIFIER, "se esperaba identificador después de ','")
            if nxt:
                node.add(self._make_token_node(nxt))

        return node

    def _parse_lista_sentencias(self, stop_tokens: set = None) -> ASTNode:
        node = ASTNode(kind="lista_sentencias")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        while not self._is_at_end() and self._current_is(*_FIRST_SENTENCIA):
            if stop_tokens and self._current_is(*stop_tokens):
                break
            sent = self._parse_sentencia()
            if sent:
                node.add(sent)

        return node

    def _parse_sentencia(self) -> Optional[ASTNode]:
        tok = self._current()
        if tok is None:
            return None

        if tok.type == TokenType.KW_IF:
            return self._parse_seleccion()
        elif tok.type == TokenType.KW_WHILE:
            return self._parse_iteracion()
        elif tok.type == TokenType.KW_DO:
            return self._parse_repeticion()
        elif tok.type == TokenType.KW_CIN:
            return self._parse_sent_in()
        elif tok.type == TokenType.KW_COUT:
            return self._parse_sent_out()
        elif tok.type == TokenType.IDENTIFIER:
            nxt = self._peek()
            if nxt and nxt.type in (TokenType.OP_INCREMENT, TokenType.OP_DECREMENT):
                return self._parse_incremento()
            return self._parse_asignacion()
        else:
            self._errors.append(
                f"Error sintáctico en línea {tok.line}, col {tok.column}: "
                f"sentencia inesperada con '{tok.value}'"
            )
            self._sync_to(_SYNC_SENTENCIA)
            return None

    def _parse_incremento(self) -> ASTNode:
        node = ASTNode(kind="incremento")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column
        id_tok = self._expect(TokenType.IDENTIFIER, "se esperaba identificador")
        if id_tok:
            node.add(self._make_token_node(id_tok))
        if self._current_is(TokenType.OP_INCREMENT, TokenType.OP_DECREMENT):
            node.add(self._make_token_node(self._advance()))
        self._expect(TokenType.SYM_SEMICOLON, "se esperaba ';'")
        return node

    def _parse_asignacion(self) -> ASTNode:
        node = ASTNode(kind="asignacion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        id_tok = self._expect(TokenType.IDENTIFIER, "se esperaba identificador")
        if id_tok:
            node.add(self._make_token_node(id_tok))

        self._expect(TokenType.OP_ASSIGN, "se esperaba '='")

        sent_expr = self._parse_sent_expresion()
        node.add(sent_expr)

        return node

    def _parse_sent_expresion(self) -> ASTNode:
        node = ASTNode(kind="sent_expresion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        if self._current_is(TokenType.SYM_SEMICOLON):
            # asignación vacía: "x = ;"
            self._advance()
            return node

        try:
            expr = self._parse_expresion()
            node.add(expr)
        except ParseError:
            self._sync_to(_SYNC_EXPRESION)

        self._expect(TokenType.SYM_SEMICOLON, "se esperaba ';'")
        return node

    def _parse_seleccion(self) -> ASTNode:
        node = ASTNode(kind="seleccion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        self._expect(TokenType.KW_IF, "se esperaba 'if'")

        try:
            expr = self._parse_expresion()
            node.add(expr)
        except ParseError:
            self._sync_to({TokenType.KW_THEN})

        self._expect(TokenType.KW_THEN, "se esperaba 'then'")

        then_body = self._parse_lista_sentencias()
        node.add(then_body)

        if self._current_is(TokenType.KW_ELSE):
            self._advance()
            else_node = ASTNode(kind="else_body")
            else_body = self._parse_lista_sentencias()
            else_node.add(else_body)
            node.add(else_node)

        self._expect(TokenType.KW_END, "se esperaba 'end'")
        return node

    def _parse_iteracion(self) -> ASTNode:
        node = ASTNode(kind="iteracion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        self._expect(TokenType.KW_WHILE, "se esperaba 'while'")

        try:
            expr = self._parse_expresion()
            node.add(expr)
        except ParseError:
            self._sync_to(_FIRST_SENTENCIA | {TokenType.KW_END})

        body = self._parse_lista_sentencias()
        node.add(body)

        self._expect(TokenType.KW_END, "se esperaba 'end'")
        return node

    def _parse_repeticion(self) -> ASTNode:
        node = ASTNode(kind="repeticion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        self._expect(TokenType.KW_DO, "se esperaba 'do'")

        body = self._parse_lista_sentencias(stop_tokens={TokenType.KW_WHILE})
        node.add(body)

        self._expect(TokenType.KW_WHILE, "se esperaba 'while'")

        try:
            expr = self._parse_expresion()
            node.add(expr)
        except ParseError:
            self._sync_to(_SYNC_SENTENCIA)

        return node

    def _parse_sent_in(self) -> ASTNode:
        node = ASTNode(kind="sent_in")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        self._expect(TokenType.KW_CIN, "se esperaba 'cin'")
        self._expect(TokenType.OP_SHIFT_RIGHT, "se esperaba '>>'")

        id_tok = self._expect(TokenType.IDENTIFIER, "se esperaba identificador")
        if id_tok:
            node.add(self._make_token_node(id_tok))

        self._expect(TokenType.SYM_SEMICOLON, "se esperaba ';'")
        return node

    def _parse_sent_out(self) -> ASTNode:
        node = ASTNode(kind="sent_out")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        self._expect(TokenType.KW_COUT, "se esperaba 'cout'")
        self._expect(TokenType.OP_SHIFT_LEFT, "se esperaba '<<'")

        salida = self._parse_salida()
        node.add(salida)

        self._expect(TokenType.SYM_SEMICOLON, "se esperaba ';'")
        return node

    def _parse_salida(self) -> ASTNode:
        node = ASTNode(kind="salida")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        if self._current_is(TokenType.STRING_LITERAL):
            str_tok = self._advance()
            node.add(self._make_token_node(str_tok))
            # salida → cadena [ << expresion ]
            if self._current_is(TokenType.OP_SHIFT_LEFT):
                self._advance()
                try:
                    expr = self._parse_expresion()
                    node.add(expr)
                except ParseError:
                    self._sync_to(_SYNC_SENTENCIA)
        else:
            # salida → expresion [ << cadena ]
            try:
                expr = self._parse_expresion()
                node.add(expr)
            except ParseError:
                self._sync_to(_SYNC_SENTENCIA)
            if self._current_is(TokenType.OP_SHIFT_LEFT):
                self._advance()
                str_tok = self._expect(TokenType.STRING_LITERAL, "se esperaba cadena de texto")
                if str_tok:
                    node.add(self._make_token_node(str_tok))

        return node

    def _parse_expresion(self) -> ASTNode:
        """expresion → comparacion [('&&' | '||') comparacion]*"""
        node = ASTNode(kind="expresion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        left = self._parse_comparacion()
        node.add(left)

        while self._current_is(TokenType.OP_AND, TokenType.OP_OR):
            op_tok = self._advance()
            node.add(self._make_token_node(op_tok))
            right = self._parse_comparacion()
            node.add(right)

        return node

    def _parse_comparacion(self) -> ASTNode:
        """comparacion → expresion_simple [rel_op expresion_simple]"""
        node = ASTNode(kind="comparacion")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        left = self._parse_expresion_simple()
        node.add(left)

        if self._current_is(*_REL_OPS):
            op_tok = self._advance()
            node.add(self._make_token_node(op_tok))
            right = self._parse_expresion_simple()
            node.add(right)

        return node

    def _parse_expresion_simple(self) -> ASTNode:
        node = ASTNode(kind="expresion_simple")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        left = self._parse_termino()
        node.add(left)

        while self._current_is(*_SUMA_OPS):
            op_tok = self._advance()
            node.add(self._make_token_node(op_tok))
            right = self._parse_termino()
            node.add(right)

        return node

    def _parse_termino(self) -> ASTNode:
        node = ASTNode(kind="termino")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        left = self._parse_factor()
        node.add(left)

        while self._current_is(*_MULT_OPS):
            op_tok = self._advance()
            node.add(self._make_token_node(op_tok))
            right = self._parse_factor()
            node.add(right)

        return node

    def _parse_factor(self) -> ASTNode:
        node = ASTNode(kind="factor")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        left = self._parse_componente()
        node.add(left)

        while self._current_is(TokenType.OP_POWER):
            op_tok = self._advance()
            node.add(self._make_token_node(op_tok))
            right = self._parse_componente()
            node.add(right)

        return node

    def _parse_componente(self) -> ASTNode:
        tok = self._current()

        if tok is None:
            self._errors.append("Error sintáctico: fin de archivo inesperado en expresión")
            raise ParseError("EOF in componente")

        # ! componente  (negación unaria)
        if tok.type == TokenType.OP_NOT:
            node = ASTNode(kind="componente_not", line=tok.line, col=tok.column)
            node.add(self._make_token_node(self._advance()))
            node.add(self._parse_componente())
            return node

        # ( expresion )
        if tok.type == TokenType.SYM_LPAREN:
            self._advance()
            node = ASTNode(kind="componente_grupo", line=tok.line, col=tok.column)
            try:
                expr = self._parse_expresion()
                node.add(expr)
            except ParseError:
                self._sync_to({TokenType.SYM_RPAREN})
            self._expect(TokenType.SYM_RPAREN, "se esperaba ')'")
            return node

        # Literales y identificador
        if tok.type in (
            TokenType.INTEGER, TokenType.REAL,
            TokenType.IDENTIFIER,
            TokenType.KW_TRUE, TokenType.KW_FALSE,
        ):
            return self._make_token_node(self._advance())

        # No es un componente válido
        self._errors.append(
            f"Error sintáctico en línea {tok.line}, col {tok.column}: "
            f"expresión inválida con '{tok.value}' ({tok.type.name})"
        )
        self._sync_to(_SYNC_EXPRESION)
        raise ParseError(f"Invalid componente at {tok.line}:{tok.column}")
