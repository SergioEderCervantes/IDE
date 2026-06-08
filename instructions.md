# instrucciones.md — Fase 2: Análisis Sintáctico (ArcaneCompiler + ArcaneIDE)

## Contexto del proyecto

Repositorio con dos paquetes Python compartiendo un único `.venv` en la raíz `IDE/`:

```
IDE/
├── .venv/
├── ArcaneIDE/          ← IDE PyQt6
│   └── src/
│       ├── core/
│       │   └── compiler_runner.py
│       └── ui/
│           ├── main_window.py
│           └── output_tabs.py
└── ArcaneCompiler/     ← Compilador
    └── src/arcane_compiler/
        ├── lexer/
        │   ├── token_type.py
        │   ├── token.py
        │   └── lexer.py
        ├── utils/
        │   └── output.py
        └── main.py
```

El lexer ya funciona y tiene 17 tests pasando (`ArcaneCompiler/tests/test_lexer.py`).
Los tokens de comentarios (`COMMENT_LINE`, `COMMENT_BLOCK`) están en el stream; el parser los filtrará.

---

## Convención de trabajo: CHECKPOINT por fase

> **CRÍTICO**: Al terminar cada fase numerada, DETENTE completamente.
> Ejecuta todos los tests y validaciones indicados al final de esa fase.
> Reporta los resultados claramente y espera confirmación explícita del usuario
> antes de continuar con la siguiente fase.
> No avances si hay tests fallando.

---

## FASE 0 — Cambios al Lexer

**Objetivo**: agregar tokens faltantes requeridos por la gramática.

### 0.1 — `ArcaneCompiler/src/arcane_compiler/lexer/token_type.py`

Agregar dentro del bloque de palabras reservadas (junto a `KW_WHILE`, `KW_INT`, etc.):

```python
KW_THEN = auto()
KW_BOOL = auto()
KW_TRUE = auto()
KW_FALSE = auto()
```

**No eliminar ni renombrar ningún token existente.** Solo agregar.

### 0.2 — `ArcaneCompiler/src/arcane_compiler/lexer/lexer.py`

En el diccionario `RESERVED`, agregar estas 4 entradas:

```python
"then":  TokenType.KW_THEN,
"bool":  TokenType.KW_BOOL,
"true":  TokenType.KW_TRUE,
"false": TokenType.KW_FALSE,
```

### ✅ CHECKPOINT FASE 0

Ejecutar:
```bash
cd IDE
source .venv/bin/activate
.venv/bin/pytest ArcaneCompiler/tests/ -v
```

**Criterio de éxito**: Los 17 tests existentes siguen pasando (ninguno debe romper).
Reporta la salida completa del pytest y ESPERA confirmación antes de continuar.

---

## FASE 1 — Módulo Parser (ArcaneCompiler)

**Objetivo**: implementar el parser descendente recursivo con construcción de AST.

Crear el directorio: `ArcaneCompiler/src/arcane_compiler/parser/`

### 1.1 — `parser/__init__.py`

Archivo vacío.

### 1.2 — `parser/ast_nodes.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ASTNode:
    """Nodo del Árbol Sintáctico Abstracto."""
    kind: str                              # tipo de nodo: "programa", "if", "asignacion", etc.
    value: Optional[str] = None            # solo en hojas: lexema del token
    line: Optional[int] = None             # línea donde empieza el nodo
    col: Optional[int] = None              # columna donde empieza el nodo
    children: list[ASTNode] = field(default_factory=list)

    def add(self, child: ASTNode) -> ASTNode:
        """Agrega un hijo y retorna self para encadenamiento."""
        if child is not None:
            self.children.append(child)
        return self

    def to_dict(self) -> dict:
        """Serializa el nodo a dict para JSON."""
        return {
            "kind": self.kind,
            "value": self.value,
            "line": self.line,
            "col": self.col,
            "children": [c.to_dict() for c in self.children],
        }
```

### 1.3 — `parser/ast_serializer.py`

```python
import json
from .ast_nodes import ASTNode


