import json
import pytest
from arcane_compiler.lexer.lexer import Lexer
from arcane_compiler.parser.parser import Parser
from arcane_compiler.parser.ast_nodes import ASTNode
from arcane_compiler.parser.ast_builder import build_ast
from arcane_compiler.parser.ast_serializer import ast_to_json


def _parse(source: str):
    """Devuelve el CST (salida directa del parser) y los errores."""
    lexer = Lexer(source)
    tokens, _ = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    return ast, parser.errors


def _build(source: str):
    """Devuelve el AST (CST transformado por build_ast) y los errores."""
    cst, errors = _parse(source)
    return build_ast(cst), errors


def _sentencias(source: str) -> list[ASTNode]:
    """Hijos de lista_declaracion en el AST de un programa sin errores."""
    ast, errors = _build(source)
    assert errors == [], f"Errores inesperados: {errors}"
    return ast.children[-1].children


def _expr_ast(expr: str) -> ASTNode:
    """Devuelve el AST de la expresión en `x = <expr>;`."""
    asignacion = _sentencias(f"main {{ x = {expr}; }}")[0]
    return asignacion.children[1]


def _shape(node: ASTNode) -> str:
    """Representación compacta con paréntesis: OP(izq, der) o el lexema."""
    if not node.children:
        return node.value
    return f"{node.value}(" + ", ".join(_shape(c) for c in node.children) + ")"


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
    src = "main { do x = x + 1; until x >= 10 }"
    ast, errors = _parse(src)
    assert errors == []


def test_repeticion_con_llaves():
    src = "main { do { x = x + 1; } until (x >= 10); }"
    ast, errors = _parse(src)
    assert errors == []


def test_repeticion_falta_until():
    src = "main { do x = x + 1; }"
    ast, errors = _parse(src)
    assert any("until" in e for e in errors)


def test_while_anidado_en_do():
    """Antes era imposible: el 'while' interno se tomaba como cierre del do."""
    src = """
    main {
        do
            y = y + 1;
            while x > 7
                x = x - 1;
            end
        until y == 5
    }
    """
    ast, errors = _parse(src)
    assert errors == [], f"Errores inesperados: {errors}"
    repeticion = ast.children[-1].children[0]
    assert repeticion.kind == "repeticion"
    cuerpo = repeticion.children[0]
    assert [s.kind for s in cuerpo.children] == ["asignacion", "iteracion"]


def test_iteracion_con_llaves_y_parentesis():
    src = "main { while (x > 7) { x = x - 1; } }"
    ast, errors = _parse(src)
    assert errors == []


def test_iteracion_condicion_con_grupos():
    """Los paréntesis son agrupación normal, no delimitan toda la condición."""
    src = "main { while (x > 0) && (y > 0) x = x - 1; end }"
    ast, errors = _parse(src)
    assert errors == []


def test_iteracion_falta_parentesis_cierre():
    src = "main { while (x > 7 { x = 1; } }"
    ast, errors = _parse(src)
    assert any("')'" in e for e in errors)


def test_main_falta_parentesis_cierre():
    ast, errors = _parse("main( { x = 1; }")
    assert any("')'" in e for e in errors)


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


