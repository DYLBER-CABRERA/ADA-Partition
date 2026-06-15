import numpy as np

# ── Valores infinitos ────────────────────────────────────────────────────────
# Lógica: Representan ±∞ como floats Python nativos para inicializar comparaciones
#         de mínimo/máximo sin depender de valores de dominio específicos.
# Sintaxis: `float("inf")` y `float("-inf")` son los constructores canónicos de
#           infinito en Python; equivalen a `math.inf` y `-math.inf`.
INFTY_POS: float = float("inf")
INFTY_NEG: float = float("-inf")

# ── Constantes enteras y flotantes base ─────────────────────────────────────
# Lógica: Definen cero y uno como constantes tipadas para evitar literales mágicos
#         y garantizar consistencia de tipo en operaciones numéricas del sistema.
# Sintaxis: `int(0)` e `int(1)` son redundantes pero documentan explícitamente
#           que el tipo esperado es int; `float(INT_ONE)` convierte int → float.
INT_ZERO: int = int(0)
INT_ONE: int = int(1)

FLOAT_ONE: float = float(INT_ONE)
FLOAT_ZERO: float = float(INT_ZERO)

# Lógica: BASE_TWO es la base del sistema binario usado en todo el proyecto.
#         Definirlo como suma de constantes existentes evita el literal mágico 2.
# Sintaxis: `INT_ONE + INT_ONE` produce 2 como int; equivale a `int(2)` pero
#           expresa la derivación desde las constantes ya definidas.
BASE_TWO: int = INT_ONE + INT_ONE

# ── Constantes de indexación ─────────────────────────────────────────────────
# Lógica: ABC_LEN es el tamaño del alfabeto estándar (A-Z). LAST_IDX es el índice
#         de último elemento en listas/arrays usando notación Python negativa.
#         ROWS_IDX/COLS_IDX y ACTUAL/EFECTO son aliases semánticos del mismo par
#         de constantes (0 y 1) usados en contextos distintos del código.
# Sintaxis: Asignaciones múltiples en una línea `A = B = valor` en Python asignan
#           el mismo objeto a múltiples nombres simultáneamente (no copias).
ABC_LEN: int = 26
LAST_IDX: int = -INT_ONE
ROWS_IDX = ACTUAL = INT_ZERO
COLS_IDX = EFECTO = INT_ONE

# ── Constantes de cadenas de texto ──────────────────────────────────────────
# Lógica: Versiones string de 0 y 1 para comparaciones con cadenas binarias del
#         tipo "1010" que representan estados del sistema. Evitan conversiones
#         repetidas y hacen explícito que se compara con caracteres, no enteros.
# Sintaxis: `str(INT_ZERO)` convierte el int 0 al string "0"; más legible que "0"
#           porque vincula la constante string a su equivalente entero.
STR_ZERO: str = str(INT_ZERO)
STR_ONE: str = str(INT_ONE)

# Lógica: Constantes de strings especiales usados en formateo y representación:
#         EMPTY_STR para concatenación neutra, COLON_DELIM para CSVs,
#         VOID_STR para representar conjuntos vacíos (∅), SMALL_PHI_STR para φ,
#         ABC_START como punto de partida del abecedario en generación de etiquetas.
# Sintaxis: Literales de string; los caracteres Unicode (∅, φ) se incluyen directamente
#           en el source UTF-8 — Python 3 maneja Unicode nativamente en strings.
EMPTY_STR: str = ""
COLON_DELIM: str = ","
VOID_STR: str = "∅"
SMALL_PHI_STR: str = "φ"
ABC_START: str = "A"

# ── Símbolos de comparación y separación ────────────────────────────────────
# Lógica: Símbolos Unicode usados en la visualización de particiones y resultados.
#         Distinguir entre ≡ (equivalencia), = (igualdad), —/–/- (guiones de
#         distinto ancho) permite un formateo tipográfico preciso en la consola.
# Sintaxis: Strings de un solo carácter Unicode; el tipo `str` de Python maneja
#           caracteres multi-byte de forma transparente gracias a UTF-8.
EQUIV_SYM: str = "≡"
EQUAL_SYM: str = "="
DASH_SYM: str = "—"
MINUS_SYM: str = "–"
LINE_SYM: str = "-"

# Lógica: EQUITIES es una tupla de símbolos de (des)igualdad usados en comparaciones
#         visuales de particiones. NEQ_SYM representa "no igual" (≠).
# Sintaxis: Tupla de strings sin nombre de variable por elemento — se accede por índice.
#           La coma final en `"≒"` no es necesaria pero es válida en Python.
EQUITIES = "≌", "≆", "≇", "≄", "≒"
NEQ_SYM: str = "≠"

# ── Representación binaria ───────────────────────────────────────────────────
# Lógica: BITS es la tupla de los dos valores posibles en el sistema binario (0 y 1).
#         ACTIVOS/INACTIVOS son flags booleanos para el modo de estados del sistema:
#         ACTIVOS=True significa que se trabaja con estados activos (valor 1),
#         INACTIVOS=False con estados inactivos (valor 0).
# Sintaxis: `tuple[int, int]` es la anotación de tipo PEP 585 para tupla de dos ints.
#           `True` y `False` son los singletons booleanos de Python.
BITS: tuple[int, int] = (0, 1)
ACTIVOS, INACTIVOS = True, False

# ── Etiquetas y rutas del sistema ────────────────────────────────────────────
# Lógica: NET_LABEL identifica el sistema de red en logs y outputs.
#         Las rutas (LOGS_PATH, SAMPLES_PATH, PROFILING_PATH, RESOLVER_PATH) definen
#         la estructura de directorios del proyecto para almacenar datos y resultados.
#         Son relativas al directorio de ejecución (Method2_Dynamic_Programming_Reformulation/).
# Sintaxis: Strings literales de ruta; se usan con `Path(...)` de pathlib para
#           construir rutas absolutas en tiempo de ejecución según el SO.
NET_LABEL: str = "NET"
LOGS_PATH: str = ".logs"
SAMPLES_PATH: str = "src/.samples/"
PROFILING_PATH: str = "review/profiling"
RESOLVER_PATH: str = "review/resolver"

# ── Extensiones de archivo ───────────────────────────────────────────────────
# Lógica: Extensiones tipadas como constantes para evitar strings mágicos en el
#         código de I/O. Facilitan cambiar el formato de salida en un solo lugar.
# Sintaxis: Strings sin punto inicial — se concatenan con "." en el código que
#           construye nombres de archivo (ej: f"N{n}{suffix}.{CSV_EXTENSION}").
CSV_EXTENSION: str = "csv"
HTML_EXTENSION: str = "html"
EXCEL_EXTENSION: str = "xlsx"

# ── Etiqueta de tipo para contexto de profiling ──────────────────────────────
# Lógica: TYPE_TAG es la clave usada en los diccionarios de contexto del decorador
#         @profile para identificar el tipo de análisis en los reportes de profiling.
# Sintaxis: String literal sin tipo anotado explícitamente — el tipo se infiere
#           como `str` por el linter/mypy según el valor asignado.
TYPE_TAG = "type"