def ast_to_json(ast: ASTNode, success: bool, errors: list[str]) -> str:
    """
    Serializa el resultado del parser al formato JSON esperado por el IDE.
    
    Formato de salida:
    {
      "success": bool,
      "ast": { ... } | null,
      "error_count": int
    }
    """
    return json.dumps({
        "success": success,
        "ast": ast.to_dict() if ast is not None else None,
        "error_count": len(errors),
    }, indent=2, ensure_ascii=False)
```

### 1.4 — `parser/parser.py`

Implementar el parser completo siguiendo EXACTAMENTE esta especificación.

#### Gramática de referencia (sin recursión izquierda)

```
programa           → main { lista_declaracion }

lista_declaracion  → declaracion+

declaracion        → declaracion_variable      [si current ∈ {KW_INT, KW_FLOAT, KW_BOOL}]
                   | sentencia                 [si current ∈ FIRST(sentencia)]

declaracion_variable → tipo id_list ;
id_list            → IDENTIFIER { , IDENTIFIER }
tipo               → KW_INT | KW_FLOAT | KW_BOOL

lista_sentencias   → sentencia*

sentencia          → seleccion | iteracion | repeticion | sent_in | sent_out | asignacion

asignacion         → IDENTIFIER = sent_expresion
sent_expresion     → expresion ;
                   | ;                          [asignación vacía: "x = ;"]

seleccion          → if expresion then lista_sentencias [ else lista_sentencias ] end

iteracion          → while expresion lista_sentencias end

repeticion         → do lista_sentencias while expresion

sent_in            → cin >> IDENTIFIER ;
sent_out           → cout << salida
salida             → STRING_LITERAL [ << expresion ]
                   | expresion      [ << STRING_LITERAL ]

expresion          → expresion_simple [ rel_op expresion_simple ]
rel_op             → OP_LT | OP_LE | OP_GT | OP_GE | OP_EQ | OP_NE

expresion_simple   → termino { suma_op termino }
suma_op            → OP_PLUS | OP_MINUS | OP_INCREMENT | OP_DECREMENT

termino            → factor { mult_op factor }
mult_op            → OP_MULTIPLY | OP_DIVIDE | OP_MODULO

factor             → componente { OP_POWER componente }

componente         → ( expresion )
                   | INTEGER | REAL
                   | IDENTIFIER
                   | KW_TRUE | KW_FALSE
                   | op_logico componente       [prefijo unario]

op_logico          → OP_AND | OP_OR | OP_NOT
```

#### Código completo de `parser.py`

```python
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
_OP_LOGICO = {TokenType.OP_AND, TokenType.OP_OR, TokenType.OP_NOT}

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
        # Construir mensaje de error
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
            if not self._current_is(*_FIRST_DECLARACION | {TokenType.SYM_RBRACE}):
                break
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

    def _parse_lista_sentencias(self) -> ASTNode:
        node = ASTNode(kind="lista_sentencias")
        tok = self._current()
        if tok:
            node.line, node.col = tok.line, tok.column

        while not self._is_at_end() and self._current_is(*_FIRST_SENTENCIA):
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
            return self._parse_asignacion()
        else:
            self._errors.append(
                f"Error sintáctico en línea {tok.line}, col {tok.column}: "
                f"sentencia inesperada con '{tok.value}'"
            )
            self._sync_to(_SYNC_SENTENCIA)
            return None

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

        body = self._parse_lista_sentencias()
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
        node = ASTNode(kind="expresion")
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

        # op_logico componente  (prefijo unario)
        if tok.type in _OP_LOGICO:
            node = ASTNode(kind="componente_logico", line=tok.line, col=tok.column)
            op_tok = self._advance()
            node.add(self._make_token_node(op_tok))
            inner = self._parse_componente()
            node.add(inner)
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
```

### ✅ CHECKPOINT FASE 1

Crear el archivo `ArcaneCompiler/tests/test_parser.py` con los siguientes tests:

```python
import pytest
from arcane_compiler.lexer.lexer import Lexer
from arcane_compiler.parser.parser import Parser
from arcane_compiler.parser.ast_nodes import ASTNode


