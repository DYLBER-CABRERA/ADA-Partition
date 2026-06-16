from src.main import run_prueba


def ejecutar_pruebas(variante="B", k=4):
    ESTADO = "100000000000000"

    pruebas = [
        ("ABCDEFGHIJKLMNO", "ABCDEFGHIJKLMNO"),
        ("ABCDEFGHIJKLMNO", "ABCDEFGHIJKLMN"),
        ("ABCDEFGHIJKLMNO", "BCDEFGHIJKLMNO"),
        ("ABCDEFGHIJKLMNO", "BCDEFGHIJKLMN"),
        ("ABCDEFGHIJKLMNO", "ABDEGHJKMN"),
        ("ABCDEFGHIJKLMNO", "ACEGIKMO"),
        ("ABCDEFGHIJKLMNO", "BDFHJLN"),

        ("ABCDEFGHIJKLMN", "ABCDEFGHIJKLMNO"),
        ("ABCDEFGHIJKLMN", "ABCDEFGHIJKLMN"),
        ("ABCDEFGHIJKLMN", "BCDEFGHIJKLMNO"),
        ("ABCDEFGHIJKLMN", "BCDEFGHIJKLMN"),
        ("ABCDEFGHIJKLMN", "ABDEGHJKMN"),
        ("ABCDEFGHIJKLMN", "ACEGIKMO"),
        ("ABCDEFGHIJKLMN", "BDFHJLN"),

        ("BCDEFGHIJKLMNO", "ABCDEFGHIJKLMNO"),
        ("BCDEFGHIJKLMNO", "ABCDEFGHIJKLMN"),
        ("BCDEFGHIJKLMNO", "BCDEFGHIJKLMNO"),
        ("BCDEFGHIJKLMNO", "BCDEFGHIJKLMN"),
        ("BCDEFGHIJKLMNO", "ABDEGHJKMN"),
        ("BCDEFGHIJKLMNO", "ACEGIKMO"),
        ("BCDEFGHIJKLMNO", "BDFHJLN"),

        ("BCDEFGHIJKLMN", "ABCDEFGHIJKLMNO"),
        ("BCDEFGHIJKLMN", "ABCDEFGHIJKLMN"),
        ("BCDEFGHIJKLMN", "BCDEFGHIJKLMNO"),
        ("BCDEFGHIJKLMN", "BCDEFGHIJKLMN"),
        ("BCDEFGHIJKLMN", "ABDEGHJKMN"),
        ("BCDEFGHIJKLMN", "ACEGIKMO"),
        ("BCDEFGHIJKLMN", "BDFHJLN"),

        ("ABDEGHJKMN", "ABCDEFGHIJKLMNO"),
        ("ABDEGHJKMN", "ABCDEFGHIJKLMN"),
        ("ABDEGHJKMN", "BCDEFGHIJKLMNO"),
        ("ABDEGHJKMN", "BCDEFGHIJKLMN"),
        ("ABDEGHJKMN", "ABDEGHJKMN"),
        ("ABDEGHJKMN", "ACEGIKMO"),
        ("ABDEGHJKMN", "BDFHJLN"),

        ("ACEGIKMO", "ABCDEFGHIJKLMNO"),
        ("ACEGIKMO", "ABCDEFGHIJKLMN"),
        ("ACEGIKMO", "BCDEFGHIJKLMNO"),
        ("ACEGIKMO", "BCDEFGHIJKLMN"),
        ("ACEGIKMO", "ABDEGHJKMN"),
        ("ACEGIKMO", "ACEGIKMO"),
        ("ACEGIKMO", "BDFHJLN"),

        ("BDFHJLN", "ABCDEFGHIJKLMNO"),
        ("BDFHJLN", "ABCDEFGHIJKLMN"),
        ("BDFHJLN", "BCDEFGHIJKLMNO"),
        ("BDFHJLN", "BCDEFGHIJKLMN"),
        ("BDFHJLN", "ABDEGHJKMN"),
        ("BDFHJLN", "ACEGIKMO"),
        ("BDFHJLN", "BDFHJLN"),

        ("BCDEFGJKLMNO", "BCDEFGHIJKLMNO"),
    ]

    for i, (alcance, mecanismo) in enumerate(pruebas, 1):
        print(f"\n{'='*60}")
        print(f"Prueba {i}/{len(pruebas)}")
        run_prueba(alcance, mecanismo, k=k, estado_inicio=ESTADO, variante=variante)