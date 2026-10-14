import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from arcane_compiler.errors import CompilerError, LEXICO, SINTACTICO, SEMANTICO
from arcane_compiler.main import compile_source

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"


# ─── CompilerError ───────────────────────────────────────────────────────────

def test_compiler_error_formato():
    assert str(CompilerError(SINTACTICO, "se esperaba ';'", 3, 7)) == (
        "Error sintáctico en línea 3, col 7: se esperaba ';'"
    )
    assert str(CompilerError(SINTACTICO, "fin de archivo inesperado")) == (
        "Error sintáctico: fin de archivo inesperado"
    )


# ─── Pipeline (compile_source) ───────────────────────────────────────────────

def test_fase_lexica_no_ejecuta_sintactico():
    r = compile_source("main { x = 1; }", "lexical")
    assert r.tokens and r.ast is None
    assert r.errores[LEXICO] == []
    assert r.errores[SINTACTICO] is None and r.errores[SEMANTICO] is None


def test_errores_lexicos_estructurados():
    r = compile_source("main {\n  x = 10@;\n}", "lexical")
    [error] = r.errores[LEXICO]
    assert (error.fase, error.linea, error.columna) == (LEXICO, 2, 9)
    assert "@" in error.mensaje


def test_errores_lexicos_bloquean_sintactico():
    r = compile_source("main { x = 10@; }", "syntactic")
    assert r.errores[LEXICO]
    assert r.errores[SINTACTICO] is None and r.ast is None
    assert any("corrige primero los errores léxicos" in a for a in r.avisos)


def test_fase_sintactica_valida():
    r = compile_source("main { int x; x = 1; }", "syntactic")
    assert r.ast is not None and r.ast.kind == "programa"
    assert r.errores[LEXICO] == [] and r.errores[SINTACTICO] == []
    assert r.avisos == []


def test_errores_sintacticos_estructurados():
    r = compile_source("main {\n  x = 1\n}", "syntactic")
    [error] = r.errores[SINTACTICO]
    assert (error.fase, error.linea, error.columna) == (SINTACTICO, 3, 1)
    assert r.ast is not None  # el árbol se muestra aunque haya errores


def test_errores_sintacticos_bloquean_semantico():
    r = compile_source("main { x = 1 }", "semantic")
    assert r.errores[SINTACTICO]
    assert r.errores[SEMANTICO] is None
    assert any("corrige primero los errores sintácticos" in a for a in r.avisos)


def test_fase_all_ejecuta_las_fases_implementadas():
    r = compile_source("main { int x; }", "all")
    assert r.tokens is not None and r.ast is not None
    assert r.avisos == []


def test_fase_pendiente_avisa():
    r = compile_source("main { int x; }", "intermediate")
    assert r.ast is not None
    assert any("aún no está implementada" in a for a in r.avisos)


def test_fase_semantica():
    r = compile_source("main {\n int x;\n x = 1.5;\n}", "semantic")
    assert r.semantico is not None and r.avisos == []
    [error] = r.errores[SEMANTICO]
    assert (error.fase, error.linea, error.columna) == (SEMANTICO, 3, 2)
    # El AST de la fase sintáctica queda sin anotar; el anotado es una copia
    assert r.ast.children[-1].children[1].attrs == {}
    assert r.semantico.ast.children[-1].children[1].attrs["verificacion"] == "int ← float ✗"


def test_fases_previas_no_ejecutan_semantico():
    for fase in ("lexical", "syntactic"):
        r = compile_source("main { int x; }", fase)
        assert r.semantico is None and r.errores[SEMANTICO] is None


def test_fase_all_ejecuta_semantico():
    r = compile_source("main { x = 1; }", "all")
    assert r.semantico is not None
    assert [e.mensaje for e in r.errores[SEMANTICO]] == ["identificador no declarado: 'x'"]
    assert r.avisos == []  # 'all' no avisa de las fases 4 y 5


def test_errores_semanticos_bloquean_codigo_intermedio():
    r = compile_source("main { x = 1; }", "intermediate")
    assert any("corrige primero los errores semánticos" in a for a in r.avisos)


# ─── CLI completa (proceso aparte, como la llama el IDE) ─────────────────────

def _run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(_SRC_DIR), PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "arcane_compiler.main", *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )


def _sections(stdout: str) -> dict[str, str]:
    pattern = re.compile(r"===(?P<n>\w+)===\r?\n(?P<c>.*?)===END_(?P=n)===", re.DOTALL)
    return {m.group("n"): m.group("c").strip() for m in pattern.finditer(stdout)}