def _parse(source: str):
    lexer = Lexer(source)
    tokens, _ = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    return ast, parser.errors


def test_programa_minimo():
    ast, errors = _parse("main { }")
    assert ast.kind == "programa"
    assert errors == []


def test_declaracion_variable_int():
    ast, errors = _parse("main { int x; }")
    assert errors == []
    lista = ast.children[-1]  # lista_declaracion
    decl = lista.children[0]
    assert decl.kind == "declaracion_variable"


def test_declaracion_multiple_ids():
    ast, errors = _parse("main { float a, b, c; }")
    assert errors == []


def test_declaracion_bool():
    ast, errors = _parse("main { bool flag; }")
    assert errors == []


def test_asignacion_simple():
    ast, errors = _parse("main { int x; x = 5; }")
    assert errors == []


def test_asignacion_expresion():
    ast, errors = _parse("main { int x; x = 2 + 3 * 4; }")
    assert errors == []


def test_seleccion_simple():
    src = "main { if x > 0 then y = 1; end }"
    ast, errors = _parse(src)
    assert errors == []


def test_seleccion_con_else():
    src = "main { if x > 0 then y = 1; else y = 0; end }"
    ast, errors = _parse(src)
    assert errors == []


def test_iteracion():
    src = "main { while x > 0 x = x - 1; end }"
    ast, errors = _parse(src)
    assert errors == []


def test_repeticion():
    src = "main { do x = x + 1; while x < 10 }"
    ast, errors = _parse(src)
    assert errors == []


def test_sent_in():
    ast, errors = _parse("main { cin >> x; }")
    assert errors == []


def test_sent_out_cadena():
    ast, errors = _parse('main { cout << "hola mundo"; }')
    assert errors == []


def test_sent_out_expresion():
    ast, errors = _parse("main { cout << x + 1; }")
    assert errors == []


def test_sent_out_cadena_y_expresion():
    ast, errors = _parse('main { cout << "valor: " << x; }')
    assert errors == []


def test_componente_true_false():
    ast, errors = _parse("main { bool b; b = true; }")
    assert errors == []


def test_expresion_logica():
    src = "main { if !x then y = 1; end }"
    ast, errors = _parse(src)
    assert errors == []


def test_error_falta_then():
    src = "main { if x > 0 y = 1; end }"
    ast, errors = _parse(src)
    assert any("then" in e for e in errors)


def test_error_falta_end():
    src = "main { while x > 0 x = x - 1; }"
    ast, errors = _parse(src)
    assert any("end" in e for e in errors)


def test_error_falta_semicolon():
    src = "main { int x x = 5; }"
    ast, errors = _parse(src)
    assert len(errors) > 0


def test_ast_to_dict():
    ast, errors = _parse("main { int x; }")
    d = ast.to_dict()
    assert d["kind"] == "programa"
    assert isinstance(d["children"], list)
```

Ejecutar:
```bash
.venv/bin/pytest ArcaneCompiler/tests/ -v
```

**Criterio de éxito**:
- Los 17 tests originales siguen pasando
- Los nuevos tests del parser pasan (pueden fallar 1-2 edge cases menores pero los tests de estructura principal deben pasar)

Reporta la salida completa y ESPERA confirmación antes de continuar.

---

## FASE 2 — Integración en `main.py`

**Objetivo**: conectar el parser al CLI del compilador.

### 2.1 — Modificar `ArcaneCompiler/src/arcane_compiler/main.py`

Agregar el soporte para la fase `syntactic`. El flujo es:

1. Si `phase in ("syntactic", "all")`:
   a. Correr el Lexer
   b. Si hay errores léxicos → emitir SINTACTICO vacío + ERRORES con mensaje bloqueante, exit
   c. Si no hay errores → filtrar comentarios, correr Parser, emitir SINTACTICO (JSON) + ERRORES

El formato de la sección SINTACTICO es JSON puro:
```json
{
  "success": true,
  "ast": { ... },
  "error_count": 0
}
```

La función `emit_section` de `output.py` ya maneja el wrapper `===SECTION===`.

Importar en `main.py`:
```python
from .parser.parser import Parser
from .parser.ast_serializer import ast_to_json
```

Condición de bloqueo léxico:
```python
if lex_errors:
    emit_section("SINTACTICO", json.dumps({"success": False, "ast": None, "error_count": 0}))
    emit_section("ERRORES", 
        "BLOQUEADO: Elimina todos los errores léxicos antes del análisis sintáctico.\n" +
        "\n".join(format_error_list(lex_errors))
    )
    sys.exit(1)
