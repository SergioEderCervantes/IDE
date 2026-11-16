"""Entrega final: código para la máquina TM y su ejecución en el simulador de la materia.

- Los ejemplos de samples/tiny/ deben dar el mismo .tm que el tiny.exe de la maestra
  (samples/tiny/esperado/*.tm), línea por línea. Solo cambia el comentario "* File:".
- El resto de las pruebas ejecutan el .tm en el simulador real (TM/tm.c, el de la materia
  extendido para reales) y revisan lo que imprime OUT. Si no hay tm.exe (ni gcc para
  compilarlo), se saltan.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from arcane_compiler.errors import GENERACION, SEMANTICO
from arcane_compiler.main import compile_source, escribir_salidas, ruta_salida
from arcane_compiler.tm.code import IADDR_SIZE

_TESTS = Path(__file__).parent
_TINY = _TESTS / "samples" / "tiny"
_EJERCICIOS = _TESTS / "samples" / "ejercicios"
_TM_DIR = _TESTS.parent.parent / "TM"
_SRC_DIR = _TESTS.parent / "src"


@pytest.fixture(scope="session")
def tm_exe(tmp_path_factory) -> str:
    """El simulador: TM/tm.exe en Windows; en otro sistema se compila TM/tm.c con gcc."""
    if sys.platform == "win32" and (_TM_DIR / "tm.exe").is_file():
        return str(_TM_DIR / "tm.exe")
    gcc = shutil.which("gcc")
    if gcc is None:
        pytest.skip("no hay simulador TM: falta TM/tm.exe y gcc para compilar TM/tm.c")
    destino = tmp_path_factory.mktemp("tm") / "tm"
    subprocess.run([gcc, "-O2", "-o", str(destino), str(_TM_DIR / "tm.c"), "-lm"], check=True)
    return str(destino)


def _tm(fuente: str):
    r = compile_source(fuente, "execution", "prueba.tm")
    assert r.tm is not None, (r.errores, r.avisos)
    return r.tm


def _correr(tm_exe: str, tmp_path: Path, fuente: str, entradas=()) -> str:
    """Compila, carga el .tm en el simulador, lo ejecuta con g y devuelve la consola."""
    archivo = tmp_path / "prueba.tm"
    archivo.write_text(_tm(fuente).texto(), encoding="utf-8")
    teclado = "g\n" + "".join(f"{x}\n" for x in entradas) + "q\n"
    proc = subprocess.run([tm_exe, str(archivo)], input=teclado, capture_output=True,
                          text=True, timeout=20)
    return proc.stdout


def _numero(texto: str) -> int | float:
    return float(texto) if any(c in texto for c in ".e") else int(texto)


def _salidas(consola: str) -> list:
    """Lo que imprimió OUT: int si salió sin decimales, float si no."""
    assert "Ejecucion finalizada (HALT)" in consola, consola
    return [_numero(n) for n in re.findall(r"Resultado del programa \(OUT\): (\S+)", consola)]


def _ejecutar(tm_exe, tmp_path, fuente: str, entradas=()) -> list:
    return _salidas(_correr(tm_exe, tmp_path, fuente, entradas))


# ─── Igual al tiny.exe de la materia ─────────────────────────────────────────

def _sin_archivo(texto: str) -> list[str]:
    return [l for l in texto.splitlines() if not l.startswith("* File:")]


@pytest.mark.parametrize("nombre", ["aritmetica", "ciclo", "condicional", "factorial", "anidado"])
def test_igual_al_tiny_de_la_materia(nombre):
    fuente = (_TINY / f"{nombre}.txt").read_text(encoding="utf-8")
    esperado = (_TINY / "esperado" / f"{nombre}.tm").read_text(encoding="utf-8")
    assert _sin_archivo(_tm(fuente).texto()) == _sin_archivo(esperado)


def test_factorial_paso_a_paso():
    """Las direcciones 16 a 21 son fact = fact * x, el ejemplo del PDF de la entrega."""
    tm = _tm((_TINY / "factorial.txt").read_text(encoding="utf-8"))
    assert len(tm.instrucciones) == 42
    cuerpo = [(i.direccion, i.op, i.operandos()) for i in tm.instrucciones[16:22]]
    assert cuerpo == [
        (16, "LD", "0,1(5)"), (17, "ST", "0,0(6)"), (18, "LD", "0,0(5)"),
        (19, "LD", "1,0(6)"), (20, "MUL", "0,1,0"), (21, "ST", "0,1(5)"),
    ]


def test_encabezado_y_fin():
    lineas = _tm("main { int x; }").texto().splitlines()
    assert lineas[:6] == [
        "* TINY Compilation to TM Code",
        "* File: prueba.tm",
        "* Standard prelude:",
        "  0:     LD  6,0(0) \tload maxaddress from location 0",
        "  1:     ST  0,0(0) \tclear location 0",
        "* End of standard prelude.",
    ]
    assert lineas[-2:] == ["* End of execution.", "  2:   HALT  0,0,0 \t"]


def test_saltos_hacia_adelante_se_escriben_despues_con_su_direccion():
    """Como en TINY: el JEQ del if se completa al terminar el then (emit_backup)."""
    tm = _tm("main { int x; cin >> x; if x < 3 then cout << 1; end }")
    lineas = [l for l in tm.texto().splitlines() if not l.startswith("*")]
    direcciones = [int(l.split(":")[0]) for l in lineas]
    assert direcciones != sorted(direcciones)
    assert sorted(direcciones) == list(range(len(direcciones)))
    assert [i.direccion for i in tm.instrucciones] == list(range(len(direcciones)))


# ─── Ejecución en el simulador ───────────────────────────────────────────────

@pytest.mark.parametrize("nombre, entradas, esperado", [
    ("factorial", [5], [120]),
    ("factorial", [0], []),
    ("aritmetica", [5], [18]),
    ("condicional", [2], [1]),
    ("condicional", [7], [2]),
    ("ciclo", [3], [0]),
    ("anidado", [3], [99, 99, 1]),
])
def test_ejemplos_de_tiny_en_la_tm(tm_exe, tmp_path, nombre, entradas, esperado):
    fuente = (_TINY / f"{nombre}.txt").read_text(encoding="utf-8")
    assert _ejecutar(tm_exe, tmp_path, fuente, entradas) == esperado


def _div(a: int, b: int) -> int:
    """División entera de C (trunca hacia cero)."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


