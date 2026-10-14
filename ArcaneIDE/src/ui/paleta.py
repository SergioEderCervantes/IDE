"""Colores de resaltado de los resultados del compilador.

Hay una paleta para temas oscuros y otra para temas claros: el rojo y el ámbar claros
no se leen sobre fondo blanco (contraste ~2:1), y los oscuros no se leen sobre fondo oscuro.
"""

PALETA_OSCURA = {
    "error": "#f38ba8",       # nodos de error y verificaciones fallidas (✗)
    "conversion": "#e5a50a",  # nodos CONV int→float
    "aviso": "#e5a50a",       # avisos del pipeline ("no se ejecutó …")
    "falla": "#e64553",       # el compilador no pudo ejecutarse
}

PALETA_CLARA = {
    "error": "#c62828",
    "conversion": "#995c00",
    "aviso": "#995c00",
    "falla": "#c62828",
}


def paleta(tema_claro: bool) -> dict:
    return PALETA_CLARA if tema_claro else PALETA_OSCURA