```

### ✅ CHECKPOINT FASE 2

Crear el archivo `ArcaneCompiler/tests/samples/valid_syntax_1.c` con este contenido:
```c
main {
    int x, y;
    float promedio;
    bool activo;

    cin >> x;
    cin >> y;

    activo = true;

    if x > y then
        promedio = x;
    else
        promedio = y;
    end

    cout << "resultado: " << promedio;
}
```

Crear `ArcaneCompiler/tests/samples/valid_syntax_2.c`:
```c
main {
    int contador;
    float suma;

    contador = 0;
    suma = 0;

    while contador < 10
        suma = suma + contador;
        contador = contador + 1;
    end

    do
        contador = contador - 1;
    while contador > 0

    cout << suma;
}
```

Crear `ArcaneCompiler/tests/samples/syntax_errors.c`:
```c
main {
    int x;
    x = 5
    if x > 0
        x = x + 1;
    end
    cout << "fin";
}
```
(errores intencionales: falta `;` después de `x = 5`, falta `then`)

Ejecutar manualmente:
```bash
source .venv/bin/activate

# Debe mostrar ===SINTACTICO=== con JSON válido y success: true
arcane-compiler ArcaneCompiler/tests/samples/valid_syntax_1.c syntactic

# Debe mostrar errores sintácticos
arcane-compiler ArcaneCompiler/tests/samples/syntax_errors.c syntactic
```

**Criterio de éxito**:
- `valid_syntax_1.c` produce `"success": true` y un AST no vacío
- `syntax_errors.c` produce `"success": false` con errores con línea y columna

Reporta la salida completa de ambas ejecuciones y ESPERA confirmación.

---

## FASE 3 — Visualización en ArcaneIDE

**Objetivo**: mostrar el AST como árbol colapsable en la pestaña Sintáctico.

### 3.1 — Nuevo signal en `CompilerRunner`

Archivo: `ArcaneIDE/src/core/compiler_runner.py`

Agregar el signal `ast_ready` a la clase `CompilerRunner`:
```python
ast_ready = pyqtSignal(dict)   # emite el dict del AST cuando el parse es exitoso
```

En el método que parsea las secciones del stdout (donde ya existe la lógica de `compilation_finished`), agregar la detección del JSON en la sección `sintactico`:

```python
import json as _json  # importar al inicio del archivo si no existe

# Dentro del método de parseo de secciones:
if section_name == "sintactico":
    try:
        data = _json.loads(section_content)
        if data.get("success") and data.get("ast"):
            self.ast_ready.emit(data["ast"])
    except (ValueError, KeyError):
        pass  # si falla el parse del JSON, no emitir señal
```

### 3.2 — Nuevo widget `ASTTreeWidget`

Crear: `ArcaneIDE/src/ui/ast_tree_widget.py`

```python
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt


# Nodos que representan tokens hoja — se muestran con su valor
_LEAF_KINDS = {
    "IDENTIFIER", "INTEGER", "REAL", "STRING_LITERAL", "CHAR_LITERAL",
    "KW_INT", "KW_FLOAT", "KW_BOOL", "KW_TRUE", "KW_FALSE",
    "KW_IF", "KW_ELSE", "KW_END", "KW_WHILE", "KW_DO",
    "KW_CIN", "KW_COUT", "KW_MAIN", "KW_THEN",
    "OP_PLUS", "OP_MINUS", "OP_MULTIPLY", "OP_DIVIDE", "OP_MODULO",
    "OP_POWER", "OP_INCREMENT", "OP_DECREMENT",
    "OP_LT", "OP_LE", "OP_GT", "OP_GE", "OP_EQ", "OP_NE",
    "OP_AND", "OP_OR", "OP_NOT",
    "OP_ASSIGN", "OP_SHIFT_LEFT", "OP_SHIFT_RIGHT",
    "SYM_SEMICOLON", "SYM_COMMA", "SYM_LPAREN", "SYM_RPAREN",
}


class ASTTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Árbol Sintáctico Abstracto")
        self.setColumnCount(1)
        self.setMinimumWidth(400)

    def populate(self, ast_dict: dict) -> None:
        """Puebla el árbol con el AST y lo expande completamente."""
        self.clear()
        if not ast_dict:
            return
        root_item = self._build_item(ast_dict)
        self.addTopLevelItem(root_item)
        self.expandAll()   # ← requisito de la maestra

    def clear_tree(self) -> None:
        self.clear()

    def _build_item(self, node: dict) -> QTreeWidgetItem:
        kind = node.get("kind", "?")
        value = node.get("value")
        line = node.get("line")
        col = node.get("col")

        # Construir label del nodo
        if kind in _LEAF_KINDS and value is not None:
            if line is not None:
                label = f"{kind}: {value!r}  [L{line}:C{col}]"
            else:
                label = f"{kind}: {value!r}"
        else:
            if line is not None:
                label = f"{kind}  [L{line}:C{col}]"
            else:
                label = kind

        item = QTreeWidgetItem([label])

        for child in node.get("children", []):
            item.addChild(self._build_item(child))

        return item
```

### 3.3 — Modificar `output_tabs.py`

En la pestaña `sintactico`, reemplazar el widget de texto plano por `ASTTreeWidget`.

Pasos:
1. Importar: `from .ast_tree_widget import ASTTreeWidget`
2. En la creación de tabs, la tab `sintactico` (índice correspondiente) debe instanciar `ASTTreeWidget` en lugar de `QPlainTextEdit`
3. Agregar método público `set_ast(ast_dict: dict)`:
   ```python
   def set_ast(self, ast_dict: dict) -> None:
       self._ast_widget.populate(ast_dict)
       # Cambiar foco a la tab sintactico
       self.setCurrentIndex(self._tab_index_of("sintactico"))
   ```
4. Mantener todos los demás tabs sin cambios

**Nota**: Si `output_tabs.py` usa un diccionario para guardar referencias a los widgets de cada tab, agregar `"sintactico": self._ast_widget` a ese dict. Si usa una lista, buscar el índice correspondiente al nombre `"SINTÁCTICO"`.

### 3.4 — Modificar `main_window.py`

1. Conectar el nuevo signal: en el método donde se conectan los signals de `CompilerRunner`:
   ```python
   self._compiler_runner.ast_ready.connect(self._on_ast_ready)
   ```

2. Agregar el slot:
   ```python
   def _on_ast_ready(self, ast_dict: dict) -> None:
       self.ignore_text_changes = True
       self._output_tabs.set_ast(ast_dict)
       self.ignore_text_changes = False
   ```

### ✅ CHECKPOINT FASE 3

Ejecutar el IDE completo:
```bash
source .venv/bin/activate
python -m src.main   # desde ArcaneIDE/
```

Pasos de validación manual:
1. Abrir `valid_syntax_1.c` en el editor
2. Correr compilación (fase syntactic o all)
3. Verificar que la tab "SINTÁCTICO" muestra un árbol expandido con nodos colapsables
4. Verificar que la tab "ERRORES" está limpia
5. Abrir `syntax_errors.c`, compilar y verificar que aparecen errores en la tab "ERRORES" con línea y columna

Reporta capturas de pantalla o descripción detallada de lo que muestra la UI y ESPERA confirmación.

---

## FASE 4 — Archivos de prueba y validación final

**Objetivo**: verificar que el compilador maneja todos los constructos de la gramática.

### 4.1 — Archivo de prueba completo `valid_syntax_full.c`

Crear `ArcaneCompiler/tests/samples/valid_syntax_full.c` con un programa que incluya:
- Declaraciones de los 3 tipos (`int`, `float`, `bool`)
- Declaración con múltiples identificadores
- `if/then/else/end`
- `while/end`
- `do/while`
- `cin >>` y `cout <<`
- Operaciones aritméticas con precedencia (`+`, `-`, `*`, `/`, `^`)
- Operador lógico (`!`, `&&`, `||`)
- Operadores relacionales (`<`, `<=`, `>`, `>=`, `==`, `!=`)
- `true` y `false`

### 4.2 — Tests adicionales en `test_parser.py`

Agregar tests que validen el árbol producido con más detalle:

```python
def test_ast_estructura_programa():
    """Verifica que programa tiene exactamente los hijos esperados."""
    ast, errors = _parse("main { int x; }")
    assert ast.kind == "programa"
    # Debe tener al menos: token main + lista_declaracion
    kinds = [c.kind for c in ast.children]
    assert "lista_declaracion" in kinds
    assert errors == []


