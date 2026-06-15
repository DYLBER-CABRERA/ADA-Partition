"""
Benchmark Paso 6 — Análisis Experimental K-GeoMIP
==================================================
Compara GeometricSIA (k=2) vs KGeometricSIA (k=3,4,5) en datasets
de tamaño creciente: n∈{3,4,5,6,8,10}.

Ejecución (desde Method2_Dynamic_Programming_Reformulation/):
    python experiments/benchmark_paso6.py
"""
import sys
import time
from pathlib import Path

# Lógica: Añade el directorio raíz del proyecto (Method2_...) al path de Python para que
#         los imports `from src.*` funcionen al ejecutar el script directamente.
# Sintaxis: `Path(__file__).resolve().parents[1]` sube un nivel desde experiments/
#           hasta Method2_Dynamic_Programming_Reformulation/; `sys.path.insert(0, ...)` lo pone primero.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.k_geometric import KGeometricSIA
from src.funcs.system import stirling

# Lógica: Deshabilita colorama después de importar todos los módulos del proyecto porque
#         `solution.py` llama a `colorama.init()` al importarse, activando los códigos ANSI.
#         En este script de benchmark la salida en consola debe ser texto plano sin ANSI.
# Sintaxis: `colorama.deinit()` revierte la inicialización de colorama; el bloque try/except
#           evita que el script falle si colorama no está instalado.
try:
    import colorama
    colorama.deinit()
except ImportError:
    pass

# ── Configuración de los experimentos ───────────────────────────────────────

# Lógica: Construye la ruta absoluta al directorio de muestras subiendo 3 niveles desde
#         experiments/ hasta la raíz del repositorio K-GeoMIP y bajando a data/samples/.
# Sintaxis: `Path(__file__).resolve().parents[3]` sube 3 niveles: experiments→Method2→src→K-GeoMIP;
#           el operador `/` de pathlib concatena el resto de la ruta.
SAMPLES_DIR = Path(__file__).resolve().parents[3] / "data" / "samples"

# Lógica: Lista de datasets disponibles como tuplas (n_nodos, nombre_csv) para iterar el benchmark;
#         solo incluye tamaños para los que existen archivos en data/samples/.
# Sintaxis: Lista de tuplas `(int, str)`; se itera con desempaquetado `for n, csv_name in DATASETS`.
DATASETS = [
    (3,  "N3A.csv"),
    (4,  "N4A.csv"),
    (5,  "N5A.csv"),
    (6,  "N6A.csv"),
    (8,  "N8A.csv"),
    (10, "N10A.csv"),
]

# Lógica: Valores de k a evaluar; k=2 usa GeometricSIA (referencia exacta),
#         k=3,4,5 usan KGeometricSIA (greedy heurístico).
# Sintaxis: Lista de enteros; se itera en los bucles de medición.
K_VALUES = [2, 3, 4, 5]

# ── Funciones de benchmark ───────────────────────────────────────────────────

def estado_inicial(n: int) -> str:
    # Lógica: Genera el estado inicial estándar del benchmark: nodo A activo (1) y todos
    #         los demás inactivos (0), para consistencia entre todos los datasets.
    # Sintaxis: `"1" + "0" * (n - 1)` concatena el "1" inicial con n-1 ceros;
    #           el operador `*` sobre strings repite el string el número indicado de veces.
    return "1" + "0" * (n - 1)

def condicion(n: int) -> str:
    # Lógica: Genera la condición "todos activos" para no descartar ninguna variable en
    #         el condicionamiento ni en el alcance/mecanismo del benchmark.
    # Sintaxis: `"1" * n` repite el carácter "1" n veces — todos los bits activos.
    return "1" * n

def cargar_tpm(csv_name: str) -> np.ndarray:
    # Lógica: Carga la TPM desde el archivo CSV en SAMPLES_DIR usando np.genfromtxt
    #         con el separador de coma estándar del proyecto.
    # Sintaxis: `SAMPLES_DIR / csv_name` concatena la ruta base con el nombre del archivo;
    #           `np.genfromtxt(path, delimiter=",")` retorna ndarray de float64.
    path = SAMPLES_DIR / csv_name
    return np.genfromtxt(path, delimiter=",")

