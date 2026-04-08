/* Programa de prueba completo */
// Comentario de linea
int main() {
    int x = 10;
    float y = 3.14;
    int contador = 0;

    if (x > 5) {
        contador++;
        cout << "mayor";
    } else {
        contador--;
    }

    while (x != 0) {
        x = x - 1;
        y = y * 2.0;
    }

    switch (contador) {
        case 1:
            x = x + 1;
        end
    }

    int a = x % 3;
    int b = x ^ 2;

    if (x >= 0 && y <= 10.0) {
        cout << "ok";
    }

    if (x == 0 || y != 1.0) {
        cin >> x;
    }

    char c = 'A';
    do {
        x = x + 1;
    } while (x < 10);
}
