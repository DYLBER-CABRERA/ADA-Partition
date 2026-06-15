import sys, json
from pathlib import Path

# Lógica: Añade el directorio raíz del proyecto al path de Python para que los imports
#         `from src.*` funcionen al ejecutar este script directamente (no como módulo).
# Sintaxis: La ruta hardcodeada es absoluta — funciona solo en el equipo de desarrollo;
#           para portabilidad se puede reemplazar por `Path(__file__).resolve().parents[1]`.
sys.path.insert(0, r"D:\Universidad\Analisis y Diseño de Algoritmos\Proyecto 2026-1\projecto-analisis-20261\K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation")
import numpy as np
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.k_geometric import KGeometricSIA
from src.funcs.system import stirling
# Lógica: Deshabilita colorama para evitar códigos ANSI en la salida del script;
#         solution.py activa colorama al importarse, por eso se deshabilita aquí.
# Sintaxis: `colorama.deinit()` revierte la inicialización; `except: pass` silencia
#           cualquier error si colorama no está instalado.
try:
    import colorama; colorama.deinit()
except: pass

# Lógica: Ruta absoluta al directorio de muestras; los CSVs de TPM deben existir aquí
#         para que el script pueda cargar cada dataset del benchmark.
# Sintaxis: `Path(r"...")` crea un objeto Path desde raw string; evita escapes de `\`.
SAMPLES = Path(r"D:\Universidad\Analisis y Diseño de Algoritmos\Proyecto 2026-1\projecto-analisis-20261\K-GeoMIP\data\samples")
# Lógica: Lista de datasets a evaluar como tuplas (n_nodos, nombre_csv); cubre n∈{3..10}
#         para comparar el crecimiento de la pérdida EMD con el tamaño de la red.
# Sintaxis: Lista de tuplas con n y el nombre del CSV correspondiente.
datasets = [(3,"N3A.csv"),(4,"N4A.csv"),(5,"N5A.csv"),(6,"N6A.csv"),(8,"N8A.csv"),(10,"N10A.csv")]

# Lógica: Dict anidado para almacenar la pérdida EMD por (n, k); se serializa a JSON
#         al final para uso por otros scripts o notebooks de análisis.
# Sintaxis: Dict vacío inicializado antes del bucle; se llena con `results[n][k] = float(...)`.
results = {}
for n, csv in datasets:
    # Lógica: Carga la TPM una vez por dataset y construye el estado inicial y condición
    #         estándar del benchmark (nodo A activo, todos los demás inactivos).
    # Sintaxis: `np.genfromtxt(SAMPLES/csv, delimiter=",")` carga el CSV como ndarray float64;
    #           `"1"+"0"*(n-1)` genera el estado inicial de n bits.
    tpm = np.genfromtxt(SAMPLES/csv, delimiter=",")
    ei = "1"+"0"*(n-1); cond = "1"*n
    results[n] = {}
    # Lógica: Ejecuta GeometricSIA (k=2) como referencia exacta y almacena la pérdida EMD
    #         bajo la clave k=2 para comparación con los valores de k>2.
    # Sintaxis: `float(sol.perdida)` convierte np.float32 a float nativo para serialización JSON.
    sol = GeometricSIA(Manager(estado_inicial=ei)).aplicar_estrategia(cond,cond,cond,tpm)
    results[n][2] = float(sol.perdida)
    for k in [3,4,5]:
        # Lógica: Solo ejecuta KGeometricSIA si n >= k — no se pueden hacer k-particiones
        #         con menos nodos que partes.
        # Sintaxis: `if n >= k` es la guarda de precondición; sin ella KGeometricSIA
        #           lanzaría un error al intentar partir n nodos en k > n grupos.
        if n >= k:
            sol = KGeometricSIA(Manager(estado_inicial=ei)).aplicar_estrategia(cond,cond,cond,tpm,k=k)
            results[n][k] = float(sol.perdida)

# Lógica: Calcula los números de Stirling S(n,k) para cada (n,k) del benchmark para
#         medir la reducción del espacio de búsqueda que logra el greedy.
# Sintaxis: Dict anidado `stir[n][k] = S(n,k)`; `stirling(n, k)` es la función importada
#           de `src.funcs.system` que calcula el número de Stirling de segunda especie.
stir = {}
for n in [3,4,5,6,8,10]:
    stir[n] = {}
    for k in [3,4,5]:
        if n >= k:
            stir[n][k] = stirling(n,k)

# Lógica: Serializa los resultados de pérdidas y números de Stirling a un archivo JSON
#         para que sean reutilizables por notebooks o scripts de visualización sin re-ejecutar.
# Sintaxis: `json.dumps(obj, indent=2)` serializa el dict a string JSON con indentación;
#           `outpath.write_text(...)` escribe el string al archivo en una sola llamada.
outpath = Path(r"D:\Universidad\Analisis y Diseño de Algoritmos\Proyecto 2026-1\projecto-analisis-20261\K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation\experiments\results.json")
# Lógica: Crea el directorio de salida si no existe antes de escribir el archivo JSON.
# Sintaxis: `.parent` accede al directorio padre de la ruta; `.mkdir(exist_ok=True)`
#           crea el directorio sin error si ya existe.
outpath.parent.mkdir(exist_ok=True)
outpath.write_text(json.dumps({"losses": results, "stirling": stir}, indent=2))