def test_ast_estructura_programa():
    """Verifica que programa tiene exactamente los hijos esperados."""
    ast, errors = _parse("main { int x; }")
    assert ast.kind == "programa"
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
        until y >= 10
        cout << z;
    }
    """
    ast, errors = _parse(src)
    assert errors == [], f"Errores inesperados: {errors}"
    assert ast.kind == "programa"


# ─── Precedencia y asociatividad (forma del AST) ─────────────────────────────

def test_and_tiene_mayor_precedencia_que_or():
    assert _shape(_expr_ast("a || b && c")) == "||(a, &&(b, c))"
    assert _shape(_expr_ast("a && b || c")) == "||(&&(a, b), c)"


def test_and_or_asocian_a_la_izquierda():
    assert _shape(_expr_ast("a || b || c")) == "||(||(a, b), c)"
    assert _shape(_expr_ast("a && b && c")) == "&&(&&(a, b), c)"


def test_and_or_con_relacionales():
    assert _shape(_expr_ast("x > 0 || y < 5 && z == 1")) == "||(>(x, 0), &&(<(y, 5), ==(z, 1)))"


def test_potencia_asocia_a_la_derecha():
    assert _shape(_expr_ast("2 ^ 3 ^ 2")) == "^(2, ^(3, 2))"


def test_potencia_mayor_precedencia_que_multiplicacion():
    assert _shape(_expr_ast("2 * 3 ^ 2")) == "*(2, ^(3, 2))"


def test_aritmetica_asocia_a_la_izquierda():
    assert _shape(_expr_ast("8 - 3 - 1")) == "-(-(8, 3), 1)"
    assert _shape(_expr_ast("8 / 2 * 3")) == "*(/(8, 2), 3)"


def test_parentesis_cambian_la_agrupacion():
    assert _shape(_expr_ast("(a || b) && c")) == "&&(||(a, b), c)"
    assert _shape(_expr_ast("(2 ^ 3) ^ 2")) == "^(^(2, 3), 2)"


# ─── '++' / '--' solo como sentencia ─────────────────────────────────────────

def test_incremento_como_sentencia_sigue_funcionando():
    ast, errors = _parse("main { int x; float c; x++; c--; }")
    assert errors == []
    kinds = [n.kind for n in ast.children[-1].children]
    assert kinds.count("incremento") == 2


def test_incremento_en_asignacion_un_solo_error_claro():
    ast, errors = _parse("main { y = x++; z = 1; }")
    assert len(errors) == 1, errors
    assert "solo puede usarse como sentencia" in errors[0]
    # La recuperación no pierde la sentencia siguiente
    assert [n.kind for n in ast.children[-1].children] == ["asignacion", "asignacion"]


def test_decremento_en_condicion_un_solo_error_claro():
    ast, errors = _parse("main { if x-- > 0 then y = 1; end }")
    assert len(errors) == 1, errors
    assert "'--'" in errors[0]


def test_incremento_binario_es_error():
    ast, errors = _parse("main { x = a ++ b; }")
    assert errors, "a ++ b no debe aceptarse"
    assert "'++' solo puede usarse como sentencia" in errors[0]


# ─── AST (build_ast): formas estables ────────────────────────────────────────

def _kinds(node: ASTNode) -> list[str]:
    return [c.kind for c in node.children]


def test_ast_programa():
    ast, errors = _build("main { int x; }")
    assert errors == []
    assert ast.kind == "programa"
    assert _kinds(ast) == ["KW_MAIN", "lista_declaracion"]


def test_ast_declaracion_un_id_conserva_id_list():
    decl = _sentencias("main { int x; }")[0]
    assert _kinds(decl) == ["KW_INT", "id_list"]
    assert [c.value for c in decl.children[1].children] == ["x"]


def test_ast_declaracion_varios_ids():
    decl = _sentencias("main { float a, b, c; }")[0]
    assert _kinds(decl) == ["KW_FLOAT", "id_list"]
    assert [c.value for c in decl.children[1].children] == ["a", "b", "c"]


def test_ast_asignacion_sin_envoltorios():
    asig = _sentencias("main { x = 2 + 3; }")[0]
    assert asig.kind == "asignacion"
    assert _kinds(asig) == ["IDENTIFIER", "OP_PLUS"]
    assert asig.children[0].line == 1 and asig.children[0].col == 8


def test_ast_sent_out_siempre_tiene_salida():
    s1 = _sentencias('main { cout << "hola"; }')[0]
    s2 = _sentencias('main { cout << "x = " << x + 1; }')[0]
    assert _kinds(s1) == ["salida"] and _kinds(s1.children[0]) == ["STRING_LITERAL"]
    assert _kinds(s2.children[0]) == ["STRING_LITERAL", "OP_PLUS"]


def test_ast_sent_in():
    s = _sentencias("main { cin >> x; }")[0]
    assert s.kind == "sent_in" and _kinds(s) == ["IDENTIFIER"]


def test_ast_not_conserva_lexema():
    assert _shape(_expr_ast("!a")) == "!(a)"
    assert _shape(_expr_ast("not a")) == "not(a)"
    assert _expr_ast("not a").kind == "OP_NOT"


def test_ast_estructuras_de_control():
    sel, it, rep = _sentencias(
        "main { if a then x = 1; else x = 2; end "
        "while a x = 1; end "
        "do x = 1; until a }"
    )
    assert _kinds(sel) == ["IDENTIFIER", "lista_sentencias", "else_body"]
    assert _kinds(it) == ["IDENTIFIER", "lista_sentencias"]
    assert _kinds(rep) == ["lista_sentencias", "IDENTIFIER"]


def test_ast_incremento():
    s = _sentencias("main { a++; }")[0]
    assert s.kind == "incremento" and _kinds(s) == ["IDENTIFIER", "OP_INCREMENT"]


def test_ast_conserva_error_con_posicion():
    ast, errors = _build("main { x = 1 }")
    asig = ast.children[-1].children[0]
    assert _kinds(asig) == ["IDENTIFIER", "INTEGER", "error"]
    error = asig.children[-1]
    assert "';'" in error.value
    assert (error.line, error.col) == (1, 14)


def test_ast_conserva_error_de_parentesis():
    ast, errors = _build("main { x = (a + b; }")
    asig = ast.children[-1].children[0]
    grupo = asig.children[1]
    assert grupo.kind == "componente_grupo"
    assert _kinds(grupo) == ["OP_PLUS", "error"]


def test_build_ast_no_modifica_el_cst():
    cst, _ = _parse("main { int x; x = (1 + 2) * 3; }")
    antes = cst.to_dict()
    build_ast(cst)
    assert cst.to_dict() == antes


def test_ast_to_json():
    ast, errors = _build("main { int x; x = 1; }")
    data = json.loads(ast_to_json(ast, not errors, errors))
    assert data["success"] is True and data["error_count"] == 0
    assert data["ast"] == ast.to_dict()
