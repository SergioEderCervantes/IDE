# Gramática del lenguaje Arcane

Gramática vigente del compilador (analizador sintáctico de `ArcaneCompiler`) y reglas
semánticas asociadas a cada producción. Es la referencia para la fase 3 (análisis
semántico) y para su documento técnico. La sección 11 describe el código intermedio de la
fase 4 y la sección 12, el código para la máquina TM de la entrega final.

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
- **Recuperación de errores (modo pánico).** Cada error de sintaxis se reporta una vez, con
  su línea y columna, y el análisis sigue con el resto del programa:
  - Quien detecta el error no descarta nada. La construcción que lo atrapa descarta tokens
    hasta su propio punto de sincronización: el `if` hasta su `then`, la asignación hasta
    su `;`, el paréntesis hasta su `)`.
  - Un error casi nunca cruza de línea. Si ese punto aparece más adelante en la misma
    línea, todo lo de en medio se toma como basura de esa sentencia, aunque sean palabras
    clave. Si no aparece, el descarte se detiene en el primer token que no puede formar
    parte de una expresión (`;`, `then`, `end`, `{`, una palabra clave…).
  - Un token que no puede iniciar una sentencia (`5;`, un `end` de más) se reporta y se
    descarta hasta el `;` de esa sentencia o hasta donde empieza la siguiente.

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
| `valor` | **Sintetizado** | Expresiones, asignaciones e incrementos | Se calcula si todos los operandos tienen valor conocido. Sube desde las hojas hasta la sentencia: `y = 2 + 3;` anota `valor = 5` en el `+`, en la `asignacion` y en la `y` destino. Un identificador tiene el último valor conocido de la variable (ver abajo) |
| `dir` | Asignado al declarar | `IDENTIFIER` declarado / tabla de símbolos | Contador secuencial `memloc` = 0, 1, 2… en orden de declaración (como TINY) |

Tipos posibles: `int`, `float`, `bool` y el tipo interno `error`, que se asigna a una
expresión con error para no reportar errores en cascada.

**Tamaño de los tipos:**

| Tipo | Representación | Rango |
|---|---|---|
| `int` | Entero de 32 bits con signo (como en C y Java) | −2 147 483 648 a 2 147 483 647 |
| `float` | Real de doble precisión (64 bits, IEEE 754) | ±1.8 × 10³⁰⁸ aprox., 15–16 dígitos significativos |
| `bool` | `true` / `false` | — |

Un literal entero fuera de rango y una expresión constante entera que se desborda son errores
semánticos. Como el lexer lee `-2147483648` como `-` aplicado a `2147483648`, ese literal se
acepta cuando va precedido de un menos unario. Una expresión constante real cuyo resultado no
es finito (se desborda a infinito) no recibe `valor`.

**Valor de las variables.** El analizador recuerda el último valor asignado a cada variable,
así que en `y = 4; y = y + 1;` la `y` de la derecha tiene `valor = 4` y la asignación (y su
destino) `valor = 5`. Solo se guarda un valor cuando es el mismo en cualquier ejecución:

- `cin >> x`, una asignación con error de tipo o con una expresión sin valor dejan a `x` sin valor.
- Después de un `if`, solo conservan su valor las variables que valen lo mismo en ambas ramas
  (sin `else`, la rama que falta es el estado antes del `if`).
- En `while` y `do … until`, las variables asignadas dentro del cuerpo no tienen valor en la
  condición, en el cuerpo ni (en el `while`) después del ciclo, porque cambian en cada vuelta.

Con esto también se detectan errores como `x = 0; y = 5 / x;` (división entre cero).