_OPERACIONES = {
    "a + b": lambda a, b: a + b,
    "a - b": lambda a, b: a - b,
    "a * b": lambda a, b: a * b,
    "a / b": _div,
    "a % b": lambda a, b: a - _div(a, b) * b,
    "a ^ 3": lambda a, b: a ** 3,
    "b ^ 0": lambda a, b: 1,
    "-a": lambda a, b: -a,
    "-(a - b)": lambda a, b: b - a,
    "a < b": lambda a, b: int(a < b),
    "a <= b": lambda a, b: int(a <= b),
    "a > b": lambda a, b: int(a > b),
    "a >= b": lambda a, b: int(a >= b),
    "a == b": lambda a, b: int(a == b),
    "a != b": lambda a, b: int(a != b),
    "a > 0 && b > 0": lambda a, b: int(a > 0 and b > 0),
    "a > 0 || b > 0": lambda a, b: int(a > 0 or b > 0),
    "!(a < b)": lambda a, b: int(not a < b),
    "true && !false": lambda a, b: 1,
    "a - b - 1 + a * b % 5": lambda a, b: a - b - 1 + (a * b) - _div(a * b, 5) * 5,
}


@pytest.mark.parametrize("a, b", [(7, 3), (-7, 3), (7, -3), (2, 10), (5, 5), (0, 4)])
def test_operadores(tm_exe, tmp_path, a, b):
    expresiones = list(_OPERACIONES)
    fuente = "main {\n int a, b;\n cin >> a;\n cin >> b;\n" + "".join(
        f" cout << {e};\n" for e in expresiones) + "}"
    esperado = [_OPERACIONES[e](a, b) for e in expresiones]
    assert _ejecutar(tm_exe, tmp_path, fuente, [a, b]) == esperado


