import argparse
import importlib.util
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description="Ejecutor de benchmarks QNodes/KQNodes")
    parser.add_argument("--nodos", type=int, required=True, help="Número de nodos (2, 3, 4, 5, 6, 8, 10, 15, 20, 22, 25)")
    parser.add_argument("--variante", type=str, required=True, help="Variante (A, B, etc.)")
    parser.add_argument("--k", type=int, default=4, help="Número de particiones (k)")
    
    args = parser.parse_args()

    modulo_nombre = f"pruebas_{args.nodos}"
    script_dir = Path(__file__).resolve().parent
    module_path = script_dir / f"{modulo_nombre}.py"

    try:
        if not module_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo {module_path}")

        spec = importlib.util.spec_from_file_location(modulo_nombre, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"No se pudo cargar el módulo {modulo_nombre}")

        pruebas_mod = importlib.util.module_from_spec(spec)
        sys.modules[modulo_nombre] = pruebas_mod
        spec.loader.exec_module(pruebas_mod)

        if not hasattr(pruebas_mod, 'ejecutar_pruebas'):
            raise AttributeError(f"El módulo {modulo_nombre} no tiene la función 'ejecutar_pruebas'")

        pruebas_mod.ejecutar_pruebas(variante=args.variante, k=args.k)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ImportError as e:
        print(f"Error de importación: {e}")
    except AttributeError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    main()
