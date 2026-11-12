# Pendientes

Fases 1 a 4 terminadas (la 4, código intermedio, el 11/11/2026). Lo siguiente no bloquea la
fase 5 y queda para después. Los tiempos son estimados de implementación y prueba.

## Bugs que no bloquean

| Pendiente | Cuándo se nota | Tiempo |
|---|---|---|
| **IDE empaquetado como `.exe`**: `CompilerRunner` lanza `sys.executable -m arcane_compiler.main`, y en PyInstaller `sys.executable` es el propio IDE, así que no compila. El `ejecutable/main.exe` viejo (de marzo, anterior al léxico) se quitó del repo: hay que volver a generarlo cuando esto se arregle | Solo si se usa el `.exe` | 30–60 min |

## Posibles extensiones del lenguaje (nadie las pide)

`int x = 0;` · `cout << a << b << c;` · `cin >> x >> y;` · `switch`/`case` · tipo `char`
