from src.main import run_prueba

def ejecutar_pruebas(variante="A", k=2):
    ESTADO = "100"  # 3 nodos: A encendido, B y C apagados
    pruebas = [
        ("ABC", "ABC"),
        ("ABC", "AB"),
        ("ABC", "AC"),
        ("ABC", "BC"),
        ("ABC", "A"),
        ("ABC", "B"),
        ("ABC", "C"),
        ("AB", "AB"),
    ]
    
    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)
