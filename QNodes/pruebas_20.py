from src.main import run_prueba

def ejecutar_pruebas(variante="A", k=4):
    ESTADO = "10000000000000000000" # 20 caracteres
    
    pruebas = [
        ("ABCDEFGHIJKLMNOPQRST", "ABCDEFGHIJKLMNOPQRST"),
        ("ABCDEFGHIJKLMNOPQRST", "ABCDEFGHIJKLMNOPQRS"),
        ("ABCDEFGHIJKLMNOPQRST", "BCDEFGHIJKLMNOPQRST"),
        ("ABCDEFGHIJKLMNOPQRST", "BCDEFGHIJKLMNOPQRS"),
        ("ABCDEFGHIJKLMNOPQRST", "ABDEGHJKMNPQST"),
        ("ABCDEFGHIJKLMNOPQRST", "ACEGIKMOQS"),
        ("ABCDEFGHIJKLMNOPQRST", "BDFHJLNPRT"),
    ]

    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)
