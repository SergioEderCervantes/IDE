# Gramática del lenguaje Arcane

Gramática vigente del compilador (analizador sintáctico de `ArcaneCompiler`) y reglas
semánticas asociadas a cada producción. Es la referencia para la fase 3 (análisis
semántico) y para su documento técnico.

---

## 1. Notación

| Símbolo | Significado |
|---|---|
| `→` | Se define como |
| `\|` | Alternativa |
| `{ X }` | X se repite cero o más veces |
| `[ X ]` | X es opcional |
| `'main'`, `';'` | Terminal (lexema literal) |
| `IDENTIFIER`, `INTEGER`, `REAL`, `STRING_LITERAL` | Terminal (clase de token del analizador léxico) |
| `minúsculas` | No terminal |

Alias léxicos: `and` ≡ `&&`, `or` ≡ `||`, `not` ≡ `!`. Los comentarios (`// …` y `/* … */`)
los descarta el analizador sintáctico.

---

## 2. Gramática (EBNF)

```
programa           → 'main' [ '(' ')' ] '{' lista_declaracion '}'

lista_declaracion  → { declaracion }
declaracion        → declaracion_variable
                   | sentencia

declaracion_variable → tipo id_list ';'
tipo               → 'int' | 'float' | 'bool'
id_list            → IDENTIFIER { ',' IDENTIFIER }

lista_sentencias   → { sentencia }
sentencia          → seleccion
                   | iteracion
                   | repeticion
                   | sent_in
                   | sent_out
                   | asignacion
                   | incremento

asignacion         → IDENTIFIER '=' sent_expresion
sent_expresion     → expresion ';'
                   | ';'
incremento         → IDENTIFIER ( '++' | '--' ) ';'

seleccion          → 'if' expresion 'then' lista_sentencias
                     [ 'else' lista_sentencias ] 'end' [ ';' ]
iteracion          → 'while' expresion cuerpo_while [ ';' ]
cuerpo_while       → '{' lista_sentencias '}'
                   | lista_sentencias 'end'
repeticion         → 'do' cuerpo_do 'until' expresion [ ';' ]
cuerpo_do          → '{' lista_sentencias '}'
                   | lista_sentencias

sent_in            → 'cin' '>>' IDENTIFIER ';'
sent_out           → 'cout' '<<' salida ';'
salida             → STRING_LITERAL [ '<<' expresion ]
                   | expresion [ '<<' STRING_LITERAL ]

expresion          → conjuncion { '||' conjuncion }
conjuncion         → comparacion { '&&' comparacion }
comparacion        → expresion_simple [ rel_op expresion_simple ]
rel_op             → '<' | '<=' | '>' | '>=' | '==' | '!='
expresion_simple   → termino { suma_op termino }
suma_op            → '+' | '-'
termino            → unario { mult_op unario }
mult_op            → '*' | '/' | '%'
unario             → '-' unario
                   | factor
factor             → componente { '^' unario }
componente         → '(' expresion ')'
                   | INTEGER | REAL
                   | 'true' | 'false'
                   | IDENTIFIER
                   | '!' componente
```

---

## 3. Precedencia y asociatividad

De menor a mayor precedencia:

| Nivel | Operadores | Asociatividad | Producción |
|---|---|---|---|
| 1 | `\|\|` | Izquierda | `expresion` |
| 2 | `&&` | Izquierda | `conjuncion` |
| 3 | `< <= > >= == !=` | No asociativos (máximo uno por comparación) | `comparacion` |
| 4 | `+ -` | Izquierda | `expresion_simple` |
| 5 | `* / %` | Izquierda | `termino` |
| 6 | `-` unario | Derecha (prefijo) | `unario` |
| 7 | `^` | Derecha | `factor` |
| 8 | `!`, `( )` | Prefijo / agrupación | `componente` |

Ejemplos: `a || b && c` = `a || (b && c)`; `2 ^ 3 ^ 2` = `2 ^ (3 ^ 2)` = 512;
`-2 ^ 2` = `-(2 ^ 2)` = -4; `2 ^ -1` es válido.

---

## 4. Notas de diseño

- **Decisiones LL(1).** Cada alternativa se elige con el token actual, con una excepción:
  en `sentencia`, si el token es `IDENTIFIER` se mira el siguiente (`++`/`--` →
  `incremento`; cualquier otro → `asignacion`).
- **`do … until` en lugar de `do … while`.** Con `do lista_sentencias while expresion` el
  token `while` pertenece a la vez a FIRST(sentencia) y a FOLLOW(lista_sentencias), lo que
  es un conflicto FIRST/FOLLOW: un `while` dentro del cuerpo no se podría distinguir del
  cierre del `do`. `until` es un terminador único. `do … until c` repite **mientras `c` sea
  falsa** (como `repeat … until` en TINY).
- **Paréntesis en condiciones.** No hay una regla especial: `while (x > 7)` funciona porque
  `( expresion )` es un `componente`. Por eso `while (a) && (b)` también es válido.
