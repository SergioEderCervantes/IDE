# ArcaneIDE + ArcaneCompiler

Compilador e IDE para el lenguaje Arcane, proyecto de Compiladores II (UAA), basado en el
compilador TINY de Kenneth C. Louden. El compilador está escrito en Python puro. El IDE usa
PyQt6 y QScintilla, y ejecuta el compilador como un proceso aparte.

## Estado

| Fase | Estado | Qué produce |
|---|---|---|
| 1. Léxico | Terminada | Tabla de tokens |
| 2. Sintáctico | Terminada | Árbol sintáctico (AST) |
| 3. Semántico | Terminada | AST anotado, tabla de símbolos y recorrido del análisis |
| 4. Código intermedio | Terminada | Código de tres direcciones (`.ci`), igual al del TINY de la materia |
| Entrega final | Terminada | Código para la máquina TM (`.tm`), igual al del TINY de la materia, y su ejecución en el simulador TM |

## Estructura

```
IDE/
├── .venv/                   entorno virtual compartido por los dos paquetes
├── GRAMATICA.md             gramática, reglas semánticas, código intermedio y código TM
├── PENDIENTES.md            fallas conocidas y limpieza pospuesta
├── TM/                      simulador TM de la materia (tm.c, extendido para reales) y tm.exe
├── ArcaneCompiler/
│   ├── src/arcane_compiler/
│   │   ├── main.py          línea de comandos y orden de las fases
│   │   ├── lexer/           análisis léxico (autómata, carácter por carácter)
│   │   ├── parser/          análisis sintáctico (descenso recursivo) y construcción del AST
│   │   ├── semantic/        análisis semántico, tipos y tabla de símbolos
│   │   ├── intermediate/    código de tres direcciones (.ci)
│   │   ├── tm/              código para la máquina TM (.tm): cgen.py y code.py
│   │   └── utils/           formato de la salida
│   └── tests/               pruebas (pytest); samples/ tiene los programas de ejemplo
│                            (tiny/: los de la materia; ejercicios/: del PDF de la entrega)
└── ArcaneIDE/src/
    ├── main.py
    ├── core/                ejecuta el compilador y maneja los archivos
    ├── ui/                  ventana, editor y pestañas de resultados
    └── utils/
```

## Instalación

