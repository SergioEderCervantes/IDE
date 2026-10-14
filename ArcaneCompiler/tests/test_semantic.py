from pathlib import Path

from arcane_compiler.errors import LEXICO, SEMANTICO, SINTACTICO
from arcane_compiler.main import compile_source
from arcane_compiler.parser.ast_nodes import ASTNode
from arcane_compiler.semantic.analyzer import SemanticAnalyzer
from arcane_compiler.semantic.constantes import (
    DivisionEntreCero, ExponenteNegativo, evaluar_binaria,
)
from arcane_compiler.semantic.symbol_table import SymbolTable
from arcane_compiler.semantic.tipos import (
    Tipo, asignacion, condicion, operacion_binaria, operacion_unaria,
)

INT, FLOAT, BOOL, ERROR = Tipo.INT, Tipo.FLOAT, Tipo.BOOL, Tipo.ERROR
_SAMPLES = Path(__file__).parent / "samples"


# ─── ASTNode.attrs ───────────────────────────────────────────────────────────

def test_attrs_vacio_por_defecto_y_en_to_dict():
    nodo = ASTNode(kind="IDENTIFIER", value="x", line=1, col=1)
    assert nodo.attrs == {}
    nodo.attrs["tipo"] = "int"
    assert nodo.to_dict()["attrs"] == {"tipo": "int"}
    assert ASTNode(kind="x").attrs is not nodo.attrs  # cada nodo tiene su propio dict


# ─── Tabla de símbolos ───────────────────────────────────────────────────────

def test_insert_asigna_direcciones_secuenciales():
    tabla = SymbolTable()
    x = tabla.insert("x", INT, 2)
    y = tabla.insert("y", INT, 2)
    a = tabla.insert("a", FLOAT, 3)
    assert [(s.nombre, s.direccion, s.declaracion) for s in (x, y, a)] == [
        ("x", 0, 2), ("y", 1, 2), ("a", 2, 3),
    ]
    assert len(tabla) == 3


def test_insert_duplicado_devuelve_none_y_no_consume_direccion():
    tabla = SymbolTable()
    tabla.insert("x", INT, 2)
    assert tabla.insert("x", FLOAT, 3) is None
    assert tabla.lookup("x").tipo == INT  # se conserva la primera declaración
    assert tabla.insert("y", BOOL, 4).direccion == 1


def test_lookup():
    tabla = SymbolTable()
    tabla.insert("x", INT, 1)
    assert tabla.lookup("x").tipo == INT
    assert tabla.lookup("suma") is None
    assert "x" in tabla and "suma" not in tabla


def test_add_reference_una_vez_por_linea():
    tabla = SymbolTable()
    tabla.insert("y", INT, 2)
    for linea in (7, 9, 9, 12):  # y = y + 1 en la línea 9 son dos usos
        tabla.add_reference("y", linea)
    assert tabla.lookup("y").referencias == [7, 9, 12]


def test_add_reference_de_no_declarado_no_hace_nada():
    tabla = SymbolTable()
    tabla.add_reference("suma", 4)
    assert "suma" not in tabla


def test_to_list_en_orden_de_declaracion():
    tabla = SymbolTable()
    tabla.insert("b", FLOAT, 1)
    tabla.insert("a", INT, 2)
    tabla.add_reference("a", 5)
    assert tabla.to_list() == [
        {"nombre": "b", "tipo": "float", "direccion": 0, "declaracion": 1, "referencias": []},
        {"nombre": "a", "tipo": "int", "direccion": 1, "declaracion": 2, "referencias": [5]},
    ]


# ─── Reglas de tipos: operadores binarios ────────────────────────────────────

def test_aritmeticos_int_int():
    for op, s in [("OP_PLUS", "+"), ("OP_MINUS", "-"), ("OP_MULTIPLY", "*"),
                  ("OP_DIVIDE", "/"), ("OP_POWER", "^")]:
        r = operacion_binaria(op, s, INT, INT)
        assert (r.tipo, r.error, r.convertir_izq, r.convertir_der) == (INT, None, False, False)


