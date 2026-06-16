from src.main import run_prueba

def ejecutar_pruebas(variante="A", k=2):
    ESTADO = "10"  # 2 nodos: primero encendido, segundo apagado
    
    # Formato: (alcance, mecanismo) como LETRAS (se convierten automáticamente)
    # Para 2 nodos: A (posición 0), B (posición 1)
    # "AB" = ambos, "AB" combinaciones diferentes
    # IMPORTANTE: El alcance y mecanismo deben tener AMBOS nodos disponibles
    pruebas = [
        ("AB", "AB"),  # Alcance AB, Mecanismo AB - Caso completo
        ("AB", "AB"),  # Alcance AB, Mecanismo AB - Caso completo (repetido)
        ("AB", "AB"),  # Alcance AB, Mecanismo AB - Caso completo (repetido)
        ("AB", "AB"),  # Alcance AB, Mecanismo AB - Caso completo (repetido)
        ("AB", "AB"),  # Alcance AB, Mecanismo AB - Caso completo (repetido)
        ("AB", "AB"),  # Alcance AB, Mecanismo AB - Caso completo (repetido)
    ]
    
    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)
