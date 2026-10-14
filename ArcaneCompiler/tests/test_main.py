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


def test_cli_archivo_inexistente():
    proc = _run_cli("no_existe_123.txt", "lexical")
    assert proc.returncode == 1
    assert "no existe" in proc.stderr


def test_cli_fase_invalida():
    proc = _run_source("main { }", "magia")
    assert proc.returncode == 1
    assert "Fase inválida" in proc.stderr