def test_aritmeticos_con_float_convierten_el_int():
    r = operacion_binaria("OP_PLUS", "+", FLOAT, INT)
    assert (r.tipo, r.convertir_izq, r.convertir_der) == (FLOAT, False, True)
    r = operacion_binaria("OP_MULTIPLY", "*", INT, FLOAT)
    assert (r.tipo, r.convertir_izq, r.convertir_der) == (FLOAT, True, False)
    r = operacion_binaria("OP_DIVIDE", "/", FLOAT, FLOAT)
    assert (r.tipo, r.convertir_izq, r.convertir_der) == (FLOAT, False, False)


def test_aritmeticos_con_bool_son_uso_indebido():
    r = operacion_binaria("OP_PLUS", "+", BOOL, INT)
    assert r.tipo == ERROR and "uso indebido del operador '+'" in r.error


def test_modulo_solo_int():
    assert operacion_binaria("OP_MODULO", "%", INT, INT).tipo == INT
    for izq, der in [(FLOAT, INT), (INT, FLOAT), (BOOL, INT)]:
        r = operacion_binaria("OP_MODULO", "%", izq, der)
        assert r.tipo == ERROR and "solo se aplica a int" in r.error


def test_relacionales():
    r = operacion_binaria("OP_LT", "<", INT, FLOAT)
    assert (r.tipo, r.convertir_izq, r.convertir_der) == (BOOL, True, False)
    assert operacion_binaria("OP_GE", ">=", INT, INT).tipo == BOOL
    r = operacion_binaria("OP_GT", ">", BOOL, BOOL)
    assert r.tipo == ERROR and "uso indebido" in r.error


def test_igualdad():
    assert operacion_binaria("OP_EQ", "==", INT, INT).tipo == BOOL
    assert operacion_binaria("OP_NE", "!=", BOOL, BOOL).tipo == BOOL
    r = operacion_binaria("OP_EQ", "==", FLOAT, INT)
    assert (r.tipo, r.convertir_der) == (BOOL, True)
    r = operacion_binaria("OP_EQ", "==", BOOL, INT)
    assert r.tipo == ERROR and "incompatibilidad de tipos" in r.error


def test_logicos():
    assert operacion_binaria("OP_AND", "&&", BOOL, BOOL).tipo == BOOL
    assert operacion_binaria("OP_OR", "or", BOOL, BOOL).tipo == BOOL
    r = operacion_binaria("OP_AND", "&&", INT, BOOL)
    assert r.tipo == ERROR and "'&&'" in r.error


def test_error_se_propaga_sin_nuevo_mensaje():
    for op, s in [("OP_PLUS", "+"), ("OP_EQ", "=="), ("OP_AND", "&&"), ("OP_MODULO", "%")]:
        r = operacion_binaria(op, s, ERROR, INT)
        assert (r.tipo, r.error) == (ERROR, None)


# ─── Reglas de tipos: operadores unarios ─────────────────────────────────────

def test_not():
    assert operacion_unaria("OP_NOT", "!", BOOL).tipo == BOOL
    r = operacion_unaria("OP_NOT", "not", INT)
    assert r.tipo == ERROR and "solo se aplica a bool" in r.error


def test_negativo_e_incremento():
    for op, s in [("OP_NEG", "-"), ("OP_INCREMENT", "++"), ("OP_DECREMENT", "--")]:
        assert operacion_unaria(op, s, INT).tipo == INT
        assert operacion_unaria(op, s, FLOAT).tipo == FLOAT
        r = operacion_unaria(op, s, BOOL)
        assert r.tipo == ERROR and "solo se aplica a int o float" in r.error
    assert operacion_unaria("OP_NEG", "-", ERROR) == operacion_unaria("OP_NOT", "!", ERROR)


# ─── Asignación y condiciones ────────────────────────────────────────────────

def test_asignacion_mismo_tipo():
    for t in (INT, FLOAT, BOOL):
        r = asignacion("x", t, t)
        assert (r.tipo, r.error, r.convertir_der) == (t, None, False)


def test_asignacion_float_desde_int_convierte():
    r = asignacion("a", FLOAT, INT)
    assert (r.tipo, r.error, r.convertir_der) == (FLOAT, None, True)


def test_asignacion_int_desde_float_es_conversion_no_valida():
    r = asignacion("x", INT, FLOAT)
    assert r.tipo == ERROR
    assert "conversión no válida" in r.error and "'x'" in r.error


