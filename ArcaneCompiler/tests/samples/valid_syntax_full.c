main {
    int x, y, z;
    float suma, promedio;
    bool activo, encontrado;

    cin >> x;
    cin >> y;

    activo = true;
    encontrado = false;

    z = x + y * 2 - 1;
    suma = x ^ 2 + y ^ 2;

    if x > y then
        promedio = x;
    else
        promedio = y;
    end

    if x >= 0 && activo then
        cout << "positivo";
    end

    if x != y then
        cout << "distintos";
    end

    while x > 0
        x = x - 1;
        suma = suma + x;
    end

    do
        y = y + 1;
    while y < 10

    if !encontrado then
        cout << "no encontrado";
    end

    cout << "resultado: " << promedio;
    cout << suma;
}
