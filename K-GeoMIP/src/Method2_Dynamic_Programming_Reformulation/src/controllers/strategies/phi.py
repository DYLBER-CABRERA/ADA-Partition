import time
import numpy as np
from src.funcs.base import ABECEDARY, lil_endian
from src.funcs.format import fmt_biparticion
from src.controllers.manager import Manager

import math
import collections
from collections.abc import Iterable, Mapping, MutableMapping, Sequence

# Lógica: Python 3.10+ eliminó los aliases de tipos colección de `collections` (movidos a
#         `collections.abc`). PyPhi aún los importa desde `collections` directamente, lo que
#         causa AttributeError en tiempo de ejecución. Este bloque los restaura dinámicamente.
# Sintaxis: `hasattr(obj, name)` verifica si el atributo existe; `setattr(obj, name, val)`
#           lo añade en tiempo de importación. El `if not hasattr` es idempotente — no daña Python <3.10.
if not hasattr(collections, "Iterable"):
    setattr(collections, "Iterable", Iterable)
if not hasattr(collections, "Mapping"):
    setattr(collections, "Mapping", Mapping)
if not hasattr(collections, "MutableMapping"):
    setattr(collections, "MutableMapping", MutableMapping)
if not hasattr(collections, "Sequence"):
    setattr(collections, "Sequence", Sequence)

from pyphi import Network, Subsystem
from pyphi.labels import NodeLabels
from pyphi.models.cuts import Bipartition, Part

from src.middlewares.slogger import SafeLogger
from src.middlewares.profile import profiler_manager, profile

from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.models.enums.distance import MetricDistance
from src.models.base.application import aplicacion


from src.constants.base import (
    NET_LABEL,
    TYPE_TAG,
    STR_ONE,
)
from src.constants.models import (
    DUMMY_ARR,
    DUMMY_PARTITION,
    PYPHI_LABEL,
    PYPHI_STRAREGY_TAG,
    PYPHI_ANALYSIS_TAG,
)


