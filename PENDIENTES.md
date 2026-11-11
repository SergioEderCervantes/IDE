# Pendientes

Fases 1 a 4 terminadas (la 4, código intermedio, el 11/11/2026). Lo siguiente no bloquea la
fase 5 y queda para después. Los tiempos son estimados de implementación y prueba.

## Bugs que no bloquean

| Pendiente | Cuándo se nota | Tiempo |
|---|---|---|
| **Token suelto corta el programa**: `main { x = 1; 5; y = 2; }` pierde `y = 2` y da errores en cascada (también `x = a ++ b;`). `_parse_lista_declaracion` sale del ciclo con el primer token fuera de FIRST | Solo programas con errores sintácticos | 30–45 min |
| **Error en la condición de un `if` se traga el resto del programa**: `if then x = 1; end …` o `if x > then …`. `_parse_componente` ya avanza hasta `;` antes de lanzar `ParseError`, y `_parse_seleccion` después busca el siguiente `then`, que puede ser el de otro `if` o no existir (fin de archivo) | Solo programas con errores sintácticos | 30–45 min |
| **IDE empaquetado como `.exe`**: `CompilerRunner` lanza `sys.executable -m arcane_compiler.main`, y en PyInstaller `sys.executable` es el propio IDE, así que no compila. El `ejecutable/main.exe` viejo (de marzo, anterior al léxico) se quitó del repo: hay que volver a generarlo cuando esto se arregle | Solo si se usa el `.exe` | 30–60 min |

## Posibles extensiones del lenguaje (nadie las pide)

`int x = 0;` · `cout << a << b << c;` · `cin >> x >> y;` · `switch`/`case` · tipo `char`