def test_asignacion_bool_con_numero_es_inconsistencia():
    for destino, origen in [(BOOL, INT), (INT, BOOL), (FLOAT, BOOL)]:
        r = asignacion("v", destino, origen)
        assert r.tipo == ERROR and "inconsistencia de tipos" in r.error


def test_asignacion_con_error_no_reporta():
    assert asignacion("x", INT, ERROR).error is None
    assert asignacion("x", ERROR, FLOAT).error is None


def test_condicion():
    assert condicion("if", BOOL) is None
    assert condicion("while", ERROR) is None
    mensaje = condicion("until", INT)
    assert "'until'" in mensaje and "debe ser bool" in mensaje and "int" in mensaje


# ═══ Valores constantes y analizador ═════════════════════════════════════════

def _analizar(source: str):
    r = compile_source(source, "syntactic")
    assert not r.errores[LEXICO] and not r.errores[SINTACTICO], r.errores
    return SemanticAnalyzer().analyze(r.ast)


def _errores(source: str) -> list[str]:
    return [e.mensaje for e in _analizar(source).errores]


def _sentencias(resultado) -> list[ASTNode]:
    return resultado.ast.children[-1].children


def _expr(source: str) -> ASTNode:
    """Expresión (anotada) de la última asignación del programa."""
    return _sentencias(_analizar(source))[-1].children[1]


def _lanza(fn, excepcion) -> bool:
    try:
        fn()
    except excepcion:
        return True
    return False


# ─── constantes.py ───────────────────────────────────────────────────────────

def test_division_y_residuo_enteros_como_c():
    assert evaluar_binaria("OP_DIVIDE", 7, 2, INT) == 3
    assert evaluar_binaria("OP_DIVIDE", -7, 2, INT) == -3
    assert evaluar_binaria("OP_MODULO", -7, 2, INT) == -1
    assert evaluar_binaria("OP_MODULO", 7, -2, INT) == 1
    assert evaluar_binaria("OP_DIVIDE", 7.0, 2.0, FLOAT) == 3.5


def test_constantes_invalidas():
    assert _lanza(lambda: evaluar_binaria("OP_DIVIDE", 1, 0, INT), DivisionEntreCero)
    assert _lanza(lambda: evaluar_binaria("OP_MODULO", 1, 0, INT), DivisionEntreCero)
    assert _lanza(lambda: evaluar_binaria("OP_POWER", 2, -1, INT), ExponenteNegativo)
    assert evaluar_binaria("OP_POWER", 2.0, -1, FLOAT) == 0.5
    assert evaluar_binaria("OP_POWER", -8.0, 0.5, FLOAT) is None  # no es un número real
    assert evaluar_binaria("OP_POWER", 2, 100000, INT) is None    # demasiado grande


# ─── Declaraciones y tabla de símbolos ───────────────────────────────────────

def test_dtype_se_hereda_a_cada_identificador():
    decl = _sentencias(_analizar("main { float a, b; }"))[0]
    tipo, id_list = decl.children
    assert tipo.attrs == {"tipo": "float"}
    assert id_list.attrs == {"dtype": "float"}
    assert [c.attrs for c in id_list.children] == [
        {"dtype": "float", "dir": 0}, {"dtype": "float", "dir": 1},
    ]


def test_declaracion_duplicada():
    res = _analizar("main {\n int x;\n float x;\n bool y; }")
    [error] = res.errores
    assert "declaración duplicada" in error.mensaje and "línea 2" in error.mensaje
    assert (error.fase, error.linea, error.columna) == (SEMANTICO, 3, 8)
    assert [(s.nombre, s.tipo, s.direccion) for s in res.tabla] == [("x", INT, 0), ("y", BOOL, 1)]


def test_no_declarado_se_reporta_en_cada_uso():
    res = _analizar("main {\n cin >> mas;\n mas = 1;\n cout << mas; }")
    assert [(e.linea, "'mas'" in e.mensaje) for e in res.errores] == [(2, True), (3, True), (4, True)]


def test_no_declarado_no_genera_errores_en_cascada():
    assert _errores("main { int z; z = suma + 1; }") == ["identificador no declarado: 'suma'"]