- **Cuerpos con llaves.** `while` y `do` aceptan `{ … }` o la forma con palabra clave. La
  decisión es LL(1): si el token es `{`, el cuerpo va entre llaves.
- **`++` y `--` solo como sentencia** (`x++;`), al estilo de Go o C0. Dentro de una expresión
  (`y = x++;`) se reporta un error sintáctico específico.
- **`;` opcional** después de `end`, `}` y la condición de `until`.
- **Un solo ámbito.** Las declaraciones solo pueden ir en `lista_declaracion` (nivel de
  `main`), no dentro de `if`/`while`/`do`, que contienen `lista_sentencias`.

---

## 5. Del árbol concreto (CST) al AST

El analizador sintáctico produce un CST (un nodo por regla) y `ast_builder.build_ast` lo
convierte en el AST que usa el análisis semántico:

| Nodo del AST | Hijos |
|---|---|
| `programa` | `[KW_MAIN, lista_declaracion]` |
| `declaracion_variable` | `[tipo, id_list[IDENTIFIER…]]` (siempre con `id_list`) |
| `asignacion` | `[IDENTIFIER, expresión]` (sin expresión si es `x = ;`) |
| `incremento` | `[IDENTIFIER, OP_INCREMENT \| OP_DECREMENT]` |
| `seleccion` | `[condición, lista_sentencias, else_body[lista_sentencias]?]` |
| `iteracion` | `[condición, lista_sentencias]` |
| `repeticion` | `[lista_sentencias, condición]` |
| `sent_in` | `[IDENTIFIER]` |
| `sent_out` | `[salida[STRING_LITERAL? , expresión?]]` |
| Operador binario | `OP_PLUS(izq, der)`, `OP_LT(izq, der)`, `OP_AND(izq, der)`, … |
| Operador unario | `OP_NOT(x)`, `OP_NEG(x)` (menos unario) |
| Hojas | `IDENTIFIER`, `INTEGER`, `REAL`, `KW_TRUE`, `KW_FALSE`, `STRING_LITERAL` |

Las cadenas `operando op operando op …` de las producciones con `{ }` se convierten en
árboles binarios con la asociatividad de la sección 3. Los paréntesis desaparecen (la
estructura del árbol ya expresa la agrupación).

---

## 6. Atributos

| Atributo | Tipo | Dónde se usa | Cálculo |
|---|---|---|---|
| `dtype` | **Heredado** | `id_list` e `IDENTIFIER` de una declaración | Baja desde `tipo` hacia cada identificador declarado |
| `tipo` | **Sintetizado** | Expresiones, literales, identificadores | Sube desde las hojas: literal → su tipo; identificador → tipo de la tabla de símbolos; operador → regla de la sección 8 |
| `valor` | **Sintetizado** | Expresiones constantes | Se calcula solo si todos los operandos tienen valor conocido (literales). Los identificadores **no** tienen valor en compilación |
| `dir` | Asignado al declarar | `IDENTIFIER` declarado / tabla de símbolos | Contador secuencial `memloc` = 0, 1, 2… en orden de declaración (como TINY) |

Tipos posibles: `int`, `float`, `bool` y el tipo interno `error`, que se asigna a una
expresión con error para no reportar errores en cascada.

---

## 7. Reglas semánticas por producción

Las reglas se aplican durante un recorrido del AST. `lookup(id)` busca en la tabla de
símbolos e `insert(id, tipo, dir, línea)` inserta. Los números `#n` corresponden a la
lista de errores de la sección 9.

