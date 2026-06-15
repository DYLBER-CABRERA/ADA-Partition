import sys
from pathlib import Path
import numpy as np
import pytest

# Lógica: Deshabilita colorama antes de que pytest capture stdout.
#         colorama.init() es llamado por solution.py al importarse; su wrapper ANSI→Win32
#         sobre sys.stdout entra en conflicto con la captura de pytest en Windows.
# Sintaxis: `colorama.deinit()` restaura sys.stdout/stderr al stream original del SO.
try:
    import colorama
    colorama.deinit()
except ImportError:
    pass

# Lógica: Garantiza que `Method2_Dynamic_Programming_Reformulation/` esté en sys.path
#         para que los imports `from src.xxx` funcionen independientemente del directorio de trabajo.
# Sintaxis: `Path(__file__).resolve().parent.parent` sube dos niveles:
#           tests/ → Method2_Dynamic_Programming_Reformulation/
_RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
if str(_RAIZ_PROYECTO) not in sys.path:
    # Lógica: Inserta la raíz en la posición 0 para que tenga prioridad sobre otros paths.
    # Sintaxis: `sys.path.insert(0, str)` — posición 0 = mayor prioridad en la búsqueda de módulos.
    sys.path.insert(0, str(_RAIZ_PROYECTO))

# Lógica: Ruta al directorio de muestras TPM del proyecto (K-GeoMIP/data/samples/).
#         Se obtiene subiendo 3 niveles desde tests/: Method2/ → src/ → K-GeoMIP/
# Sintaxis: `parents[2]` retorna el tercer ancestro del archivo conftest.py.
_SAMPLES_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "samples"


# ── Fixtures de TPM (cargadas una vez por módulo de test) ────────────────────

@pytest.fixture(scope="module")
def tpm_n4() -> np.ndarray:
    # Lógica: Carga la TPM del sistema de 4 variables (N4A.csv) como array NumPy float64.
    #         scope="module" garantiza que el CSV se lee solo una vez para todos los tests del módulo.
    # Sintaxis: `np.genfromtxt(path, delimiter=",")` parsea el CSV sin encabezado a ndarray.
    return np.genfromtxt(_SAMPLES_DIR / "N4A.csv", delimiter=",")


@pytest.fixture(scope="module")
def tpm_n6() -> np.ndarray:
    # Lógica: Carga la TPM del sistema de 6 variables (N6A.csv) — usada en tests de rendimiento.
    # Sintaxis: Mismo patrón que tpm_n4; N6A.csv tiene 64 filas × 6 columnas.
    return np.genfromtxt(_SAMPLES_DIR / "N6A.csv", delimiter=",")


# ── Fixtures de Manager ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def gestor_n4():
    # Lógica: Crea un Manager para el sistema de 4 variables.
    #         Manager auto-resuelve la ruta de la TPM desde K-GeoMIP/data/samples/.
    # Sintaxis: Import local dentro del fixture — evita ImportError si el módulo no está en path al cargar conftest.
    from src.controllers.manager import Manager
    return Manager(estado_inicial="1000")


@pytest.fixture(scope="module")
def gestor_n6():
    # Lógica: Crea un Manager para el sistema de 6 variables (n=6 garantiza S(6,3)=90 para el test de speedup).
    # Sintaxis: `estado_inicial="100000"` — cadena binaria de longitud 6 con el bit más significativo en 1.
    from src.controllers.manager import Manager
    return Manager(estado_inicial="100000")