class Phi(SIA):
    """Class Phi is used as base for other strategies, bruteforce with pyphi."""

    def __init__(self, config: Manager) -> None:
        # Lógica: Inicializa SIA con el gestor para configurar el acceso a la TPM y los
        #         atributos base del análisis antes de añadir los específicos de Phi.
        # Sintaxis: `super().__init__(config)` llama al __init__ de SIA en la MRO;
        #           `config` es recibido como `gestor` internamente en SIA.
        super().__init__(config)
        # Lógica: Abre una sesión de profiling con el identificador de la red actual para
        #         que el reporte HTML agrupe todos los análisis de esta ejecución.
        # Sintaxis: f-string concatena NET_LABEL, longitud del estado (número de nodos)
        #           y la letra de página; `profiler_manager` es la instancia global del módulo.
        profiler_manager.start_session(
            f"{NET_LABEL}{len(config.estado_inicial)}{config.pagina}"
        )
        # Lógica: Crea el logger con el tag de estrategia Phi para distinguir sus mensajes
        #         de los de otras estrategias en los archivos de log.
        # Sintaxis: `SafeLogger(tag)` construye un logger con handlers de archivo y consola;
        #           PYPHI_STRAREGY_TAG = "Pyphi_strategy".
        self.logger = SafeLogger(PYPHI_STRAREGY_TAG)

    @profile(context={TYPE_TAG: PYPHI_ANALYSIS_TAG})
    def aplicar_estrategia(self, condiciones: str, alcance: str, mecanismo: str):
        # Lógica: Marca el inicio del análisis para calcular el tiempo total al final;
        #         se registra aquí antes de preparar_subsistema que también consume tiempo.
        # Sintaxis: `time.time()` retorna el timestamp Unix en segundos como float;
        #           se resta al `time.time()` final para obtener la duración total.
        self.sia_tiempo_inicio = time.time()
        # Lógica: Construye el Network y Subsystem de PyPhi a partir de las cadenas de bits,
        #         delegando la validación y construcción del sistema al método auxiliar.
        # Sintaxis: Desempaquetado de tupla de 3 elementos retornados por preparar_subsistema;
        #           alcance_idx y mecanismo_idx son tuplas de enteros para PyPhi.
        alcance_idx, mecanismo_idx, subsistema = self.preparar_subsistema(
            condiciones, alcance, mecanismo
        )
        # Lógica: Calcula la MIP (Minimum Information Partition) usando PyPhi según la
        #         métrica configurada — efecto (t+1) para EMD_EFECTO, causa (t) para EMD_CAUSA.
        # Sintaxis: Operador ternario `A if cond else B`; `.effect_mip` y `.cause_mip`
        #           son métodos del Subsystem de PyPhi que devuelven un objeto Mip con φ.
        mip = (
            subsistema.effect_mip(mecanismo_idx, alcance_idx)
            if aplicacion.distancia_metrica == MetricDistance.EMD_EFECTO.value
            else subsistema.cause_mip(mecanismo_idx, alcance_idx)
        )

        # Lógica: Extrae φ (small phi) del objeto Mip; representa la información integrada
        #         mínima — la pérdida al particionar el sistema de la forma óptima.
        # Sintaxis: `mip.phi` es un atributo float del objeto Mip de PyPhi.
        small_phi: float = mip.phi
        # Lógica: Inicializa distribuciones con centinelas para garantizar que Solution
        #         tenga valores válidos aunque la MIP no retorne repertorios (caso degenerado).
        # Sintaxis: `np.array(DUMMY_ARR, dtype=np.float32)` convierte [-1] a array float32.
        repertorio = np.array(DUMMY_ARR, dtype=np.float32)
        repertorio_partido = np.array(DUMMY_ARR, dtype=np.float32)
        format = DUMMY_PARTITION

        # Lógica: Solo procesa los repertorios si PyPhi los devolvió — pueden ser None
        #         si la MIP es trivial o el subsistema es degenerado.
        # Sintaxis: `is not None` es más explícito que el test de verdad `if mip.repertoire`,
        #           que fallaría con arrays NumPy vacíos (ambigüedad booleana).
        if mip.repertoire is not None and mip.partitioned_repertoire is not None:
            # Lógica: Aplana los repertorios n-dimensionales de PyPhi a vectores 1D
            #         para compatibilidad con el formato de distribución del proyecto.
            # Sintaxis: `.flatten()` crea una copia 1D del array multidimensional;
            #           a diferencia de `.ravel()` siempre retorna una copia, no una vista.
            repertorio = mip.repertoire.flatten()
            repertorio_partido = mip.partitioned_repertoire.flatten()

            # Lógica: Calcula el número de nodos (bits) del repertorio para generar la
            #         permutación de reordenamiento de PyPhi (big-endian) a little-endian.
            # Sintaxis: `math.log2(size)` retorna el logaritmo base 2 del tamaño;
            #           `int(...)` trunca al entero inferior (exacto para potencias de 2).
            states = int(math.log2(mip.repertoire.size))
            sub_estados: np.ndarray = lil_endian(states)

            # Lógica: Reordena in-place los arrays usando los índices de permutación para
            #         alinear la notación big-endian de PyPhi con la little-endian del proyecto.
            # Sintaxis: `arr.put(indices, values)` coloca `values[i]` en `arr[indices[i]]`;
            #           aquí realiza la permutación de reordenamiento de estados.
            repertorio.put(sub_estados, repertorio)
            repertorio_partido.put(sub_estados, repertorio_partido)

            # Lógica: Extrae las dos partes de la bipartición óptima calculada por PyPhi
            #         para formatearlas con la notación de partición del proyecto.
            # Sintaxis: `mejor_biparticion.parts[True]` y `parts[False]` son los dos lados
            #           de la Bipartition; `Part` tiene atributos .mechanism y .purview.
            mejor_biparticion: Bipartition = mip.partition
            prim: Part = mejor_biparticion.parts[True]
            dual: Part = mejor_biparticion.parts[False]

            prim_mech, prim_purv = prim.mechanism, prim.purview
            dual_mech, dual_purv = dual.mechanism, dual.purview
            # Lógica: Formatea la bipartición como string legible con la notación del proyecto
            #         (ej. "AB|C // DE|F") para incluirlo en la Solution final.
            # Sintaxis: `fmt_biparticion` recibe [mecanismo, alcance] para dual y primario;
            #           retorna string con separador // entre los dos lados de la bipartición.
            format = fmt_biparticion(
                [dual_mech, dual_purv],
                [prim_mech, prim_purv],
            )

        # Lógica: Construye la Solution con los resultados de PyPhi incluyendo φ,
        #         los repertorios reordenados, la bipartición formateada y el tiempo total.
        # Sintaxis: `Solution(...)` acepta keyword arguments; `time.time() - sia_tiempo_inicio`
        #           da la duración en segundos desde el inicio del análisis.
        return Solution(
            estrategia=PYPHI_LABEL,
            perdida=small_phi,
            distribucion_subsistema=repertorio,
            distribucion_particion=repertorio_partido,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=format,
        )

    def preparar_subsistema(self, condiciones: str, futuros: str, presentes: str):
        # Lógica: Convierte el estado inicial de string binario a tupla de enteros, que
        #         es el formato que PyPhi espera para el estado del sistema (no ndarray).
        # Sintaxis: Generator expression con `int(s)` convierte cada carácter '0'/'1'
        #           a entero; `tuple(gen)` materializa el generador como tupla inmutable.
        estado_inicial = tuple(int(s) for s in self.sia_gestor.estado_inicial)
        # Lógica: La longitud del estado inicial determina el número de nodos de la red;
        #         se usa para crear las etiquetas e índices de los nodos.
        # Sintaxis: `len(tuple)` retorna el número de elementos en O(1).
        longitud = len(estado_inicial)

        # Lógica: Genera las tuplas de índices (0..n-1) y etiquetas alfabéticas (A..Z...)
        #         necesarias para construir el NodeLabels de PyPhi.
        # Sintaxis: `tuple(range(n))` crea (0,1,...,n-1); `ABECEDARY[:n]` es un slice
        #           de la tupla de etiquetas generada por get_labels en funcs/base.py.
        indices = tuple(range(longitud))
        etiquetas = tuple(ABECEDARY[:longitud])

        # Lógica: Crea el objeto NodeLabels de PyPhi que mapea índices enteros a etiquetas
        #         de nodos para que las salidas de PyPhi sean legibles ('A', 'B'...).
        # Sintaxis: `NodeLabels(etiquetas, indices)` — constructor de PyPhi; etiquetas primero,
        #           índices segundo; el objeto soporta indexación y es iterable.
        completo = NodeLabels(etiquetas, indices)
        # Lógica: Carga la TPM desde el archivo CSV mediante el método heredado de SIA,
        #         que usa np.genfromtxt con el separador de columnas configurado.
        # Sintaxis: `self.sia_cargar_tpm()` retorna np.ndarray de shape (2^n, n).
        mpt_estados_nodos_on = self.sia_cargar_tpm()
        # Lógica: Construye la red PyPhi con la TPM y las etiquetas de nodos; representa
        #         el sistema completo antes de aplicar condiciones de fondo.
        # Sintaxis: `Network(tpm=arr, node_labels=labels)` — constructor de PyPhi; espera
        #           TPM en formato estado-nodo (filas=estados, columnas=nodos).
        red = Network(tpm=mpt_estados_nodos_on, node_labels=completo)
        self.sia_logger.critic("Original creado.")

        # Lógica: Aplica condiciones de fondo seleccionando solo los nodos con bit=1 en
        #         `condiciones` — los nodos con bit=0 quedan excluidos del candidato.
        # Sintaxis: Generator expression con `if bit == STR_ONE` filtra posiciones activas;
        #           `completo[i]` indexa NodeLabels para obtener la etiqueta del nodo i.
        candidato = tuple(
            completo[i] for i, bit in enumerate(condiciones) if bit == STR_ONE
        )
        self.sia_logger.critic("Candidato creado.")

        # Lógica: Construye el Subsystem de PyPhi fijando el estado inicial y los nodos
        #         del candidato; PyPhi internamente condiciona y construye la red reducida.
        # Sintaxis: `Subsystem(network, state, nodes)` — el `state` debe ser tupla de enteros
        #           y `nodes` una tupla de etiquetas NodeLabels del candidato.
        subsistema = Subsystem(network=red, state=estado_inicial, nodes=candidato)
        self.sia_logger.critic("Subsistema creado.")
        # Lógica: Extrae los índices de alcance (futuro) como la intersección de los nodos
        #         activos en `futuros` Y en `condiciones` — solo los que sobreviven a ambos filtros.
        # Sintaxis: `enumerate(zip(A, B))` itera pares (índice, (bitA, bitB)) en paralelo;
        #           la doble condición `(bit==1) and (cond==1)` implementa la intersección lógica.
        alcance = tuple(
            ind
            for ind, (bit, cond) in enumerate(zip(futuros, condiciones))
            if (bit == STR_ONE) and (cond == STR_ONE)
        )
        # Lógica: Análogo al alcance para el mecanismo (presente); solo los nodos activos
        #         en `presentes` Y en `condiciones` forman el mecanismo del análisis.
        # Sintaxis: Mismo patrón de generator expression con doble filtro booleano.
        mecanismo = tuple(
            ind
            for ind, (bit, cond) in enumerate(zip(presentes, condiciones))
            if (bit == STR_ONE) and (cond == STR_ONE)
        )

        # Lógica: Retorna los tres elementos necesarios para que aplicar_estrategia llame
        #         a effect_mip/cause_mip de PyPhi con los índices y subsistema correctos.
        # Sintaxis: `return A, B, C` retorna tupla de 3 que se desempaqueta en el llamador
        #           con `alcance_idx, mecanismo_idx, subsistema = self.preparar_subsistema(...)`.
        return alcance, mecanismo, subsistema