def test_referencias_en_la_tabla():
    res = _analizar("main {\n int y;\n y = 1;\n y = y + 1;\n cout << y; }")
    assert res.tabla.to_list() == [
        {"nombre": "y", "tipo": "int", "direccion": 0, "declaracion": 2, "referencias": [3, 4, 5]},
    ]


# ─── Asignaciones ────────────────────────────────────────────────────────────

def test_asignacion_float_desde_int_inserta_conv():
    asig = _sentencias(_analizar("main { float a; a = 5; }"))[1]
    conv = asig.children[1]
    assert conv.kind == "CONV" and conv.value == "int→float"
    assert conv.attrs == {"tipo": "float", "valor": 5.0}
    assert conv.children[0].kind == "INTEGER" and conv.children[0].attrs == {"tipo": "int", "valor": 5}
    assert asig.attrs["verificacion"] == "float ← int ✓ con conversión int → float"


def test_asignacion_int_desde_float_es_error():
    res = _analizar("main {\n int x;\n x = 32.32; }")
    [error] = res.errores
    assert "conversión no válida" in error.mensaje and (error.linea, error.columna) == (3, 2)
    assert _sentencias(res)[1].attrs["verificacion"] == "int ← float ✗"


def test_asignacion_bool_con_numero():
    assert "inconsistencia de tipos" in _errores("main { bool b; b = 3; }")[0]
    assert "inconsistencia de tipos" in _errores("main { int x; x = true; }")[0]


def test_asignacion_sin_expresion():
    assert _errores("main { int x; x = ; }") == [
        "asignación sin expresión: falta el valor que se asigna a 'x'",
    ]


# ─── Expresiones ─────────────────────────────────────────────────────────────

def test_expresion_mixta_convierte_y_calcula_valor():
    expr = _expr("main { float a; a = 1 + 2.5; }")
    assert expr.attrs == {"tipo": "float", "valor": 3.5}
    assert [c.kind for c in expr.children] == ["CONV", "REAL"]


def test_variables_no_tienen_valor():
    expr = _expr("main { int x, y; y = x + 1; }")
    assert expr.attrs == {"tipo": "int"}
    assert expr.children[0].attrs == {"tipo": "int", "dir": 0}


def test_division_entera_en_comparacion():
    cond = _sentencias(_analizar("main { if 7 / 2 > 3 then cout << 1; end }"))[0].children[0]
    assert cond.attrs == {"tipo": "bool", "valor": False}  # 7 / 2 = 3 (entera)
    assert cond.children[0].attrs == {"tipo": "int", "valor": 3}


def test_bool_en_aritmetica_es_uso_indebido():
    assert _errores("main { bool b; int x; x = b + 1; }") == [
        "uso indebido del operador '+': no se puede aplicar a bool y int",
    ]


def test_modulo():
    assert _expr("main { int x; x = 7 % 3; }").attrs == {"tipo": "int", "valor": 1}
    assert "solo se aplica a int" in _errores("main { float a; a = 7.5 % 2; }")[0]


def test_igualdad_y_logicos():
    assert _expr("main { bool b; b = 1 == 1.0; }").attrs == {"tipo": "bool", "valor": True}
    assert "incompatibilidad de tipos" in _errores("main { bool b; b = b == 1; }")[0]
    assert "uso indebido del operador '&&'" in _errores("main { bool b; b = 1 && b; }")[0]
    assert "uso indebido del operador 'not'" in _errores("main { bool b; b = not 5; }")[0]


def test_negativo():
    assert _expr("main { int x; x = -2 ^ 2; }").attrs == {"tipo": "int", "valor": -4}
    assert "uso indebido del operador '-'" in _errores("main { bool b; int x; x = -b; }")[0]


def test_division_entre_cero():
    casos = {
        "main { int x; x = 5 / 0; }": "/",
        "main { int x, y; x = y / 0; }": "/",      # el dividendo es una variable
        "main { int x; x = 5 % (2 - 2); }": "%",   # el divisor es una expresión constante
        "main { float a; a = 1.0 / 0.0; }": "/",
    }
    for src, op in casos.items():
        assert _errores(src) == [f"división entre cero en '{op}'"], src