def medir_geometric(gestor, tpm, n):
    # Lógica: Mide el tiempo de ejecución de GeometricSIA (k=2) usando perf_counter de alta
    #         resolución y retorna el tiempo en segundos junto a la pérdida EMD óptima.
    # Sintaxis: `time.perf_counter()` retorna float en segundos con resolución de nanosegundos;
    #           la diferencia `t = perf_counter() - t0` es la duración del análisis.
    cond = condicion(n)
    t0 = time.perf_counter()
    sol = GeometricSIA(gestor).aplicar_estrategia(cond, cond, cond, tpm)
    t = time.perf_counter() - t0
    return t, sol.perdida

def medir_kgeometric(gestor, tpm, n, k):
    # Lógica: Mide el tiempo de ejecución de KGeometricSIA para el k dado; retorna (None, None)
    #         si n < k porque no se pueden hacer k-particiones con menos nodos que partes.
    # Sintaxis: `if n < k: return None, None` es la guarda de precondición; retorna tupla
    #           de Nones para que el llamador la maneje con `if t_k is not None`.
    if n < k:
        return None, None
    cond = condicion(n)
    t0 = time.perf_counter()
    sol = KGeometricSIA(gestor).aplicar_estrategia(cond, cond, cond, tpm, k=k)
    t = time.perf_counter() - t0
    return t, sol.perdida

# ── Ejecución ────────────────────────────────────────────────────────────────

print("=" * 72)
print("  BENCHMARK PASO 6 — K-GeoMIP vs GeoMIP")
print("  Fecha: 2026-05-29  |  Entorno: Python 3.12.5 / Windows 11")
print("=" * 72)

# Tabla 1: Tiempos por (n, k)
print("\n[TABLA 1] Tiempo de ejecución (segundos) por dataset y k")
print(f"{'n':>4} {'archivo':>10} {'k=2 (Geo)':>12} {'k=3':>10} {'k=4':>10} {'k=5':>10}")
print("-" * 62)

# Lógica: `resultados` almacena los tiempos y pérdidas por (n, k) para reutilizarlos
#         en las tablas 2 y 3 sin repetir los análisis.
# Sintaxis: Dict anidado `{n: {k: (tiempo, perdida)}}`; se llena en el bucle siguiente.
resultados = {}

for n, csv_name in DATASETS:
    # Lógica: Omite datasets que no existen en disco sin lanzar excepción, permitiendo
    #         ejecutar el benchmark con un subconjunto de los archivos disponibles.
    # Sintaxis: `(SAMPLES_DIR / csv_name).exists()` retorna True si el archivo existe;
    #           `continue` salta a la siguiente iteración del bucle.
    if not (SAMPLES_DIR / csv_name).exists():
        print(f"  [SKIP] {csv_name} no encontrado en {SAMPLES_DIR}")
        continue

    # Lógica: Carga la TPM una vez por dataset y crea el Manager para reutilizarlos en
    #         todos los k del mismo n, evitando I/O redundante.
    # Sintaxis: `Manager(estado_inicial=estado_inicial(n))` usa el keyword argument;
    #           `resultados[n] = {}` inicializa el dict interno para este n.
    tpm = cargar_tpm(csv_name)
    gestor = Manager(estado_inicial=estado_inicial(n))
    resultados[n] = {}

    # Lógica: Mide GeometricSIA (k=2) como referencia exacta para comparar con los k>2;
    #         su tiempo y pérdida son el denominador del ratio en la Tabla 2.
    # Sintaxis: Desempaquetado de la tupla retornada por medir_geometric.
    t_geo, loss_geo = medir_geometric(gestor, tpm, n)
    resultados[n][2] = (t_geo, loss_geo)

    # Lógica: Inicia la fila de la tabla con n, nombre del CSV y el tiempo de k=2
    #         formateado con 4 decimales para alineación de columnas.
    # Sintaxis: f-string con especificadores de formato `>4` (alinear derecha 4 chars)
    #           y `.4f` (float con 4 decimales).
    row = f"{n:>4} {csv_name:>10} {t_geo:>12.4f}"

    # Lógica: Mide KGeometricSIA para k=3,4,5 con un Manager nuevo por k para evitar
    #         estado compartido entre análisis con distinto k.
    # Sintaxis: Bucle `for k in [3, 4, 5]`; `if t_k is not None` maneja el caso n < k.
    for k in [3, 4, 5]:
        gestor_k = Manager(estado_inicial=estado_inicial(n))
        t_k, loss_k = medir_kgeometric(gestor_k, tpm, n, k)
        if t_k is not None:
            resultados[n][k] = (t_k, loss_k)
            row += f" {t_k:>10.4f}"
        else:
            row += f" {'N/A':>10}"
    print(row)