def test_while_incremento_y_decremento(tm_exe, tmp_path):
    fuente = """main {
      int i, s, k;
      cin >> i;
      s = 0;
      k = 10;
      while i > 0 {
        s = s + i;
        i--;
        k++;
      }
      cout << s;
      cout << k;
      cout << i;
    }"""
    assert _ejecutar(tm_exe, tmp_path, fuente, [4]) == [10, 14, 0]
    assert _ejecutar(tm_exe, tmp_path, fuente, [0]) == [0, 10, 0]


def test_do_until_y_if_anidados(tm_exe, tmp_path):
    fuente = """main {
      int n, pares, impares;
      cin >> n;
      pares = 0;
      impares = 0;
      do {
        if n % 2 == 0 then pares++; else impares++; end
        n--;
      } until n == 0;
      cout << pares;
      cout << impares;
    }"""
    assert _ejecutar(tm_exe, tmp_path, fuente, [5]) == [2, 3]


def test_variables_bool(tm_exe, tmp_path):
    fuente = """main {
      bool b, c;
      int x;
      cin >> x;
      b = x > 3;
      c = !b || x == 0;
      if b && !c then cout << 1; else cout << 0; end
      cout << b;
      cout << c;
    }"""
    assert _ejecutar(tm_exe, tmp_path, fuente, [5]) == [1, 1, 0]
    assert _ejecutar(tm_exe, tmp_path, fuente, [0]) == [0, 0, 1]


def test_expresion_profunda_usa_varios_temporales(tm_exe, tmp_path):
    fuente = "main { int a; cin >> a; cout << a + (a * (a - (a + (a * 2)))); }"
    a = 3
    assert _ejecutar(tm_exe, tmp_path, fuente, [a]) == [a + (a * (a - (a + (a * 2))))]


def test_division_entre_cero_la_detecta_la_tm(tm_exe, tmp_path):
    fuente = "main { int a, b; cin >> a; cin >> b; cout << a / b; }"
    consola = _correr(tm_exe, tmp_path, fuente, [4, 0])
    assert "Error: division entre cero" in consola
    assert "Resultado del programa" not in consola


def test_residuo_entre_cero_tambien(tm_exe, tmp_path):
    consola = _correr(tm_exe, tmp_path, "main { int a, b; cin >> a; cin >> b; cout << a % b; }", [4, 0])
    assert "Error: division entre cero" in consola


def test_exponente_negativo_da_1(tm_exe, tmp_path):
    """Limitación documentada: el ciclo de ^ no se ejecuta con exponente <= 0."""
    assert _ejecutar(tm_exe, tmp_path, "main { int a, b; cin >> a; cin >> b; cout << a ^ b; }", [2, -1]) == [1]


# ─── Ejercicios del PDF de la entrega final ──────────────────────────────────

