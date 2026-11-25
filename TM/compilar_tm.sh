#!/bin/sh
# Compila el simulador TM de la materia (tm.c, extendido para reales) con gcc en Linux.
# Uso: ./compilar_tm.sh   (desde esta carpeta o desde cualquier otra)
# Deja el ejecutable en TM/tm, que es donde lo busca el IDE fuera de Windows.
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! gcc -O2 -o "$DIR/tm" "$DIR/tm.c" -lm; then
  echo "No se pudo compilar tm.c. Revisa que gcc este instalado (sudo apt install gcc)."
  exit 1
fi
echo "Listo: $DIR/tm"