Desde la raíz del repo (`IDE/`), una sola vez:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e "ArcaneCompiler/[dev]"
.venv/Scripts/python -m pip install -e ArcaneIDE/
```

En Linux o macOS cambia `.venv/Scripts/` por `.venv/bin/`. Los dos paquetes van en el mismo
entorno porque el IDE ejecuta el compilador con su mismo Python.

El simulador ya viene compilado en `TM/tm.exe`. Si hace falta volver a compilarlo, corre
`TM/compilar_tm.bat` (necesita el `gcc` de MinGW en el PATH). En Linux, corre
`TM/compilar_tm.sh` (necesita `gcc`): deja el ejecutable en `TM/tm`, que es donde lo busca el IDE.

## Usar el IDE

```bash
cd ArcaneIDE
../.venv/Scripts/python -m src.main
```

Abre un programa, por ejemplo `ArcaneCompiler/tests/samples/tiny/factorial.txt`, y compila
con la barra de herramientas o con las teclas:

| Tecla | Fase |
|---|---|
| F5 | Léxico |
| F6 | Sintáctico |
| F7 | Semántico |
| F8 | Código intermedio: genera el `.ci` y el `.tm` |
| F9 | Ejecutar: genera el `.tm` y lo corre en el simulador TM |

Cada fase corre también las anteriores, y el IDE guarda el archivo antes de compilar. Los
resultados salen en las pestañas:

| Pestaña | Contenido |
|---|---|
| Tokens, Sintáctico, Semántico | Resultado de cada análisis |
| Código Intermedio | El código TM (`.tm`): dirección, instrucción, operandos y comentario de cada instrucción, o el archivo tal cual |
| Código intermedio de tres direcciones | El `.ci` |
| Tabla de Símbolos | Variables con tipo, dirección y líneas donde aparecen |
| Errores | Errores léxicos, sintácticos, semánticos y de generación, y avisos |
| Ejecución | La consola del simulador TM |

Los errores además se subrayan en el editor y su mensaje aparece al pasar el mouse.

**Ejecutar (F9).** El IDE carga el `.tm` en `TM/tm.exe` y lo ejecuta (comando `g`).
- Cuando el programa pide un dato (`Ingrese un numero entero (IN):`), escríbelo en la línea
  de abajo y presiona Enter. Los `Resultado del programa (OUT): …` salen en negritas.
- Al terminar puedes usar los comandos de la TM: `d 0 5` muestra la memoria, `r` los
  registros, `v` el `.ci` y `h` la ayuda.
- «Ejecutar de nuevo» vuelve a correrlo, y «Abrir en consola» abre el mismo simulador en
  una ventana aparte.

La TM de la materia solo manejaba enteros y solo imprimía números. `TM/tm.c` está extendido
para nuestro lenguaje (detalle en GRAMATICA.md §12):
- maneja reales: un `cin` de una variable `float` pide un número real (`INR`) y uno de
  `int` solo acepta enteros;
- imprime texto: `cout << "Total: " << x;` sale como
  `Resultado del programa (OUT): Total: 120`;
- calcula potencias reales (`x ^ 0.5`).

## Usar el compilador desde la terminal

```bash
.venv/Scripts/python -m arcane_compiler.main <archivo> <fase>
```

Con el entorno activado también funciona `arcane-compiler <archivo> <fase>`. Las fases son
`lexical`, `syntactic`, `semantic`, `intermediate`, `execution` y `all`. Por ejemplo:

```bash
.venv/Scripts/python -m arcane_compiler.main ArcaneCompiler/tests/samples/tiny/factorial.txt intermediate
```

Con `intermediate`, `execution` y `all` el compilador escribe también `programa.ci` y
`programa.tm` junto al archivo fuente, como el `tiny.exe` de la materia. Para correr el `.tm`
a mano:

```bash
TM/tm.exe ArcaneCompiler/tests/samples/tiny/factorial.tm
```

La salida siempre trae ocho secciones, en este orden, cada una entre `===NOMBRE===` y
`===END_NOMBRE===`:

| Sección | Contenido |
|---|---|
| `LEXICO` | Tabla de tokens |
| `SINTACTICO` | AST en JSON |
| `SEMANTICO` | AST anotado y recorrido del análisis, en JSON |
| `CODIGO_INTERMEDIO` | Código de tres direcciones, en el formato `.ci` de TINY |
| `CODIGO_TM` | Código para la máquina TM, en el formato `.tm` de TINY |
| `TABLA_SIMBOLOS` | Variables con tipo, dirección y líneas donde aparecen, en JSON |
| `ERRORES` | Errores de cada fase (léxico, sintáctico, semántico, generación) y avisos, en JSON |
| `EJECUCION` | Con la fase `execution`, la ruta del `.tm` que hay que cargar en el simulador |

Una fase solo corre si la anterior no tuvo errores. Si no corrió, su sección queda vacía y
un aviso en `ERRORES` explica por qué. El compilador termina con código 0 aunque el programa
tenga errores; solo devuelve 1 si se le llama mal.

## Pruebas

```bash
.venv/Scripts/python -m pytest ArcaneCompiler/tests/ -q
```

`tests/samples/tiny/` tiene los programas del TINY de la materia escritos en nuestro
lenguaje. En `tiny/esperado/` están el `.ci` y el `.tm` que da el `tiny.exe` de la maestra
para cada uno, y nuestro código debe ser igual línea por línea. `tests/samples/ejercicios/`
tiene ejercicios del PDF de la entrega final. Las pruebas de `test_tm.py` los ejecutan en el
simulador real y revisan los resultados.

## El lenguaje

```
main {
  int x, fact;
  cin >> x;
  if 0 < x then
    fact = 1;
    do
      fact = fact * x;
      x = x - 1;
    until x == 0;
    cout << fact;
  end
}
```

- **Tipos:** `int` (32 bits), `float` y `bool`. Las variables se declaran en el nivel de
  `main`, no dentro de un `if` o de un ciclo.
- **Sentencias:**
  - asignación (`x = expr;`), `x++;` y `x--;`;
  - `if c then … [else …] end`;
  - `while c { … }` (o `while c … end`) y `do … until c;`;
  - `cin >> x;`;
  - `cout << expr;`, `cout << "texto" << expr;` y `cout << expr << "texto";`.
- **Operadores**, de menor a mayor precedencia:
  1. `||`
  2. `&&`
  3. `< <= > >= == !=`
  4. `+ -`
  5. `* / %`
  6. `-` unario
  7. `^`
  8. `!`

  `and`, `or` y `not` equivalen a `&&`, `||` y `!`.
- **Comentarios:** `// …` y `/* … */`.

La gramática completa, las reglas de tipos, los errores semánticos, el esquema del código
intermedio y la correspondencia con las instrucciones TM están en [GRAMATICA.md](GRAMATICA.md).
