from src.main import run_prueba

def ejecutar_pruebas(variante="A", k=2):
    ESTADO = "10000"  # 5 nodos: A encendido, B,C,D,E apagados
    pruebas = [
        ("ABCDE", "ABCDE"),
        ("ABCDE", "ABCD"),
        ("ABCDE", "ABCE"),
        ("ABCDE", "ABC"),
        ("ABCDE", "AB"),
        ("ABCDE", "A"),
        ("ABCD", "ABCD"),
        ("ABC", "ABC"),
    ]
    
    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)
