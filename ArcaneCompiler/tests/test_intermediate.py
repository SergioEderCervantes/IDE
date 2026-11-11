"""Fase 4: código intermedio de tres direcciones.

Los ejemplos de samples/tiny/ son los programas del TINY de la materia (Tiny_Intermedio_TM)
escritos en nuestro lenguaje. Cada .ci es la salida del tiny.exe de la maestra para el
.tny original: nuestro código debe ser igual línea por línea (sin contar los comentarios).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from arcane_compiler.intermediate import cuadruplos as c
from arcane_compiler.main import compile_source

_TINY = Path(__file__).parent / "samples" / "tiny"
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"


def _lineas(texto: str) -> list[str]:
    """Líneas de código, sin comentarios (#) ni líneas en blanco."""
    return [l.strip() for l in texto.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def _intermedio(source: str):
    r = compile_source(source, "intermediate")
    assert r.intermedio is not None, (r.errores, r.avisos)
    return r.intermedio


def _codigo(cuerpo: str) -> list[str]:
    """Código intermedio de `main { <cuerpo> }`, sin el halt final."""
    lineas = _lineas(_intermedio("main {\n" + cuerpo + "\n}").texto())
    assert lineas[-1] == "halt"
    return lineas[:-1]


# ─── Ejemplos del TINY de la materia ─────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["aritmetica", "ciclo", "condicional", "factorial", "anidado"])
def test_igual_al_tiny_de_la_materia(nombre):
    fuente = (_TINY / f"{nombre}.txt").read_text(encoding="utf-8")
    esperado = _lineas((_TINY / f"{nombre}.ci").read_text(encoding="utf-8"))
    assert _lineas(_intermedio(fuente).texto()) == esperado


def test_error_semantico_no_genera_codigo():
    r = compile_source((_TINY / "error_semantico.txt").read_text(encoding="utf-8"), "intermediate")
    assert r.intermedio is None
    assert any("corrige primero los errores semánticos" in a for a in r.avisos)


def test_factorial_completo():
    """El ejemplo del LEEME_PRIMERO.md de la maestra."""
    fuente = (_TINY / "factorial.txt").read_text(encoding="utf-8")
    assert _lineas(_intermedio(fuente).texto()) == [
        "read x",
        "t1 = 0 < x",
        "if_false t1 goto L1",
        "fact = 1",
        "label L2",
        "t2 = fact * x",
        "fact = t2",
        "t3 = x - 1",
        "x = t3",
        "t4 = x == 0",
        "if_false t4 goto L2",
        "write fact",
        "label L1",
        "halt",
    ]


def test_encabezado_con_comentarios():
    texto = _intermedio("main { int x; x = 1; }").texto()
    primeras = texto.splitlines()[:4]
    assert all(l.startswith("#") for l in primeras[:3]) and primeras[3] == ""


# ─── Sentencias ──────────────────────────────────────────────────────────────

def test_declaraciones_no_generan_codigo():
    assert _codigo("int x, y; float z;") == []


def test_asignacion_de_constante_y_variable_va_directa():
    assert _codigo("int x, y; x = 5; y = x;") == ["x = 5", "y = x"]


def test_operaciones_en_postorden_con_temporales_nuevos():
    assert _codigo("int x, y; y = (x + 1) * (x - 2) / 3;") == [
        "t1 = x + 1", "t2 = x - 2", "t3 = t1 * t2", "t4 = t3 / 3", "y = t4",
    ]


def test_if_sin_else():
    assert _codigo("int x; if x > 0 then x = 1; end") == [
        "t1 = x > 0", "if_false t1 goto L1", "x = 1", "label L1",
    ]


def test_if_con_else_numera_l2_despues_del_then():
    assert _codigo(
        "int x; if x > 0 then if x > 1 then x = 2; end else x = 3; end"
    ) == [
        "t1 = x > 0", "if_false t1 goto L1",
        "t2 = x > 1", "if_false t2 goto L2", "x = 2", "label L2",
        "goto L3", "label L1", "x = 3", "label L3",
    ]


def test_if_con_else_vacio():
    assert _codigo("int x; if x > 0 then x = 1; else end") == [
        "t1 = x > 0", "if_false t1 goto L1", "x = 1", "goto L2", "label L1", "label L2",
    ]


def test_while():
    assert _codigo("int i; while i < 3 { i = i + 1; }") == [
        "label L1", "t1 = i < 3", "if_false t1 goto L2",
        "t2 = i + 1", "i = t2", "goto L1", "label L2",
    ]


def test_while_con_end():
    assert _codigo("int i; while i < 3 i = i + 1; end") == _codigo(
        "int i; while i < 3 { i = i + 1; }"
    )


def test_do_until():
    assert _codigo("int x; do x = x - 1; until x == 0;") == [
        "label L1", "t1 = x - 1", "x = t1", "t2 = x == 0", "if_false t2 goto L1",
    ]


def test_condicion_que_es_una_variable_o_literal_va_directa():
    assert _codigo("bool b; if b then b = false; end while true { }") == [
        "if_false b goto L1", "b = false", "label L1",
        "label L2", "if_false true goto L3", "goto L2", "label L3",
    ]


def test_incremento_y_decremento():
    assert _codigo("int i; float f; i++; f--;") == [
        "t1 = i + 1", "i = t1", "t2 = f - 1.0", "f = t2",
    ]


def test_cin():
    assert _codigo("int x; cin >> x;") == ["read x"]


def test_cout_con_cadena_y_expresion():
    assert _codigo('int i; cout << "i = " << i + 1; cout << i << " fin"; cout << "hola";') == [
        "t1 = i + 1", 'write "i = ", t1', 'write i, " fin"', 'write "hola"',
    ]


# ─── Expresiones ─────────────────────────────────────────────────────────────

def test_todos_los_operadores_binarios():
    ops = {"+": "+", "-": "-", "*": "*", "/": "/", "%": "%", "^": "^",
           "<": "<", "<=": "<=", ">": ">", ">=": ">=", "==": "==", "!=": "!="}
    for fuente, esperado in ops.items():
        destino = "b" if esperado in ("<", "<=", ">", ">=", "==", "!=") else "x"
        assert _codigo(f"int x; bool b; {destino} = x {fuente} 2;") == [
            f"t1 = x {esperado} 2", f"{destino} = t1",
        ]


def test_logicos_sin_cortocircuito_y_alias():
    assert _codigo("bool a, b; a = not a and b or true;") == [
        "t1 = !a", "t2 = t1 && b", "t3 = t2 || true", "a = t3",
    ]
    assert _codigo("bool a, b; a = !a && b || true;") == _codigo(
        "bool a, b; a = not a and b or true;"
    )


def test_menos_unario():
    assert _codigo("int x; x = -x;") == ["t1 = -x", "x = t1"]
    # Sobre un literal es la constante negativa
    assert _codigo("int x; x = -5; x = -2147483648;") == ["x = -5", "x = -2147483648"]
    assert _codigo("float f; f = -2.5;") == ["f = -2.5"]
    assert _codigo("int x; x = - -3;") == ["t1 = - -3", "x = t1"]
    assert _codigo("int x; x = -(x + 1);") == ["t1 = x + 1", "t2 = -t1", "x = t2"]


def test_conversion_int_a_float():
    assert _codigo("int i; float f; f = i / 2; f = f + i; f = 3;") == [
        "t1 = i / 2", "t2 = (float) t1", "f = t2",
        "t3 = (float) i", "t4 = f + t3", "f = t4",
        "t5 = (float) 3", "f = t5",
    ]


def test_constantes():
    # Los enteros se normalizan (como TINY); los reales quedan como están escritos
    assert _codigo("int x; float f; bool b; x = 007; f = 2.50; b = true;") == [
        "x = 7", "f = 2.50", "b = true",
    ]


def test_no_se_precalculan_expresiones_constantes():
    # El análisis semántico conoce el valor (5), pero el código hace la operación
    assert _codigo("int x; x = 2 + 3; x = x * 1;") == [
        "t1 = 2 + 3", "x = t1", "t2 = x * 1", "x = t2",
    ]


def test_codigo_que_nunca_se_ejecuta_se_genera():
    assert _codigo("int x, y; x = 0; if x != 0 then y = 10 / x; end") == [
        "x = 0", "t1 = x != 0", "if_false t1 goto L1", "t2 = 10 / x", "y = t2", "label L1",
    ]


# ─── Cuádruplos ──────────────────────────────────────────────────────────────

def test_cuadruplos_con_tipo_y_linea():
    r = _intermedio("main {\n int x; float f;\n cin >> x;\n f = x * 2;\n}")
    assert [q.to_dict() for q in r.cuadruplos] == [
        {"op": "read", "arg1": None, "arg2": None, "resultado": "x", "tipo": "int", "linea": 3},
        {"op": "*", "arg1": "x", "arg2": "2", "resultado": "t1", "tipo": "int", "linea": 4},
        {"op": "(float)", "arg1": "t1", "arg2": None, "resultado": "t2", "tipo": "float", "linea": 4},
        {"op": "=", "arg1": "t2", "arg2": None, "resultado": "f", "tipo": "float", "linea": 4},
        {"op": "halt", "arg1": None, "arg2": None, "resultado": None, "tipo": None, "linea": None},
    ]
    assert (r.temporales, r.etiquetas) == (2, 0)


def test_clases_y_valores_de_los_operandos():
    r = _intermedio('main { int x; bool b; x = -3; b = true; cout << "hola"; }')
    copia_x, copia_b, write, _halt = r.cuadruplos
    assert (copia_x.arg1.clase, copia_x.arg1.valor) == (c.CONSTANTE, -3)
    assert (copia_x.resultado.clase, copia_x.resultado.texto) == (c.VARIABLE, "x")
    assert copia_b.arg1.valor is True
    assert (write.arg1.clase, write.arg1.valor, write.arg1.texto) == (c.CADENA, "hola", '"hola"')


def test_operandos_de_saltos_son_etiquetas_y_temporales():
    r = _intermedio("main { int x; while x < 3 { x = 1; } }")
    label, op, salto = r.cuadruplos[:3]
    assert label.resultado.clase == c.ETIQUETA and op.resultado.clase == c.TEMPORAL
    assert (salto.op, salto.arg1.texto, salto.resultado.texto) == (c.IF_FALSE, "t1", "L2")


# ─── Pipeline y CLI ──────────────────────────────────────────────────────────

def test_fases_previas_no_generan_codigo_intermedio():
    for fase in ("lexical", "syntactic", "semantic"):
        assert compile_source("main { int x; x = 1; }", fase).intermedio is None


def test_all_genera_codigo_intermedio():
    r = compile_source("main { int x; x = 1; }", "all")
    assert r.intermedio is not None and r.avisos == []


def test_cli_seccion_codigo_intermedio():
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "prog.txt"
        ruta.write_text((_TINY / "aritmetica.txt").read_text(encoding="utf-8"), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "arcane_compiler.main", str(ruta), "intermediate"],
            capture_output=True, cwd=_SRC_DIR,
        )
    salida = proc.stdout.decode("utf-8").replace("\r\n", "\n")
    assert proc.returncode == 0
    inicio = salida.index("===CODIGO_INTERMEDIO===\n") + len("===CODIGO_INTERMEDIO===\n")
    seccion = salida[inicio:salida.index("===END_CODIGO_INTERMEDIO===")]
    assert _lineas(seccion) == _lineas((_TINY / "aritmetica.ci").read_text(encoding="utf-8"))
    errores = json.loads(salida.split("===ERRORES===\n")[1].split("===END_ERRORES===")[0])
    assert errores["avisos"] == []
