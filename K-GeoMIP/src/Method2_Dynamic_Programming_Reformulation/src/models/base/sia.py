from abc import ABC, abstractmethod
import time

import numpy as np
import numpy.typing as NDArray

from src.constants.models import SIA_PREPARATION_TAG
from src.middlewares.slogger import SafeLogger
from src.controllers.manager import Manager
from src.models.core.system import System

from src.constants.base import (
    COLON_DELIM,
    FLOAT_ZERO,
    STR_ZERO,
)
from src.constants.error import (
    ERROR_INCOMPATIBLE_SIZES,
)


class SIA(ABC):
    """
    La clase SIA es la encargada de albergar como madre todos los diferentes algoritmos desarrollados, planteando la base de la que con el método `preparar_subsistema` 
    se obtendrá uno con características indicadas por el usuario.

    Args:
    ----
        - config (Loader): El cargador de la data desde las muestras con las matrices, es relevante recordar que este tiene el estado inicial como cadena, por lo que 
            es crucial su transoformación a `np.array(...)` para capacidad de indexar datos.
        - `sia_debug_observer` (DebugObserver): Debugger que no afecte el rendimiento de la ejecución para un sistema.
        - `sia_logger` (Logger): Imprime datos de la ejecución en `logs/<fecha>/<hora>/` asociando una hora específica por cada fecha del año,
            allí agrupa el resultado de la ejecución de los distintos loggers situados en aplicativo. De esta forma por hora se almacenará el último resultado de la ejecución.
        - `sia_subsistema` (System): El subsistema resultante de la preparación, es almacenado para tener una copia reutilizable en el proceso de particionamiento.
        - `sia_dists_marginales` (np.ndarray): Igualmente, una copia con fines de reutilización durante cálculos con la EMD.
    """

    def __init__(self, gestor: Manager) -> None:
        # Lógica: Almacena el gestor (Manager) que provee acceso a la TPM y al estado
        #         inicial. Es el único punto de acceso a los datos del sistema desde SIA.
        # Sintaxis: Asignación directa de atributo de instancia; el prefijo `sia_` en todos
        #           los atributos evita colisiones de nombres con las subclases herederas.
        self.sia_gestor = gestor
        self.sia_logger = SafeLogger(SIA_PREPARATION_TAG)

        # Lógica: Declaraciones de tipo sin inicialización — se asignan en `sia_preparar_subsistema`.
        #         `sia_subsistema` es el System resultante del condicionamiento y sustracción.
        #         `sia_dists_marginales` es la distribución de probabilidad marginal del subsistema.
        #         `sia_tiempo_inicio` marca el inicio del análisis para medir tiempo de ejecución.
        # Sintaxis: `self.attr: Type` sin `=` es una anotación de tipo (PEP 526) sin asignación;
        #           indica al linter/mypy el tipo esperado sin inicializar el atributo todavía.
        self.sia_subsistema: System
        self.sia_dists_marginales: NDArray[np.float32]
        self.sia_tiempo_inicio: float = FLOAT_ZERO

    @abstractmethod
    def aplicar_estrategia(self):
        """
        Método principal sobre el que las clases herederas implementarán su algoritmo de resolución del problema con una metodología determinada.
        """

    def sia_cargar_tpm(self) -> np.ndarray:
        """Carga TPM desde archivo"""
        return np.genfromtxt(
            self.sia_gestor.tpm_filename,
            delimiter=COLON_DELIM,
        )

    def sia_preparar_subsistema(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray #! COMENTAR PARA UN SOLO ESTADO INICIAL
    ):
        """Es en este método donde dada la entrada del usuario, vamos a generar un sistema completo, aplicamos condiciones de fondo (background conditions),
        lo substraemos partes para dejar un subsistema y es este el que retornamos pues este es el mínimo "sistema" útil para poder encontrar la bipartición que le genere la menor pérdida.

        Args:
            - `condicion` (str): Cadena de bits donde los bits en cero serán las dimensiones a condicionar.
            - `alcance` (str): Cadena de bits donde los bits en cero serán las dimensiones a substraer del alcance .
            - `mecanismo` (str): Cadena de bits donde los bits en cero serán las dimensiones a substraer del mecanismo.

        Raises:
            - `Exception:` Es crucial que todos tengan el mismo tamaño del estado inicial para correctamente identificar los índices y valor de cada variable rápidamente.
        """
        # Lógica: Valida que condicion, alcance y mecanismo tengan la misma longitud que
        #         el estado inicial. Si difieren, los índices de bits no tendrían correspondencia
        #         con las variables del sistema y los resultados serían incorrectos.
        # Sintaxis: `chequear_parametros` retorna True si hay error; `raise Exception` lanza
        #           la excepción con el mensaje de error importado de constants.error.
        if self.chequear_parametros(condicion, alcance, mecanismo):
            raise Exception(ERROR_INCOMPATIBLE_SIZES)

        # Lógica: Convierte las cadenas binarias a arrays de índices de dimensiones activas.
        #         Un bit "0" en la cadena significa "esta dimensión se substrae/condiciona".
        #         Los índices (posiciones de los 0s) son los que se eliminan del sistema.
        # Sintaxis: List comprehension con `enumerate` produce pares (índice, bit);
        #           `if bit == STR_ZERO` filtra solo las posiciones con "0".
        #           `dtype=np.int8` usa el tipo más compacto para arrays de índices ≤127.
        dims_condicionadas = np.array(
            [ind for ind, bit in enumerate(condicion) if bit == STR_ZERO], dtype=np.int8
        )
        dims_alcance = np.array(
            [ind for ind, bit in enumerate(alcance) if bit == STR_ZERO], dtype=np.int8
        )
        dims_mecanismo = np.array(
            [ind for ind, bit in enumerate(mecanismo) if bit == STR_ZERO], dtype=np.int8
        )

        # Lógica: Crea el directorio de salida para logs y resultados del análisis actual.
        #         El directorio es único por configuración (N+página+estado_inicial).
        # Sintaxis: `.mkdir(parents=True, exist_ok=True)` crea la ruta completa sin error
        #           si ya existe — equivalente a `mkdir -p` en Unix.
        self.sia_gestor.output_dir.mkdir(parents=True, exist_ok=True)

        # Lógica: Convierte el estado inicial de string binario ("1000...") a array NumPy
        #         de int8 para poder usarlo como índice en las operaciones del sistema.
        #         Ejemplo: "1000" → array([1, 0, 0, 0], dtype=int8)
        # Sintaxis: List comprehension sobre el string — en Python, iterar un string
        #           produce sus caracteres individuales; `dtype=np.int8` los convierte a int.
        estado_inicial = np.array(
            [canal for canal in self.sia_gestor.estado_inicial], dtype=np.int8
        )

        # Lógica: Pipeline de construcción del subsistema en tres fases:
        #         1. `System(tpm, estado_inicial)` — sistema completo con todos los nodos.
        #         2. `.condicionar(dims_condicionadas)` — aplica background conditions,
        #            fijando las dimensiones condicionadas al valor de su estado inicial.
        #         3. `.substraer(dims_alcance, dims_mecanismo)` — marginaliza las dimensiones
        #            substradas del alcance (t+1) y mecanismo (t), dejando el subsistema mínimo.
        # Sintaxis: Cada método retorna un nuevo objeto System (inmutable); el encadenamiento
        #           produce el subsistema sin modificar los objetos intermedios.
        completo = System(tpm, estado_inicial)
        self.sia_logger.critic("Original creado.")
        self.sia_logger.critic("Original:")

        candidato = completo.condicionar(dims_condicionadas)
        self.sia_logger.critic("Candidato creado.")

        subsistema = candidato.substraer(dims_alcance, dims_mecanismo)
        self.sia_logger.critic("Subsistema creado.")

        # Lógica: Almacena el subsistema y su distribución marginal como atributos de instancia
        #         para que las subclases (GeometricSIA, KGeometricSIA) los usen en el análisis.
        #         `sia_tiempo_inicio` marca el inicio del cómputo de la estrategia.
        # Sintaxis: `time.time()` retorna el timestamp Unix en segundos como float;
        #           se resta al final de la ejecución para calcular tiempo transcurrido.
        self.sia_subsistema = subsistema
        self.sia_dists_marginales = subsistema.distribucion_marginal()
        self.sia_tiempo_inicio = time.time()

    def chequear_parametros(self, candidato: str, futuro: str, presente: str):
        """Valida que los datos enviados por el usuario sean correctos, donde no hay problema si tienen la misma longitud puesto se están asignando los valores correspondientes a cada variable.

        Args:
            `candidato` (str): Cadena de texto que representa la presencia o ausencia de un conjunto de variables que serán enviadas para condicionar el sistema original dejándolo como un Sistema candidato, si su bit asociado equivale a 0 se condiciona la variable, si equivale a 1 esta variable se mantendrá en el sistema durante toda la ejecución (hasta que un subsistema la marginalice).
            `futuro` (str): Cadena de texto que representa la presencia o ausencia de un conjunto de variables que serán enviadas para substraer en el alcance del Sistema candidato dejándo un Subsistema, si su bit asociado equivale a 0 la variable será marginalizada, si equivale a 1 la variable se mantendrá en el Sistema candidato durante toda la ejecución (hasta que una partición la marginalice).
            `presente` (str): Cadena de texto que representa la presencia o ausencia de un conjunto de variables que serán enviadas para substraer en el mecanismo del Sistema candidato dejándolo como un Subsistema, si su bit asociado equivale a 0 la variable será marginalizada, si equivale a 1 la variable se mantendrá en el Sistema candidato durante toda la ejecución (hasta que una partición la marginalice).

        Returns:
            bool: True si las dimensiones son diferentes, de otra forma los parámetros enviados son válidos (y depende si existe la red asociada).
        """
        return not (
            len(self.sia_gestor.estado_inicial)
            == len(candidato)
            == len(futuro)
            == len(presente)
        )