| Producción | Regla semántica |
|---|---|
| `programa → main { lista_declaracion }` | Tabla de símbolos vacía; `memloc = 0`. Se recorren las declaraciones y sentencias en orden |
| `declaracion_variable → tipo id_list ;` | `id_list.dtype = tipo.tipo` (heredado) |
| `tipo → int \| float \| bool` | `tipo.tipo = int \| float \| bool` |
| `id_list → IDENTIFIER { , IDENTIFIER }` | Para cada identificador: `id.dtype = id_list.dtype`. Si `lookup(id)` existe → **#2** (duplicado). Si no, `insert(id, id.dtype, memloc, línea)` y `memloc = memloc + 1` |
| `asignacion → IDENTIFIER = expresion ;` | `t = lookup(id)` (si no existe → **#1**). Se compara `t` con `expresion.tipo` (sección 8, asignación). Si es `float ← int` se inserta `CONV int→float` sobre la expresión |
| `asignacion → IDENTIFIER = ;` | Error: asignación sin expresión |
| `incremento → IDENTIFIER (++ \| --) ;` | `t = lookup(id)` (**#1**). `t` debe ser `int` o `float`; si es `bool` → **#5**. `incremento.tipo = t` |
| `seleccion → if expresion then …` | `expresion.tipo` debe ser `bool` → si no, **#7** |
| `iteracion → while expresion …` | `expresion.tipo` debe ser `bool` → si no, **#7** |
| `repeticion → do … until expresion` | `expresion.tipo` debe ser `bool` → si no, **#7** |
| `sent_in → cin >> IDENTIFIER ;` | `lookup(id)` debe existir → si no, **#1** |
| `sent_out → cout << salida ;` | Cada expresión de `salida` debe tener un tipo válido; las cadenas no se verifican |
| `componente → INTEGER \| REAL` | `tipo = int \| float`; `valor` = el número |
| `componente → true \| false` | `tipo = bool`; `valor` = verdadero / falso |
| `componente → IDENTIFIER` | `tipo = lookup(id).tipo` (si no existe → **#1** y `tipo = error`); se registra la línea como referencia. Sin `valor` |
| `componente → ( expresion )` | `tipo` y `valor` de la expresión |
| `componente → ! componente` | Operando `bool` → `tipo = bool`; si no, **#5** |
| `unario → - unario` | Operando `int`/`float` → mismo tipo; `bool` → **#5** |
| `factor`, `termino`, `expresion_simple`, `comparacion`, `conjuncion`, `expresion` | Por cada operador binario del AST: regla de la sección 8; `valor` si ambos operandos lo tienen |

Cada uso de un identificador no declarado se reporta (una vez por aparición). Un error no
detiene el recorrido.

---

## 8. Reglas de tipos

**Conversión permitida:** solo `int → float` (ampliación, sin pérdida). Se representa en el
AST anotado con un nodo explícito `CONV int→float` sobre el operando convertido.
`float → int` (reducción, pierde decimales) **no** es implícita.

| Operación | Operandos | Resultado | Error |
|---|---|---|---|
| `+ - * /` | `int, int` | `int` | — |
| `+ - * /` | `float` con `int`/`float` | `float` (el `int` lleva `CONV`) | — |
| `+ - * /` | algún `bool` | `error` | **#5** |
| `/` | `int, int` | `int`, división **truncada** como en C (`1 / 3` = 0) | divisor constante 0 → división entre cero |
| `%` | `int, int` | `int` | `float` o `bool` → **#5**; divisor constante 0 → división entre cero |
| `^` | `int, int` / algún `float` | `int` / `float` | algún `bool` → **#5** |
| `-` unario | `int` / `float` | mismo tipo | `bool` → **#5** |
| `< <= > >=` | dos números (con `CONV` si se mezclan) | `bool` | algún `bool` → **#5** |
| `== !=` | dos números, o dos `bool` | `bool` | número con `bool` → **#3** |
| `&& \|\|` | `bool, bool` | `bool` | algún número → **#5** |
| `!` | `bool` | `bool` | número → **#5** |
| Asignación `x = e` | mismo tipo | — | — |
| Asignación | `float ← int` | — (se agrega `CONV`) | — |
| Asignación | `int ← float` | — | **#4** conversión no válida |
| Asignación | `bool ←` número, o número `← bool` | — | **#3** / **#6** |

Si un operando ya tiene tipo `error`, el resultado es `error` sin reportar un nuevo error.

---

## 9. Errores semánticos

| # | Error (sección 8 del PDF de la fase 3) | Ejemplo |
|---|---|---|
| 1 | Uso de un identificador no declarado | `suma = 45;` |
| 2 | Declaración duplicada en el ámbito | `int x; float x;` |
| 3 | Incompatibilidad de tipos | `activo == 5` (con `activo` bool) |
| 4 | Conversión de tipos no válida | `x = 32.32;` (con `x` int) |
| 5 | Uso indebido de un operador según el tipo de sus operandos | `activo + 1`, `a % 2.0`, `!x` (con `x` int) |
| 6 | Inconsistencia de tipos en asignaciones y expresiones | `activo = 3;` |
| 7 | Condición no booleana | `if x then …` (con `x` int) |
| — | División entre cero con divisor constante | `x = 5 / 0;` |
| — | Asignación sin expresión | `x = ;` |

Cada error se reporta con línea, columna y una descripción.

---

## 10. Cambios respecto a la gramática original

| Cambio | Motivo |
|---|---|
| `repeticion`: `do … while expresion` → `do … until expresion` | Conflicto FIRST/FOLLOW con `while` (sección 4) |
| Cuerpos `{ … }` en `while`/`do` como regla única `cuerpo` | Compatibilidad con programas que usan llaves, sin duplicar reglas |
| Se elimina el manejo especial de paréntesis en condiciones | Los paréntesis ya son agrupación normal; el manejo especial cortaba `(a) && (b)` y aceptaba `(` sin cerrar |
| `expresion` se separa en `expresion` (`\|\|`) y `conjuncion` (`&&`) | `&&` debe tener mayor precedencia que `\|\|` |
| `^` asocia a la derecha | Convención matemática: `2 ^ 3 ^ 2` = 512 |
| `suma_op` ya no incluye `++`/`--` | `a ++ b` no tiene significado; el incremento es la sentencia `incremento` |
| Nueva producción `unario → - unario` | Permitir números negativos (`-5`, `-x`, `2 ^ -1`) |
