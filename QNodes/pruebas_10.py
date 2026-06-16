from src.main import run_prueba

def ejecutar_pruebas(variante="A", k=4):
    ESTADO = "1000000000" # 10 caracteres
    
    pruebas = [
    ("ABCDEFGHIJ", "ABCDEFGHIJ"),
    ("ABCDEFGHIJ", "ABCDEFGHI"),
    ("ABCDEFGHIJ", "BCDEFGHIJ"),
    ("ABCDEFGHIJ", "BCDEFGHI"),
    ("ABCDEFGHIJ", "ABDEGHJ"),
    ("ABCDEFGHIJ", "ACEGI"),
    ("ABCDEFGHIJ", "BDFHJ"),

    ("ABCDEFGHI", "ABCDEFGHIJ"),
    ("ABCDEFGHI", "ABCDEFGHI"),
    ("ABCDEFGHI", "BCDEFGHIJ"),
    ("ABCDEFGHI", "BCDEFGHI"),
    ("ABCDEFGHI", "ABDEGHJ"),
    ("ABCDEFGHI", "ACEGI"),
    ("ABCDEFGHI", "BDFHJ"),

    ("BCDEFGHIJ", "ABCDEFGHIJ"),
    ("BCDEFGHIJ", "ABCDEFGHI"),
    ("BCDEFGHIJ", "BCDEFGHIJ"),
    ("BCDEFGHIJ", "BCDEFGHI"),
    ("BCDEFGHIJ", "ABDEGHJ"),
    ("BCDEFGHIJ", "ACEGI"),
    ("BCDEFGHIJ", "BDFHJ"),

    ("BCDEFGHI", "ABCDEFGHIJ"),
    ("BCDEFGHI", "ABCDEFGHI"),
    ("BCDEFGHI", "BCDEFGHIJ"),
    ("BCDEFGHI", "BCDEFGHI"),
    ("BCDEFGHI", "ABDEGHJ"),
    ("BCDEFGHI", "ACEGI"),
    ("BCDEFGHI", "BDFHJ"),

    ("ABDEGHJ", "ABCDEFGHIJ"),
    ("ABDEGHJ", "ABCDEFGHI"),
    ("ABDEGHJ", "BCDEFGHIJ"),
    ("ABDEGHJ", "BCDEFGHI"),
    ("ABDEGHJ", "ABDEGHJ"),
    ("ABDEGHJ", "ACEGI"),
    ("ABDEGHJ", "BDFHJ"),

    ("ACEGI", "ABCDEFGHIJ"),
    ("ACEGI", "ABCDEFGHI"),
    ("ACEGI", "BCDEFGHIJ"),
    ("ACEGI", "BCDEFGHI"),
    ("ACEGI", "ABDEGHJ"),
    ("ACEGI", "ACEGI"),
    ("ACEGI", "BDFHJ"),

    ("BDFHJ", "ABCDEFGHIJ"),
    ("BDFHJ", "ABCDEFGHI"),
    ("BDFHJ", "BCDEFGHIJ"),
    ("BDFHJ", "BCDEFGHI"),
    ("BDFHJ", "ABDEGHJ"),
    ("BDFHJ", "ACEGI"),
    ("BDFHJ", "BDFHJ"),
    ]

    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)