# Tabla 2: Ratio t_k / t_geo
print("\n[TABLA 2] Ratio de tiempo t_k / t_geo(k=2)")
print(f"{'n':>4} {'k=3/k=2':>12} {'k=4/k=2':>12} {'k=5/k=2':>12}")
print("-" * 44)
for n in sorted(resultados):
    if 2 not in resultados[n]:
        continue
    # Lógica: Recupera el tiempo base (k=2) para calcular el ratio de speedup relativo;
    #         `max(t_geo, 1e-9)` evita división por cero si el tiempo fue < 1ns.
    # Sintaxis: `resultados[n][2][0]` indexa el dict anidado; `[0]` extrae el tiempo
    #           de la tupla (tiempo, perdida).
    t_geo = resultados[n][2][0]
    row = f"{n:>4}"
    for k in [3, 4, 5]:
        if k in resultados[n]:
            # Lógica: Calcula el ratio t_k / t_geo para mostrar cuántas veces más lento
            #         es KGeometricSIA respecto a GeometricSIA.
            # Sintaxis: `max(t_geo, 1e-9)` como denominador seguro; `.2f` con "x" al final.
            ratio = resultados[n][k][0] / max(t_geo, 1e-9)
            row += f" {ratio:>12.2f}x"
        else:
            row += f" {'N/A':>12}"
    print(row)

# Tabla 3: Pérdida δ_k (calidad de la solución)
print("\n[TABLA 3] Pérdida δ_k (EMD, menor = mejor partición)")
print(f"{'n':>4} {'δ₂ (Geo)':>12} {'δ₃':>10} {'δ₄':>10} {'δ₅':>10}")
print("-" * 50)
for n in sorted(resultados):
    row = f"{n:>4}"
    for k in [2, 3, 4, 5]:
        if k in resultados[n]:
            # Lógica: Extrae la pérdida EMD de la solución; muestra "N/A" si es None
            #         (caso n < k donde no se ejecutó el análisis).
            # Sintaxis: `resultados[n][k][1]` accede al segundo elemento de la tupla
            #           (perdida); ternario `if loss is not None` maneja el caso N/A.
            loss = resultados[n][k][1]
            row += f" {loss:>10.6f}" if loss is not None else f" {'N/A':>10}"
        else:
            row += f" {'N/A':>10}"
    print(row)

# Tabla 4: Espacio de búsqueda reducido por el greedy
print("\n[TABLA 4] Reducción del espacio de búsqueda (candidatos greedy C=3 vs S(n,k))")
print(f"{'n':>4} {'S(n,3)':>10} {'speedup k=3':>14} {'S(n,4)':>10} {'speedup k=4':>14} {'S(n,5)':>10} {'speedup k=5':>14}")
print("-" * 80)
for n, _ in DATASETS:
    row = f"{n:>4}"
    for k in [3, 4, 5]:
        # Lógica: Calcula el número de Stirling S(n,k) (particiones exactas en k partes)
        #         y el speedup del greedy con C=3 candidatos vs explorar todas las particiones.
        # Sintaxis: `stirling(n, k)` retorna S(n,k); `s / 3` es el ratio de reducción;
        #           `if n >= k else 0` evita calcular S(n,k) para n < k.
        s = stirling(n, k) if n >= k else 0
        speedup = s / 3 if s > 0 else 0
        row += f" {s:>10} {speedup:>13.1f}x"
    print(row)

print("\n" + "=" * 72)
print("  Benchmark completado.")
print("=" * 72)