def test_programa_with_all_constructs():
    src = """
    main {
        int x, y;
        float z;
        bool flag;
        cin >> x;
        cin >> y;
        z = x + y * 2;
        flag = true;
        if x > y then
            cout << "mayor";
        else
            cout << "menor";
        end
        while x > 0
            x = x - 1;
        end
        do
            y = y + 1;
        while y < 10
        cout << z;
    }
    """
    ast, errors = _parse(src)
    assert errors == [], f"Errores inesperados: {errors}"
    assert ast.kind == "programa"
```

Ejecutar:
```bash
.venv/bin/pytest ArcaneCompiler/tests/ -v
```

**Criterio de éxito**:
- Todos los tests pasan
- El programa completo parsea sin errores

Reporta la salida y ESPERA confirmación final.

---

## Resumen de archivos creados/modificados

### Creados (nuevos)
```
ArcaneCompiler/src/arcane_compiler/parser/__init__.py
ArcaneCompiler/src/arcane_compiler/parser/ast_nodes.py
ArcaneCompiler/src/arcane_compiler/parser/ast_serializer.py
ArcaneCompiler/src/arcane_compiler/parser/parser.py
ArcaneCompiler/tests/test_parser.py
ArcaneCompiler/tests/samples/valid_syntax_1.c
ArcaneCompiler/tests/samples/valid_syntax_2.c
ArcaneCompiler/tests/samples/syntax_errors.c
ArcaneCompiler/tests/samples/valid_syntax_full.c
ArcaneIDE/src/ui/ast_tree_widget.py
```

### Modificados (cambios acotados)
```
ArcaneCompiler/src/arcane_compiler/lexer/token_type.py  ← +4 tokens
ArcaneCompiler/src/arcane_compiler/lexer/lexer.py       ← +4 RESERVED entries
ArcaneCompiler/src/arcane_compiler/main.py              ← +fase syntactic
ArcaneIDE/src/core/compiler_runner.py                   ← +signal ast_ready
ArcaneIDE/src/ui/output_tabs.py                         ← tab sintactico → ASTTreeWidget
ArcaneIDE/src/ui/main_window.py                         ← +slot _on_ast_ready
```

---

## Notas importantes para Claude Code

1. **No modificar** `test_lexer.py` ni ningún test existente.
2. **No crear** un nuevo `.venv`. Usar siempre el de `IDE/.venv`.
3. **No usar** el módulo `re` en el parser (consistencia con el lexer).
4. En `sent_in` y `sent_out`, usar `TokenType.OP_SHIFT_RIGHT` y `TokenType.OP_SHIFT_LEFT` respectivamente (nombres del lexer existente).
5. El `ignore_text_changes` flag en `MainWindow` debe respetarse al actualizar la tab del árbol.
6. Si un método en `output_tabs.py` o `compiler_runner.py` no existe con ese nombre exacto, leer el archivo primero e identificar el método equivalente antes de modificar.
7. **DETENTE** al final de cada fase numerada, ejecuta los tests, reporta resultados y espera confirmación explícita.