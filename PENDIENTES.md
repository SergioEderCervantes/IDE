# Pendientes

Fase 2 (análisis sintáctico) cerrada el 13/10/2026. Lo siguiente no bloquea la fase 3
y queda para después. Los tiempos son estimados de implementación y prueba.

## Bugs que no bloquean

| Pendiente | Cuándo se nota | Tiempo |
|---|---|---|
| **Recursión del lexer**: ~1000 espacios o saltos de línea seguidos provocan `RecursionError` (también tumba el resaltado del editor). Cambiar la recursión de `_next_token` por un ciclo | Muy raro | 5–10 min |
| **Colores desfasados con acentos o ñ** en el editor: `arcane_lexer.py` mezcla posiciones en caracteres con posiciones en bytes UTF-8 | Comentarios o cadenas con acentos | 20–30 min |
| **Token suelto corta el programa**: `main { x = 1; 5; y = 2; }` pierde `y = 2` y da errores en cascada (también `x = a ++ b;`). `_parse_lista_declaracion` sale del ciclo con el primer token fuera de FIRST | Solo programas con errores sintácticos | 30–45 min |
| **IDE desde el `.exe`**: busca `arcane-compiler` junto a `sys.executable`, que en PyInstaller es `main.exe`. Hoy muestra un error claro, pero no compila | Solo si se usa el `.exe` | 30–60 min |

## Limpieza

| Pendiente | Tiempo |
|---|---|
| Código muerto: `_FIRST_COMPONENTE` y `_SYNC_DECLARACION` en `parser.py`, la rama "Número inválido" en `arcane_lexer.py` | 5–10 min |
| `ArcaneIDE/pyproject.toml` no declara la dependencia a `arcane-compiler` (el resaltado la importa) | 5 min |
| Archivos sobrantes: `ArcaneCompiler/compiler.py` (mock viejo), `ArcaneIDE/test.txt`, `ejecutable/main.exe` versionado | 5 min |
| Samples viejos: `edge_cases.c` (sintaxis de C), `errors.c` (solo errores léxicos, no prueba el parser), `test_input.c` | 15–20 min |
| README desactualizado: estado de las fases, `do … until`, sin `switch`, formato JSON de `ERRORES`, comando de tests | 20–30 min |

## Posibles extensiones del lenguaje (nadie las pide)

`int x = 0;` · `cout << a << b << c;` · `cin >> x >> y;` · `switch`/`case` · tipo `char`