**Código que nunca se ejecuta.** Si la condición de un `if` o de un `while` tiene un valor
conocido, la parte que nunca se ejecuta (el `then` de una condición siempre falsa, el `else`
de una siempre verdadera o el cuerpo de un `while` siempre falso) se sigue analizando: ahí se
reportan los errores de tipos y los de expresiones formadas solo por literales (`5 / 0`),
pero no los que dependen del valor de una variable. Así, `x = 0; if x != 0 then y = 10 / x; end`
no tiene errores. El error que no se reporta queda en la traza del recorrido (acción
*error omitido*). El cuerpo de `do … until` siempre se ejecuta al menos una vez.

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
| `id_list → IDENTIFIER { , IDENTIFIER }` | Para cada identificador: `id.dtype = id_list.dtype`. Si `lookup(id)` existe → **#2** (duplicado). Si no, `insert(id, id.dtype, memloc, línea)` y `memloc = memloc + 1`; la línea de la declaración es la primera referencia |
| `asignacion → IDENTIFIER = expresion ;` | `t = lookup(id)` (si no existe → **#1**). Se compara `t` con `expresion.tipo` (sección 8, asignación). Si es `float ← int` se inserta `CONV int→float` sobre la expresión. Si no hay error y la expresión tiene `valor`, `asignacion.valor = id.valor = expresion.valor` y la variable lo conserva; si no, la variable queda sin valor |
| `asignacion → IDENTIFIER = ;` | Error: asignación sin expresión |
| `incremento → IDENTIFIER (++ \| --) ;` | `t = lookup(id)` (**#1**). `t` debe ser `int` o `float`; si es `bool` → **#5**. `incremento.tipo = t`; si la variable tiene valor, `incremento.valor = id.valor = valor ± 1` |
| `seleccion → if expresion then …` | `expresion.tipo` debe ser `bool` → si no, **#7** |
| `iteracion → while expresion …` | `expresion.tipo` debe ser `bool` → si no, **#7** |
| `repeticion → do … until expresion` | `expresion.tipo` debe ser `bool` → si no, **#7** |
| `sent_in → cin >> IDENTIFIER ;` | `lookup(id)` debe existir → si no, **#1**. La variable queda sin valor |
| `sent_out → cout << salida ;` | Cada expresión de `salida` debe tener un tipo válido; las cadenas no se verifican |
| `componente → INTEGER \| REAL` | `tipo = int \| float`; `valor` = el número. Fuera del rango del tipo → error (constante fuera de rango) |
| `componente → true \| false` | `tipo = bool`; `valor` = verdadero / falso |
| `componente → IDENTIFIER` | `tipo = lookup(id).tipo` (si no existe → **#1** y `tipo = error`); se registra la línea como referencia, una vez por aparición (`y = y + 1` registra la línea dos veces). `valor` = último valor conocido de la variable, si lo tiene |
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
| `^` | `int, int` / algún `float` | `int` / `float` | algún `bool` → **#5**; `int ^` exponente constante negativo → error; `0.0 ^` exponente negativo → división entre cero |
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

En toda operación entera constante, un resultado fuera del rango de `int` es un error de
desbordamiento (por ejemplo `2147483647 + 1` o `2 ^ 31`).

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
| — | División entre cero con divisor constante | `x = 5 / 0;`, `f = 0.0 ^ -1;` |
| — | Asignación sin expresión | `x = ;` |
| — | Exponente negativo en una potencia entera | `x = 2 ^ -1;` |
| — | Constante fuera de rango | `x = 3000000000;` |
| — | Desbordamiento en expresión constante | `x = 2147483647 + 1;` |

Cada error se reporta con línea, columna y una descripción.

Si un programa tiene expresiones anidadas tan profundas que el análisis no puede procesarlas
(más de ~500 paréntesis anidados o expresiones de más de ~1000 términos), se reporta un error
en lugar de detener el compilador.

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

---

## 11. Código intermedio de tres direcciones (fase 4)

La fase 4 recorre el AST anotado (con sus nodos `CONV`) y produce una lista de cuádruplos
`(op, arg1, arg2, resultado)`. El texto sigue el formato del archivo `.ci` del TINY de la
materia (`Tiny_Intermedio_TM`, `intermedio.c`): un programa de TINY escrito igual en este
lenguaje da el mismo código línea por línea (los `.ci` de referencia están en
`tests/samples/tiny/esperado/`). Solo se genera si el análisis semántico no tuvo errores.

**Instrucciones:**

| Instrucción | Significado |
|---|---|
| `read x` | Lee un valor para `x` (`cin`) |
| `write a` / `write "texto", a` | Escribe (`cout`); un `cout` con dos elementos es una sola instrucción |
| `x = a` | Copia |
| `t1 = a op b` | Operación binaria: `+ - * / % ^ < <= > >= == != && \|\|` |
| `t1 = -a` / `t1 = !a` | Menos unario / negación lógica |
| `t1 = (float) a` | Conversión `int → float` (nodo `CONV`) |
| `if_false a goto L1` | Salta a `L1` si `a` es false |
| `goto L1` / `label L1` | Salto incondicional / etiqueta |
| `halt` | Fin del programa |

Los operandos son variables, temporales (`t1`, `t2`, …), constantes (`5`, `2.50`, `true`)
o cadenas (`"texto"`). Cada cuádruplo guarda además el tipo del resultado y la línea del
código fuente.

**Esquema de traducción** (`c` es el operando donde quedó el valor de la condición):

| Producción | Código |
|---|---|
| `asignacion → IDENTIFIER = expresion` | código de la expresión; `x = r` |
| `incremento → IDENTIFIER ++` (`--`) | `t = x + 1` (`- 1`); `x = t` (`1.0` si `x` es float) |
| `sent_in → cin >> IDENTIFIER` | `read x` |
| `sent_out → cout << salida` | código de la expresión; `write …` |
| `seleccion` sin `else` | `if_false c goto L1` / then / `label L1` |
| `seleccion` con `else` | `if_false c goto L1` / then / `goto L2` / `label L1` / else / `label L2` |
| `iteracion → while c …` | `label L1` / `if_false c goto L2` / cuerpo / `goto L1` / `label L2` |
| `repeticion → do … until c` | `label L1` / cuerpo / `if_false c goto L1` |
| Operador binario / unario / `CONV` | código de los operandos; resultado en un temporal nuevo |
| Literal o identificador | Se usa directamente, sin temporal |
| `declaracion_variable` | No genera código |

**Reglas** (las mismas de TINY, para que la numeración coincida):

- Las expresiones se traducen en postorden (izquierdo, derecho, operación). El temporal se
  numera después de traducir los operandos: `(x + 1) * (x - 2)` da `t1 = x + 1`,
  `t2 = x - 2`, `t3 = t1 * t2`.
- Los temporales y las etiquetas se numeran en todo el programa y no se reutilizan.
- En un `if`, `L1` se numera antes de traducir el then y `L2` después.
- No se usan los valores que calculó el análisis semántico: `x = 2 + 3` da `t1 = 2 + 3`,
  `x = t1`. La única excepción es el menos unario sobre un literal, que se escribe como la
  constante negativa (`x = -5`, y así `-2147483648` es una constante válida).
- `&&` y `||` se evalúan completos (sin cortocircuito), como cualquier operación binaria.
- El código de una rama que nunca se ejecuta (sección 6) se genera igual.

Ejemplo (`tests/samples/tiny/factorial.txt`, idéntico al `factorial.ci` de la materia):

```
main {                              read x
  int x, fact;                      t1 = 0 < x
  cin >> x;                         if_false t1 goto L1
  if 0 < x then                     fact = 1
    fact = 1;                       label L2
    do                              t2 = fact * x
      fact = fact * x;              fact = t2
      x = x - 1;                    t3 = x - 1
    until x == 0;                   x = t3
    cout << fact;                   t4 = x == 0
  end                               if_false t4 goto L2
}                                   write fact
                                    label L1
                                    halt
```

---

## 12. Código para la máquina TM (entrega final)

El generador de código TM recorre el mismo AST anotado que la fase 4. El `.ci` y el `.tm`
salen por caminos paralelos, como en el TINY de la materia, y la TM no lee el `.ci`.
Solo se genera si el análisis semántico no tuvo errores. Los dos módulos tienen el papel de
los archivos de Louden:

| Nuestro módulo | TINY | Qué hace |
|---|---|---|
| `tm/cgen.py` | `cgen.c` | Recorre el árbol y decide qué instrucciones generar (`genStmt`, `genExp`) |
| `tm/code.py` | `code.c`, `code.h` | Registros, formato de cada instrucción y resolución de saltos (`emit_ro`, `emit_rm`, `emit_skip`, `emit_backup`, `emit_restore`, `emit_rm_abs`) |
| Tabla de símbolos | `st_lookup` | Dirección de cada variable (`direccion` = `memloc` de TINY) |

Un programa de TINY escrito igual en este lenguaje da el mismo `.tm` que el `tiny.exe` de
la materia, línea por línea. Solo cambia el comentario `* File:`. Los archivos de
referencia están en `tests/samples/tiny/esperado/`. Las pruebas (`test_tm.py`) también
ejecutan el código en el simulador real y revisan lo que imprime.

**La máquina.** `TM/tm.c` es el simulador de la materia con una extensión para nuestro
lenguaje: reales, texto en la salida y potencia real. La maestra permite adaptar la TM al
compilador. Los cambios están marcados con `EXTENSION` en el código:

| Cambio | Original | Extendido |
|---|---|---|
| Registros y memoria de datos | `int` | `double` |
| `LDC r,d(s)` | `d` entero | `d` puede tener decimales (`LDC 0,7.59(0)`) |
| `IN r` | Lee un entero (aceptaba `2.5` como 2) | Lee un entero; con decimales responde `Illegal value` y vuelve a preguntar |
| `INR r` | (no existe) | Lee un número real: `Ingrese un numero real (INR):` |
| `DIV r,s,t` | División entera | Igual: divide y trunca hacia cero |
| `DIVR r,s,t` | (no existe) | División real |
| `OUT`, comandos `r` y `d` | `%d` | Sin decimales si el valor es entero, con decimales si no |
| `OUTC r` | (no existe) | Escribe el carácter (byte) `reg[r]` en la línea actual; el 10 (`'\n'`) la termina |
| `OUTN r` | (no existe) | Escribe el número `reg[r]` sin terminar la línea |
| `POW r,s,t` | (no existe) | Potencia real `reg[s] ^ reg[t]`. `0 ^ negativo` es división entre cero; sin resultado real (`-4 ^ 0.5`): `Error: potencia sin resultado real` |

`OUTC` y `OUTN` empiezan la línea con el mismo letrero de `OUT`, así que un `cout` con texto
sale como `Resultado del programa (OUT): Total: 120`.

Un programa de solo enteros y sin texto se ejecuta igual y la consola se ve igual que con el
`tm.c` original (las pruebas lo comparan). La única diferencia es que un entero que pasa de 32 bits
ya no da un valor sin sentido, porque los registros son `double`. Hay 8 registros, 1024
direcciones de instrucciones y 1024 de datos.

| Registro | Nombre | Uso |
|---|---|---|
| 7 | `pc` | Contador del programa |
| 6 | `mp` | Tope de la memoria: los temporales están en `0(6)`, `-1(6)`, `-2(6)`… |
| 5 | `gp` | Inicio de la memoria: la variable con dirección `d` está en `d(5)` |
| 0 | `ac` | Acumulador: cada expresión deja ahí su resultado |
| 1 | `ac1` | Segundo acumulador: el operando izquierdo |
| 2 | `ac2` | Auxiliar de `%`, `^`, `&&` y `\|\|`. TINY no lo usa |

Hay dos formatos de instrucción: `op r,s,t` (solo registros: `ADD`, `SUB`, `MUL`, `DIV`,
`DIVR`, `POW`, `IN`, `INR`, `OUT`, `OUTC`, `OUTN`, `HALT`) y `op r,d(s)` (registro y dirección `d + reg[s]`: `LD`, `ST`, `LDA`,
`LDC` y los saltos `JLT`, `JLE`, `JGT`, `JGE`, `JEQ`, `JNE`). El preludio carga en `mp`
la dirección más alta (`LD 6,0(0)`) y limpia la posición 0 (`ST 0,0(0)`).

**Correspondencia entre nuestros nodos y las instrucciones TM.** `d` es la dirección de la
variable en la tabla de símbolos. `t` es el temporal libre (empieza en 0 y baja con cada
operando guardado).

| Nuestro nodo | Nodo de TINY | Instrucciones TM |
|---|---|---|
| `programa`, `lista_declaracion`, `lista_sentencias`, `else_body` | Sentencias hermanas (`sibling`) | El código de cada sentencia, en orden |
| `declaracion_variable`, `KW_MAIN` | (no existe) | Ninguna: la tabla ya tiene las direcciones |
| `asignacion` | `AssignK` | expresión; `ST 0,d(5)` |
| `sent_in` | `ReadK` | `IN 0,0,0` (`INR 0,0,0` si la variable es `float`); `ST 0,d(5)` |
| `sent_out` sin texto | `WriteK` | por cada expresión: expresión; `OUT 0,0,0` |
| `sent_out` con texto | (no existe) | por cada byte del texto (UTF-8): `LDC 0,b(0)`; `OUTC 0,0,0`. Por cada expresión: expresión; `OUTN 0,0,0`. Al final: `LDC 0,10(0)`; `OUTC 0,0,0` |
| `seleccion` | `IfK` | condición; `JEQ 0,→else(7)`; then; `LDA 7,→fin(7)`; else |
| `repeticion` (`do … until`) | `RepeatK` | cuerpo; condición; `JEQ 0,→cuerpo(7)` |
| `iteracion` (`while`) | (no existe) | condición; `JEQ 0,→salida(7)`; cuerpo; `LDA 7,→condición(7)` |
| `incremento` | (no existe) | `LD 0,d(5)`; `LDA 0,1(0)` (`-1` para `--`); `ST 0,d(5)` |
| `INTEGER`, `REAL`, `true`, `false`, `-literal` | `ConstK` | `LDC 0,v(0)` (`true` = 1, `false` = 0; un real como en el fuente: `LDC 0,7.59(0)`) |
| `CONV` (int → float) | (no existe) | Ninguna: en la TM extendida un entero ya es un número real |
| `IDENTIFIER` | `IdK` | `LD 0,d(5)` |
| `OP_PLUS`, `OP_MINUS`, `OP_MULTIPLY`, `OP_DIVIDE` | `OpK` (`PLUS`, `MINUS`, `TIMES`, `OVER`) | izq; `ST 0,t(6)`; der; `LD 1,t(6)`; `ADD`/`SUB`/`MUL`/`DIV 0,1,0` (`DIVR` si la división es `float`) |
| `OP_LT`, `OP_EQ` | `OpK` (`LT`, `EQ`) | izq; `ST 0,t(6)`; der; `LD 1,t(6)`; `SUB 0,1,0`; `JLT`/`JEQ 0,2(7)`; `LDC 0,0(0)`; `LDA 7,1(7)`; `LDC 0,1(0)` |
| `OP_LE`, `OP_GT`, `OP_GE`, `OP_NE` | (no existen) | Igual que `<`, con `JLE`, `JGT`, `JGE`, `JNE` |
| `OP_MODULO` | (no existe) | operandos; `DIV 2,1,0`; `MUL 2,2,0`; `SUB 0,1,2` (izq − (izq / der) · der) |
| `OP_POWER` entre `int` | (no existe) | operandos; `LDC 2,1(0)`; `JLE 0,3(7)`; `MUL 2,2,1`; `LDA 0,-1(0)`; `LDA 7,-4(7)`; `LDA 0,0(2)`. Un ciclo de multiplicaciones: es exacto, mientras que `pow` con reales podría dar 99.999… |
| `OP_POWER` `float` | (no existe) | operandos; `POW 0,1,0` (acepta exponentes con decimales y negativos) |
| `OP_AND` | (no existe) | operandos; `JEQ 1,3(7)`; `JEQ 0,2(7)`; `LDC 0,1(0)`; `LDA 7,1(7)`; `LDC 0,0(0)` |
| `OP_OR` | (no existe) | operandos; `JNE 1,3(7)`; `JNE 0,2(7)`; `LDC 0,0(0)`; `LDA 7,1(7)`; `LDC 0,1(0)` |
| `OP_NOT` | (no existe) | operando; `JEQ 0,2(7)`; `LDC 0,0(0)`; `LDA 7,1(7)`; `LDC 0,1(0)` |
| `OP_NEG` | (no existe) | operando; `LDC 1,0(0)`; `SUB 0,1,0` |

Una condición es verdadera si su valor no es 0: `if`, `while` y `until` saltan con `JEQ`
cuando vale 0. `&&` y `||` evalúan los dos operandos (sin cortocircuito), igual que en el
`.ci`.

**Saltos.** La TM no tiene etiquetas: cada salto es un desplazamiento respecto del `pc`,
que al ejecutar una instrucción ya apunta a la siguiente. `JEQ 0,27(7)` en la dirección
13 salta a 13 + 1 + 27 = 41.
- Un salto hacia atrás ya conoce su destino. `emit_rm_abs` lo convierte en desplazamiento:
  d = destino − (dirección actual + 1).
- Un salto hacia adelante todavía no lo conoce:
  1. `emit_skip(1)` aparta su dirección y el generador sigue.
  2. Al terminar la parte que salta, `emit_backup` regresa a esa dirección y la escribe.
  3. `emit_restore` vuelve al final del código.

Por eso, en el archivo, ese salto aparece más abajo con su dirección original, igual que en
el `.tm` de TINY. El simulador acomoda cada instrucción en su dirección. En el factorial,
la etiqueta `L2` del `.ci` (inicio del `do`) es la dirección 16 del `.tm`: el `JEQ
0,-22(7)` de la dirección 37 salta a 37 + 1 − 22 = 16.

Ejemplo (`fact = fact * x;`, direcciones 16 a 21 del factorial):

```
 16:     LD  0,1(5)   carga fact (dirección 1) en ac
 17:     ST  0,0(6)   guarda el operando izquierdo en el temporal 0
 18:     LD  0,0(5)   carga x (dirección 0) en ac
 19:     LD  1,0(6)   recupera el operando izquierdo en ac1
 20:    MUL  0,1,0    ac = ac1 * ac
 21:     ST  0,1(5)   guarda el resultado en fact
```

En el `.ci` la misma sentencia es `t2 = fact * x` / `fact = t2`. El temporal `t2` es
simbólico y no corresponde a una dirección del `.tm`.

**Límites y errores:**

| Caso | Qué pasa |
|---|---|
| Más de 1024 instrucciones, o más de 1024 variables y temporales | Error de generación: no se genera el `.tm`, pero sí el `.ci`. Los ejercicios más largos del PDF usan unas 200 instrucciones |
| `^` entero con exponente negativo | Da 1: el ciclo de multiplicaciones no se ejecuta (con una constante negativa el análisis semántico ya da error). Con resultado `float` sí se calcula (`2.0 ^ -1` = 0.5) |
| División o residuo entre cero, `0.0 ^ negativo` | Lo detecta el simulador al ejecutar: `Error: division entre cero` |
| Potencia sin resultado real (`-4.0 ^ 0.5`) | Lo detecta el simulador al ejecutar: `Error: potencia sin resultado real` |

**Archivos y ejecución.** Con las fases `intermediate`, `execution` y `all`, el compilador
escribe `programa.ci` y `programa.tm` junto al fuente, como `tiny.exe`. Si alguno no se
generó, borra el que hubiera de una compilación anterior. Con `execution`, la sección
`EJECUCION` trae la ruta del `.tm`. El IDE la carga en `TM/tm.exe` y manda `g` (ejecutar).
En la pestaña Ejecución se contestan los `IN` / `INR` y se ven los `OUT`; también acepta
los comandos de la TM (`d`, `r`, `s`, `v`, `h`, `q`).
