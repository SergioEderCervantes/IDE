## Objetivo de la demo
Mostrar que el IDE cumple Fase 1:
- Gestión de archivos.
- Menú y botones de compilación por fases.
- Comunicación IDE -> compilador externo por parámetros.
- Compilador ejecutable de forma independiente desde consola.

---

##  Prueba rapida del compilador independiente
Desde la raíz del proyecto:

```powershell
python compiler/compiler.py test.txt lexical
python compiler/compiler.py test.txt execution
```


## Arranque del IDE

```powershell
python -m src.main
```

### Que revisar visualmente
- Menú **Archivo** con: Nuevo, Abrir, Cerrar, Guardar, Guardar como, Salir.
- Menú **Compile** con: Lexical, Syntactic, Semantic, Intermediate, Execute.
- Botones rápidos de compilación en toolbar.
- Editor con numeración de líneas.
- Línea/columna visibles de forma permanente en status bar.

---


## Checklist
- [ ] Compilador ejecuta por consola sin IDE.
- [ ] IDE invoca compilador externo.
- [ ] Menús y botones de fases disponibles.
- [ ] Gestión de archivos completa (incluye Cerrar y Salir).
- [ ] Paneles de resultados visibles.
- [ ] Línea y columna visibles en la interfaz.

---