@pytest.mark.parametrize("nombre, entradas, esperado", [
    ("inverso", [1, 2, 3, 4], [4, 3, 2, 1]),
    ("segundos", [2], [172800]),
    ("expresion", [2, 3], [8]),
    ("signo", [15], [0]),
    ("signo", [-4], [1]),
    ("signo", [0], [2]),
    ("creciente", [1, 5, 9], [1]),
    ("creciente", [1, 9, 5], [0]),
    ("desigualdad", [2, 3], [1]),
    ("desigualdad", [5, 5], [0]),
    ("fibonacci", [1], [0]),
    ("fibonacci", [2], [1]),
    ("fibonacci", [10], [34]),
    ("ulam", [26], [26, 13, 40, 20, 10, 5, 16, 8, 4, 2, 1]),
    ("primos", [20], [2, 3, 5, 7, 11, 13, 17, 19, 8]),
    ("perfectos", [30], [6, 28]),
    ("serie_potencias", [4], [288]),
    ("votos", [1, 3, 1, 4, 2, 2, 1, 4, 1, 1, 1, 2, 1, 3, 1, 4, 0], [8, 50, 3, 18, 2, 12, 3, 18]),
    ("votos", [0], []),
    ("ceros", [3, 0, 5, 0, 0, -2, -1], [3]),
    ("mayor_menor", [5, 4, -2, 9, 0, 7], [9, -2]),
    # con reales
    ("promedio", [12345, 8, 9.5, 10, 7, 8.5], [12345, 8.6]),
    ("cilindro", [3, 2], [2 * 3.1416 * 3 * 2, 3.1416 * 3 ** 2 * 2]),
    ("dinosaurio", [1000, 20], [453.6, 6.096]),
    ("sueldo", [800], [920]),
    ("sueldo", [1500], [1680]),
    ("impuesto", [15], [15]),
    ("impuesto", [30], [33]),
    ("impuesto", [100], [130]),
    ("impuesto", [600], [886]),
    ("mayor_reales", [1.5, 7.25, 3], [7.25]),
    ("mayor_reales", [-2.5, -2.5, -9], [-2.5]),
    ("serie_alternada", [4], [1 - 1 / 2 + 1 / 3 - 1 / 4]),
])
def test_ejercicios(tm_exe, tmp_path, nombre, entradas, esperado):
    fuente = (_EJERCICIOS / f"{nombre}.txt").read_text(encoding="utf-8")
    assert _ejecutar(tm_exe, tmp_path, fuente, entradas) == pytest.approx(esperado, rel=1e-9)


# ─── Reales (extensión de TM/tm.c) ───────────────────────────────────────────