def test_exponente_negativo_en_potencia_entera():
    assert "exponente negativo" in _errores("main { int x; x = 2 ^ -1; }")[0]
    assert "exponente negativo" in _errores("main { int x, y; x = y ^ -1; }")[0]
    assert _expr("main { float a; a = 2.0 ^ -1; }").attrs == {"tipo": "float", "valor": 0.5}


# ─── Sentencias ──────────────────────────────────────────────────────────────

def test_condiciones_deben_ser_bool():
    errores = _errores(
        "main { int x;\n if x then x = 1; end\n while x + 1 x = 1; end\n do x = 1; until x }"
    )
    assert errores == [
        "la condición de 'if' debe ser bool, se obtuvo int",
        "la condición de 'while' debe ser bool, se obtuvo int",
        "la condición de 'until' debe ser bool, se obtuvo int",
    ]


def test_condicion_valida_se_anota():
    sel = _sentencias(_analizar("main { int x; if x > 0 && true then x = 1; end }"))[1]
    assert sel.attrs["verificacion"] == "condición bool ✓"


def test_incremento():
    assert _errores("main { int x; float a; x++; a--; }") == []
    assert "uso indebido del operador '++'" in _errores("main { bool b; b++; }")[0]


def test_cin_y_cout():
    assert _errores('main { int x; cin >> x; cout << "x = " << x * 2; }') == []
    assert _errores("main { cout << y + 1; }") == ["identificador no declarado: 'y'"]


# ─── Copia, traza y archivo de la maestra ────────────────────────────────────

def test_el_ast_original_no_se_modifica():
    r = compile_source("main { float a; a = 1 + 2; }", "syntactic")
    antes = r.ast.to_dict()
    SemanticAnalyzer().analyze(r.ast)
    assert r.ast.to_dict() == antes


def test_recorrido():
    res = _analizar("main {\n float a;\n a = 1;\n if a > 0 then a = a; end }")
    pasos = [(t["linea"], t["accion"]) for t in res.recorrido]
    assert pasos == [
        (1, "inicio"),
        (2, "insertar"),
        (3, "buscar"), (3, "conversión"), (3, "asignación"),
        (4, "buscar"), (4, "conversión"), (4, "condición"),
        (4, "buscar"), (4, "buscar"), (4, "asignación"),
        (None, "fin"),
    ]


def test_samples_validos_sin_errores_semanticos():
    for nombre in ["valid_full.c", "valid_simple.c", "valid_syntax_1.c",
                   "valid_syntax_2.c", "valid_syntax_full.c"]:
        res = _analizar((_SAMPLES / nombre).read_text(encoding="utf-8"))
        assert res.errores == [], (nombre, res.errores)


def test_test_semantica_errores():
    res = _analizar((_SAMPLES / "TestSemantica.txt").read_text(encoding="utf-8"))
    assert [(e.linea, e.columna, e.mensaje.split(":")[0]) for e in res.errores] == [
        (4, 5, "identificador no declarado"),
        (5, 5, "conversión no válida"),
        (14, 5, "conversión no válida"),
        (16, 9, "conversión no válida"),
        (33, 13, "identificador no declarado"),
        (37, 16, "identificador no declarado"),
    ]


def test_test_semantica_tabla():
    res = _analizar((_SAMPLES / "TestSemantica.txt").read_text(encoding="utf-8"))
    assert [(s.nombre, str(s.tipo), s.direccion, s.declaracion) for s in res.tabla] == [
        ("x", "int", 0, 2), ("y", "int", 1, 2), ("z", "int", 2, 2),
        ("a", "float", 3, 3), ("b", "float", 4, 3), ("c", "float", 5, 3),
    ]
    assert res.tabla.lookup("x").referencias == [5, 6, 11, 27, 30, 31, 32, 38]


def test_test_semantica_valores_constantes():
    res = _analizar((_SAMPLES / "TestSemantica.txt").read_text(encoding="utf-8"))
    valores = {
        s.line: s.children[1].attrs.get("valor")
        for s in _sentencias(res) if s.kind == "asignacion"
    }
    assert {l: valores[l] for l in (7, 10, 11, 12, 13, 27)} == {
        7: 4, 10: 61.0, 11: 8, 12: -2, 13: 64, 27: 7,
    }
    assert valores[8] is None  # z = y + 7 depende de una variable
