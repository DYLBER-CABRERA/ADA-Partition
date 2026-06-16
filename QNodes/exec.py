import sys
import os
import re
from pathlib import Path
from src.models.base.application import aplicacion
from src.main import iniciar

def obtener_redes_disponibles():
    """Busca archivos CSV en .samples/ y retorna sus nombres"""
    ruta_samples = Path("src/.samples")
    if not ruta_samples.exists():
        return []
    
    # Buscamos archivos que sigan el patrón N(número)(Letra).csv
    redes = [f.stem for f in ruta_samples.glob("N[0-9]*[A-Z].csv")]
    return sorted(redes, key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)

def main():
    """Inicialización del aplicativo con CLI inteligente"""
    
    # 1. Configuración básica
    aplicacion.activar_profiling()
    
    # 2. Lógica de selección de red
    red_seleccionada = None
    
    # Caso A: Se pasó el nombre por argumento (ej: python exec.py N10A)
    if len(sys.argv) > 1:
        red_seleccionada = sys.argv[1].upper()
    
    # Caso B: Menú interactivo
    else:
        redes = obtener_redes_disponibles()
        
        if not redes:
            print("❌ No se encontraron redes en src/.samples/")
            return

        print("\n--- 🌐 MENÚ DE SELECCIÓN DE RED ---")
        for i, red in enumerate(redes, 1):
            print(f"{i}. {red}")
        print("-----------------------------------")
        
        try:
            opcion_str = input(f"\nSelecciona el número de la red (1-{len(redes)}): ")
            if not opcion_str:
                return
            opcion = int(opcion_str)
            if 1 <= opcion <= len(redes):
                red_seleccionada = redes[opcion - 1]
            else:
                print("❌ Opción inválida.")
                return
        except ValueError:
            print("❌ Por favor, introduce un número.")
            return

    # 3. Ejecutar
    if red_seleccionada:
        iniciar(red_seleccionada)

if __name__ == "__main__":
    main()