def test_operaciones_con_reales(tm_exe, tmp_path):
    fuente = """main {
      float a, b;
      int n;
      cin >> a;
      cin >> b;
      cin >> n;
      cout << a + b;
      cout << a - b;
      cout << a * b;
      cout << a / b;
      cout << -a;
      cout << a < b;
      cout << a >= b;
      cout << a ^ 2;
      cout << b ^ -2;
      cout << n / 2;
      cout << n / 2.0;
      cout << n + a;
      cout << n * 0.1;
    }"""
    a, b, n = 7.5, 2, 7
    esperado = [a + b, a - b, a * b, a / b, -a, int(a < b), int(a >= b), a ** 2, b ** -2,
                n // 2, n / 2, n + a, n * 0.1]
    assert _ejecutar(tm_exe, tmp_path, fuente, [a, b, n]) == pytest.approx(esperado)


def test_float_con_valor_entero_se_imprime_sin_decimales(tm_exe, tmp_path):
    fuente = "main { float x; x = 3; cout << x; x = 0.5 * 4; cout << x; cout << 0.0 - 0; }"
    consola = _correr(tm_exe, tmp_path, fuente)
    assert re.findall(r"\(OUT\): (\S+)", consola) == ["3", "2", "0"]


def test_incremento_de_float(tm_exe, tmp_path):
    fuente = "main { float x; cin >> x; x++; cout << x; x--; x--; cout << x; }"
    assert _ejecutar(tm_exe, tmp_path, fuente, [1.25]) == pytest.approx([2.25, 0.25])


def test_cin_de_float_usa_inr(tm_exe, tmp_path):
    tm = _tm("main { float x; int n; cin >> x; cin >> n; }")
    ops = [i.op for i in tm.instrucciones]
    assert ops.count("INR") == 1 and ops.count("IN") == 1
    consola = _correr(tm_exe, tmp_path, "main { float x; cin >> x; cout << x; }", [2.75])
    assert "Ingrese un numero real (INR): " in consola
    assert _salidas(consola) == [2.75]


def test_cin_de_int_no_acepta_decimales(tm_exe, tmp_path):
    """IN vuelve a preguntar si el dato tiene decimales (antes se quedaba con el 2)."""
    consola = _correr(tm_exe, tmp_path, "main { int n; cin >> n; cout << n; }", ["2.5", "abc", 3])
    assert consola.count("Illegal value") == 2
    assert _salidas(consola) == [3]


def test_literal_real_se_carga_con_ldc():
    tm = _tm("main { float x; x = 7.59; x = -0.5; }")
    constantes = [i.operandos() for i in tm.instrucciones if i.op == "LDC"]
    assert constantes == ["0,7.59(0)", "0,-0.5(0)"]


def test_division_real_y_entera():
    tm = _tm("main { int a; float x; a = 7 / 2; x = 7 / 2.0; }")
    divisiones = [i.op for i in tm.instrucciones if i.op.startswith("DIV")]
    assert divisiones == ["DIV", "DIVR"]


def test_programa_de_enteros_no_usa_las_instrucciones_nuevas():
    """Así sigue siendo igual al del tiny.exe de la materia."""
    for nombre in ("factorial", "aritmetica", "anidado"):
        tm = _tm((_TINY / f"{nombre}.txt").read_text(encoding="utf-8"))
        assert not {"INR", "DIVR"} & {i.op for i in tm.instrucciones}


def test_division_real_entre_cero(tm_exe, tmp_path):
    consola = _correr(tm_exe, tmp_path, "main { float x; cin >> x; cout << 1 / x; }", [0])
    assert "Error: division entre cero" in consola


def test_potencia_real_con_exponente_negativo_de_cero(tm_exe, tmp_path):
    """0.0 ^ -1 es dividir entre cero."""
    consola = _correr(tm_exe, tmp_path, "main { float x; cin >> x; cout << x ^ -1; }", [0])
    assert "Error: division entre cero" in consola


# ─── Lo que la TM no puede hacer ─────────────────────────────────────────────

def test_exponente_float_es_un_error_de_generacion():
    r = compile_source("main {\n  float x, y;\n  x = 2.0;\n  y = x ^ x;\n}", "execution")
    assert r.errores[SEMANTICO] == [] and r.tm is None
    assert r.intermedio is not None  # el .ci sí se puede generar
    [error] = r.errores[GENERACION]
    assert (error.linea, error.columna) == (4, 11)
    assert "exponente entero" in error.mensaje
    assert any("no se puede ejecutar" in a for a in r.avisos)


def test_exponente_entero_de_una_base_real_si_se_puede():
    r = compile_source("main { float x; x = 1.5; x = x ^ 3; }", "execution")
    assert r.tm is not None and r.errores[GENERACION] == []


def test_texto_del_cout_se_omite_con_aviso(tm_exe, tmp_path):
    fuente = 'main {\n int x;\n x = 7;\n cout << "x vale " << x;\n cout << x << " fin";\n}'
    r = compile_source(fuente, "execution")
    assert r.tm is not None and r.errores[GENERACION] == []
    assert sum("se omitió el texto" in a for a in r.avisos) == 2
    assert '* cout: se omite el texto "x vale " (OUT solo imprime números)' in r.tm.texto()
    assert _ejecutar(tm_exe, tmp_path, fuente) == [7, 7]


def test_programa_demasiado_grande():
    cuerpo = "".join(f"  x = x + {i};\n" for i in range(IADDR_SIZE // 6 + 1))
    r = compile_source("main {\n int x;\n x = 0;\n" + cuerpo + "}", "intermediate")
    [error] = r.errores[GENERACION]
    assert "instrucciones TM" in error.mensaje and r.tm is None


def test_errores_semanticos_no_generan_tm():
    r = compile_source("main { int x; x = y; }", "execution")
    assert r.tm is None and r.errores[GENERACION] is None


# ─── Archivos .ci y .tm junto al fuente ──────────────────────────────────────

def test_ruta_salida():
    assert ruta_salida(Path("a/prog.txt"), ".tm") == Path("a/prog.tm")
    assert ruta_salida(Path("a/prog"), ".ci") == Path("a/prog.ci")
    # nunca encima del propio programa
    assert ruta_salida(Path("a/prog.tm"), ".tm") == Path("a/prog.tm.tm")
    assert ruta_salida(Path("a/prog.ci"), ".tm") == Path("a/prog.ci.tm")


def test_escribe_ci_y_tm_y_borra_los_viejos(tmp_path):
    fuente = tmp_path / "prog.txt"
    r = compile_source("main { int x; cin >> x; cout << x; }", "execution", "prog.tm")
    assert escribir_salidas(fuente, r) == tmp_path / "prog.tm"
    assert (tmp_path / "prog.tm").read_text(encoding="utf-8") == r.tm.texto()
    assert (tmp_path / "prog.ci").read_text(encoding="utf-8").startswith("# CÓDIGO INTERMEDIO")

    # Una compilación con errores no deja el código de la anterior
    r = compile_source("main { int x; x = y; }", "execution")
    assert escribir_salidas(fuente, r) is None
    assert not (tmp_path / "prog.tm").exists() and not (tmp_path / "prog.ci").exists()


def test_error_de_generacion_deja_el_ci_pero_no_el_tm(tmp_path):
    fuente = tmp_path / "prog.txt"
    (tmp_path / "prog.tm").write_text("viejo", encoding="utf-8")
    r = compile_source("main { float x; x = 1.5; x = x ^ x; }", "execution")
    assert escribir_salidas(fuente, r) is None
    assert (tmp_path / "prog.ci").exists() and not (tmp_path / "prog.tm").exists()


def _cli(ruta: Path, fase: str) -> dict[str, str]:
    env = dict(os.environ, PYTHONPATH=str(_SRC_DIR), PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-m", "arcane_compiler.main", str(ruta), fase],
                          capture_output=True, text=True, encoding="utf-8", env=env)
    assert proc.returncode == 0, proc.stderr
    patron = re.compile(r"===(?P<n>\w+)===\r?\n(?P<c>.*?)===END_(?P=n)===", re.DOTALL)
    return {m.group("n"): m.group("c").strip() for m in patron.finditer(proc.stdout)}


def test_cli_ejecucion_entrega_el_tm_para_el_simulador(tmp_path):
    ruta = tmp_path / "factorial.txt"
    ruta.write_text((_TINY / "factorial.txt").read_text(encoding="utf-8"), encoding="utf-8")
    secciones = _cli(ruta, "execution")
    assert Path(secciones["EJECUCION"]) == (tmp_path / "factorial.tm").resolve()
    assert secciones["CODIGO_TM"].splitlines()[1] == "* File: factorial.tm"
    assert (tmp_path / "factorial.tm").read_text(encoding="utf-8").strip() == secciones["CODIGO_TM"]
    assert (tmp_path / "factorial.ci").exists()


def test_cli_fase_intermedia_escribe_pero_no_pide_ejecutar(tmp_path):
    ruta = tmp_path / "prog.txt"
    ruta.write_text("main { int x; x = 1; }", encoding="utf-8")
    secciones = _cli(ruta, "intermediate")
    assert secciones["EJECUCION"] == "" and secciones["CODIGO_TM"]
    assert (tmp_path / "prog.tm").exists()


def test_cli_fases_de_analisis_no_escriben_archivos(tmp_path):
    ruta = tmp_path / "prog.txt"
    ruta.write_text("main { int x; x = 1; }", encoding="utf-8")
    secciones = _cli(ruta, "semantic")
    assert secciones["CODIGO_TM"] == ""
    assert sorted(p.name for p in tmp_path.iterdir()) == ["prog.txt"]
