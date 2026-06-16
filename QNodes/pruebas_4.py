from src.main import run_prueba

def ejecutar_pruebas(variante="A", k=2):
    ESTADO = "1000"  # 4 nodos: A encendido, B,C,D apagados
    pruebas = [
        ("ABCD", "ABCD"),
        ("ABCD", "ABC"),
        ("ABCD", "ABD"),
        ("ABCD", "AB"),
        ("ABCD", "A"),
        ("ABC", "ABC"),
        ("ABD", "ABD"),
        ("AB", "AB"),
    ]
    
    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)
