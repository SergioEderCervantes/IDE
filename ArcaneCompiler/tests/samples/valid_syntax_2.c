main {
    int contador;
    float suma;

    contador = 0;
    suma = 0;

    while contador < 10
        suma = suma + contador;
        contador = contador + 1;
    end

    do
        contador = contador - 1;
    while contador > 0

    cout << suma;
}
