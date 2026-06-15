# ── Constantes de sistema general ───────────────────────────────────────────
# Lógica: Valores centinela para señalizar errores o ausencia de resultados
#         en particiones y arrays, sin lanzar excepciones.
# Sintaxis: `int` y `list[int]` con valores -1 son convención para "no válido";
#           `str` con mensajes descriptivos se usan en logs y outputs de consola.
DUMMY_EMD: int = -1
DUMMY_ARR: list[int] = [-1]
ERROR_PARTITION: str = "No hay suficientes elementos para particionar.\n"
DUMMY_PARTITION: str = "NO-PARTITION\n"

# ── SIA (System Irreducibility Analysis) ─────────────────────────────────────
# Lógica: Etiquetas para el módulo SIA base. SIA_LABEL es el identificador corto;
#         SIA_PREPARATION_TAG identifica específicamente la fase de preparación
#         del subsistema en logs y reportes de profiling.
# Sintaxis: f-string `f"{SIA_LABEL}_preparation"` concatena el label con el sufijo
#           en tiempo de definición del módulo — evaluación estática al importar.
SIA_LABEL: str = "sia"
SIA_PREPARATION_TAG: str = f"{SIA_LABEL}_preparation"


# ── Fuerza Bruta ─────────────────────────────────────────────────────────────
# Lógica: Etiquetas para la estrategia BruteForce. Separa el label legible
#         (BRUTEFORCE_LABEL) de los tags de logging/profiling (sufijos _strategy,
#         _analysis, _full_analysis) para modularidad en los reportes.
# Sintaxis: Tres f-strings derivados del mismo BRUTEFORCE_LABEL base garantizan
#           consistencia — cambiar el label actualiza automáticamente todos los tags.
BRUTEFORCE_LABEL: str = "BruteForce"
BRUTEFORCE_STRAREGY_TAG: str = f"{BRUTEFORCE_LABEL}_strategy"
BRUTEFORCE_ANALYSIS_TAG: str = f"{BRUTEFORCE_LABEL}_analysis"
BRUTEFORCE_FULL_ANALYSIS_TAG: str = f"{BRUTEFORCE_LABEL}_full_analysis"

# ── Pyphi ────────────────────────────────────────────────────────────────────
# Lógica: Etiquetas para la integración con la librería PyPhi (cálculo de Φ).
#         Permite distinguir sus resultados de los de las estrategias propias
#         en logs y comparativas de rendimiento.
# Sintaxis: Mismo patrón de f-strings derivados de la constante label base.
PYPHI_LABEL: str = "Pyphi"
PYPHI_STRAREGY_TAG: str = f"{PYPHI_LABEL}_strategy"
PYPHI_ANALYSIS_TAG: str = f"{PYPHI_LABEL}_analysis"

# ── Q-Nodes ──────────────────────────────────────────────────────────────────
# Lógica: Etiquetas para la estrategia Q-Nodes, una heurística de bi-partición
#         basada en nodos de corte (Q-nodes) del grafo del subsistema.
# Sintaxis: Igual patrón de derivación desde QNODES_LABEL.
QNODES_LABEL: str = "Q-Nodes"
QNODES_STRAREGY_TAG: str = f"{QNODES_LABEL}_strategy"
QNODES_ANALYSIS_TAG: str = f"{QNODES_LABEL}_analysis"

# ── Geometric (bi-particiones, k=2) ──────────────────────────────────────────
# Lógica: Etiquetas para GeometricSIA, la estrategia exacta de bi-partición
#         usando BFS sobre el hipercubo de estados con tabla de costos geométrica.
#         Es el algoritmo de referencia para k=2 en el proyecto.
# Sintaxis: Patrón consistente con los demás módulos para uniformidad en logs.
GEOMETRIC_LABEL: str = "Geometric"
GEOMETRIC_STRAREGY_TAG: str = f"{GEOMETRIC_LABEL}_strategy"
GEOMETRIC_ANALYSIS_TAG: str = f"{GEOMETRIC_LABEL}_analysis"

# ── K-GeoMIP (k-particiones, k ∈ {2,3,4,5}) ──────────────────────────────────
# Lógica: Etiquetas para KGeometricSIA, la extensión a k-particiones con
#         heurística greedy. K_MIN=2 es la bi-partición mínima (exacta);
#         K_MAX=5 es el límite superior soportado por la implementación actual.
# Sintaxis: K_MIN y K_MAX como `int` anotados explícitamente — se usan en
#           guards de validación (`if not (K_MIN <= k <= K_MAX)`) y como defaults.
KGEOMETRIC_LABEL: str = "KGeometric"
KGEOMETRIC_STRATEGY_TAG: str = f"{KGEOMETRIC_LABEL}_strategy"
KGEOMETRIC_ANALYSIS_TAG: str = f"{KGEOMETRIC_LABEL}_analysis"
K_MIN: int = 2
K_MAX: int = 5
