import argparse
import importlib

def main():
    parser = argparse.ArgumentParser(description="Ejecutor de benchmarks QNodes/KQNodes")
    parser.add_argument("--nodos", type=int, required=True, help="Número de nodos (10, 15, 20, 22, 25)")
    parser.add_argument("--variante", type=str, required=True, help="Variante (A, B, etc.)")
    parser.add_argument("--k", type=int, default=4, help="Número de particiones (k)")
    
    args = parser.parse_args()

    # Construimos el nombre del módulo: pruebas_10, pruebas_15, etc.
    modulo_pruebas = f"pruebas_{args.nodos}"
    
    try:
        # Importamos dinámicamente el módulo de pruebas
        pruebas_mod = importlib.import_module(modulo_pruebas)
        
        # Ejecutamos las pruebas con la configuración proporcionada
        pruebas_mod.ejecutar_pruebas(variante=args.variante, k=args.k)
        
    except ImportError:
        print(f"❌ Error: No se encontró el archivo {modulo_pruebas}.py")
    except AttributeError:
        print(f"❌ Error: El archivo {modulo_pruebas}.py no tiene una función 'ejecutar_pruebas'")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()
