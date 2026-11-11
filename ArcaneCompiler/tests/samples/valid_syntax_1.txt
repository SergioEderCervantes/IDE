main {
    int x, y;
    float promedio;
    bool activo;

    cin >> x;
    cin >> y;

    activo = true;

    if x > y then
        promedio = x;
    else
        promedio = y;
    end

    cout << "resultado: " << promedio;
}