def _run_source(source: str, phase: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "prog.txt"
        path.write_text(source, encoding="utf-8")
        return _run_cli(str(path), phase)


def test_cli_emite_las_siete_secciones():
    proc = _run_source("main { int x; }", "syntactic")
    assert proc.returncode == 0
    assert set(_sections(proc.stdout)) == {
        "LEXICO", "SINTACTICO", "SEMANTICO", "CODIGO_INTERMEDIO",
        "TABLA_SIMBOLOS", "ERRORES", "EJECUCION",
    }


def test_cli_errores_del_programa_salen_con_codigo_0():
    proc = _run_source("main { x = 1 }", "syntactic")
    assert proc.returncode == 0
    errores = json.loads(_sections(proc.stdout)["ERRORES"])
    assert errores["lexico"] == []
    assert errores["semantico"] is None
    [error] = errores["sintactico"]
    assert error["linea"] == 1 and error["columna"] == 14


def test_cli_errores_lexicos_en_fase_sintactica():
    proc = _run_source("main { x = 10@; }", "syntactic")
    assert proc.returncode == 0
    sections = _sections(proc.stdout)
    errores = json.loads(sections["ERRORES"])
    assert len(errores["lexico"]) == 1 and errores["sintactico"] is None
    assert errores["avisos"]
    assert sections["SINTACTICO"] == ""


def test_cli_fase_semantica_con_test_semantica():
    source = (Path(__file__).parent / "samples" / "TestSemantica.txt").read_text(encoding="utf-8")
    proc = _run_source(source, "semantic")
    assert proc.returncode == 0
    sections = _sections(proc.stdout)

    errores = json.loads(sections["ERRORES"])
    assert errores["lexico"] == [] and errores["sintactico"] == []
    assert [e["linea"] for e in errores["semantico"]] == [4, 5, 14, 16, 33, 37]

    semantico = json.loads(sections["SEMANTICO"])
    assert semantico["success"] is False and semantico["error_count"] == 6
    declaracion = semantico["ast"]["children"][-1]["children"][0]
    assert declaracion["children"][1]["attrs"] == {"dtype": "int"}
    assert semantico["recorrido"][0]["accion"] == "inicio"

    tabla = json.loads(sections["TABLA_SIMBOLOS"])
    assert [(s["nombre"], s["tipo"], s["direccion"]) for s in tabla] == [
        ("x", "int", 0), ("y", "int", 1), ("z", "int", 2),
        ("a", "float", 3), ("b", "float", 4), ("c", "float", 5),
    ]

    # El AST de la sección SINTACTICO sigue sin anotaciones
    sintactico = json.loads(sections["SINTACTICO"])
    assert sintactico["ast"]["children"][-1]["children"][0]["children"][1]["attrs"] == {}


def test_cli_fase_sintactica_no_emite_semantico():
    proc = _run_source("main { int x; }", "syntactic")
    sections = _sections(proc.stdout)
    assert sections["SEMANTICO"] == "" and sections["TABLA_SIMBOLOS"] == ""


def test_cli_archivo_inexistente():
    proc = _run_cli("no_existe_123.txt", "lexical")
    assert proc.returncode == 1
    assert "no existe" in proc.stderr


def test_cli_fase_invalida():
    proc = _run_source("main { }", "magia")
    assert proc.returncode == 1
    assert "Fase inválida" in proc.stderr


# ─── Anidamiento profundo (auditoría) ────────────────────────────────────────

def _parentesis(n: int) -> str:
    return "main { int i; i = " + "(" * n + "1" + ")" * n + "; }"


def test_anidamiento_excesivo_es_un_error_y_no_truena():
    r = compile_source(_parentesis(5000), "semantic")
    [error] = r.errores[SINTACTICO]
    assert "anidadas demasiado profundas" in error.mensaje
    assert any("corrige primero los errores sintácticos" in a for a in r.avisos)


def test_cli_soporta_anidamiento_razonable():
    # La CLI sube el límite de recursión: 300 paréntesis y 800 términos se analizan bien
    for src in [_parentesis(300), "main { int i; i = " + " + ".join(["1"] * 800) + "; }"]:
        proc = _run_source(src, "semantic")
        assert proc.returncode == 0, proc.stderr[-300:]
        errores = json.loads(_sections(proc.stdout)["ERRORES"])
        assert errores["sintactico"] == [] and errores["semantico"] == []


def test_cli_anidamiento_excesivo():
    proc = _run_source(_parentesis(5000), "semantic")
    assert proc.returncode == 0
    errores = json.loads(_sections(proc.stdout)["ERRORES"])
    assert "anidadas demasiado profundas" in errores["sintactico"][0]["mensaje"]
