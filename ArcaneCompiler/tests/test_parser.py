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
