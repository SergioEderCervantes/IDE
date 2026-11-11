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
| 4. Código intermedio | Terminada | Código de tres direcciones, igual al del TINY de la materia |
| 5. Ejecución | Pendiente | |

## Estructura

```
IDE/
├── .venv/                   entorno virtual compartido por los dos paquetes
├── GRAMATICA.md             gramática, reglas semánticas y esquema del código intermedio
├── PENDIENTES.md            fallas conocidas y limpieza pospuesta
├── ArcaneCompiler/
│   ├── src/arcane_compiler/
│   │   ├── main.py          línea de comandos y orden de las fases
│   │   ├── lexer/           análisis léxico (autómata, carácter por carácter)
│   │   ├── parser/          análisis sintáctico (descenso recursivo) y construcción del AST
│   │   ├── semantic/        análisis semántico, tipos y tabla de símbolos
│   │   ├── intermediate/    código de tres direcciones
│   │   └── utils/           formato de la salida
│   └── tests/               pruebas (pytest); samples/ tiene los programas de ejemplo
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
| F8 | Código intermedio |
| F9 | Ejecución (pendiente) |

Cada fase corre también las anteriores, y el IDE guarda el archivo antes de compilar. Los
resultados salen en las pestañas Tokens, Sintáctico, Semántico, Código Intermedio, Tabla de
Símbolos, Errores y Ejecución. Los errores además se subrayan en el editor y su mensaje
aparece al pasar el mouse.

## Usar el compilador desde la terminal

```bash
.venv/Scripts/python -m arcane_compiler.main <archivo> <fase>
```

Con el entorno activado también funciona `arcane-compiler <archivo> <fase>`. Las fases son
`lexical`, `syntactic`, `semantic`, `intermediate`, `execution` y `all`. Por ejemplo:

```bash
.venv/Scripts/python -m arcane_compiler.main ArcaneCompiler/tests/samples/tiny/factorial.txt intermediate
```

La salida siempre trae siete secciones, en este orden, cada una entre `===NOMBRE===` y
`===END_NOMBRE===`:

| Sección | Contenido |
|---|---|
| `LEXICO` | Tabla de tokens |
| `SINTACTICO` | AST en JSON |
| `SEMANTICO` | AST anotado y recorrido del análisis, en JSON |
| `CODIGO_INTERMEDIO` | Código de tres direcciones, en el formato `.ci` de TINY |
| `TABLA_SIMBOLOS` | Variables con tipo, dirección y líneas donde aparecen, en JSON |
| `ERRORES` | Errores de cada fase y avisos, en JSON |
| `EJECUCION` | Vacía mientras la fase 5 esté pendiente |

Una fase solo corre si la anterior no tuvo errores. Si no corrió, su sección queda vacía y
un aviso en `ERRORES` explica por qué. El compilador termina con código 0 aunque el programa
tenga errores; solo devuelve 1 si se le llama mal.

## Pruebas

```bash
.venv/Scripts/python -m pytest ArcaneCompiler/tests/ -q
```

`tests/samples/tiny/` tiene los programas del TINY de la materia escritos en nuestro
lenguaje. Cada `.ci` es la salida del `tiny.exe` de la maestra, y nuestro código intermedio
debe ser igual línea por línea.

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

La gramática completa, las reglas de tipos, los errores semánticos y el esquema del código
intermedio están en [GRAMATICA.md](GRAMATICA.md).
