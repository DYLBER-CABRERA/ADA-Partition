import time
from typing import Union
import numpy as np
from src.middlewares.slogger import SafeLogger
from src.funcs.iit import emd_efecto, ABECEDARY
from src.middlewares.profile import gestor_perfilado, profile
from src.funcs.format import fmt_biparticion_q
from src.models.base.sia import SIA

from src.models.core.solution import Solution
from src.constants.models import (
    QNODES_ANALYSIS_TAG,
    QNODES_LABEL,
    QNODES_STRAREGY_TAG,
)
from src.constants.base import (
    COLS_IDX,
    INT_ZERO,
    TYPE_TAG,
    NET_LABEL,
    INFTY_POS,
    LAST_IDX,
    EFFECT,
    ACTUAL,
)
from src.models.base.application import aplicacion


class QNodes(SIA):
    """
    Clase QNodes para el análisis de redes mediante el algoritmo Q.

    Esta clase implementa un gestor principal para el análisis de redes que utiliza
    el algoritmo Q para encontrar la partición óptima que minimiza la
    pérdida de información en el sistema. Hereda de la clase base SIA (Sistema de
    Información Activo) y proporciona funcionalidades para analizar la estructura
    y dinámica de la red.

    Args:
    ----
        config (Loader):
            Instancia de la clase Loader que contiene la configuración del sistema
            y los parámetros necesarios para el análisis.

    Attributes:
    ----------
        m (int):
            Número de elementos en el conjunto de purview (vista).

        n (int):
            Número de elementos en el conjunto de mecanismos.

        tiempos (tuple[np.ndarray, np.ndarray]):
            Tupla de dos arrays que representan los tiempos para los estados
            actual y efecto del sistema.

        etiquetas (list[tuple]):
            Lista de tuplas conteniendo las etiquetas para los nodos,
            con versiones en minúsculas y mayúsculas del abecedario.

        vertices (set[tuple]):
            Conjunto de vértices que representan los nodos de la red,
            donde cada vértice es una tupla (tiempo, índice).

        memoria (dict):
            Diccionario para almacenar resultados intermedios y finales
            del análisis (memoización).

        logger:
            Instancia del logger configurada para el análisis Q.

    Methods:
    -------
        run(condicion, purview, mechanism):
            Ejecuta el análisis principal de la red con las condiciones,
            purview y mecanismo especificados.

        algorithm(vertices):
            Implementa el algoritmo Q para encontrar la partición
            óptima del sistema.

        funcion_submodular(deltas, omegas):
            Calcula la función submodular para evaluar particiones candidatas.

        view_solution(mip):
            Visualiza la solución encontrada en términos de las particiones
            y sus valores asociados.

        nodes_complement(nodes):
            Obtiene el complemento de un conjunto de nodos respecto a todos
            los vértices del sistema.

    Notes:
    -----
    - La clase implementa una versión secuencial del algoritmo Q para encontrar
      la partición que minimiza la pérdida de información.
    - Utiliza memoización para evitar recálculos innecesarios durante el proceso.
    - El análisis se realiza considerando dos tiempos: actual (presente) y
      efecto (futuro).
    - Optimización v2: poda temprana entre fases cuando δ=0 y memoización
      cruzada de biparticiones en funcion_submodular.
    """

    def __init__(self, tpm: np.ndarray):
        super().__init__(tpm)
        gestor_perfilado.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{aplicacion.pagina_red_muestra}"
        )
        self.m: int
        self.n: int
        self.tiempos: tuple[np.ndarray, np.ndarray]
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        self.vertices: set[tuple]
        self.clave_submodular = [], []
        self.memoria_delta = {}
        self.memoria_grupo_candidato = {}
        # Optimización: caché de biparticiones ya computadas
        self.memoria_biparticion: dict[tuple, tuple[float, np.ndarray]] = {}

        self.indices_alcance: np.ndarray
        self.indices_mecanismo: np.ndarray

        self.logger = SafeLogger(QNODES_STRAREGY_TAG)

    def aplicar_estrategia(
        self,
        estado_inicial: str,
        condicion: str,
        alcance: str,
        mecanismo: str,
    ):
        self.sia_preparar_subsistema(estado_inicial, condicion, alcance, mecanismo)

        # e.g. (1,0)=A (1,1)=B (1,2)=C #
        futuro = tuple(
            (EFFECT, idx_efecto) for idx_efecto in self.sia_subsistema.indices_ncubos
        )

        # e.g. (0,0)=a (0,2)=c (0,4)=e #
        presente = tuple(
            (ACTUAL, idx_actual) for idx_actual in self.sia_subsistema.dims_ncubos
        )

        self.m = self.sia_subsistema.indices_ncubos.size
        self.n = self.sia_subsistema.dims_ncubos.size

        self.indices_alcance = self.sia_subsistema.indices_ncubos
        self.indices_mecanismo = self.sia_subsistema.dims_ncubos

        self.tiempos = (
            np.zeros(self.n, dtype=np.int8),
            np.zeros(self.m, dtype=np.int8),
        )

        vertices = list(presente + futuro)
        self.vertices = set(presente + futuro)
        mip = self.algorithm(vertices)

        fmt_mip = fmt_biparticion_q(list(mip), self.nodes_complement(mip))
        perdida_mip, dist_marginal_mip = self.memoria_grupo_candidato[mip]

        return Solution(
            estrategia=QNODES_LABEL,
            perdida=perdida_mip,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist_marginal_mip,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
            quiere_hablar=False,
        )

    @profile(context={TYPE_TAG: QNODES_ANALYSIS_TAG})
    def algorithm(self, vertices: list[tuple[int, int]]):
        """
        Implementa el algoritmo Q optimizado para encontrar la partición óptima
        de un sistema que minimiza la pérdida de información.
        """
        # Validación de seguridad: si no hay vértices, no podemos particionar.
        if not vertices or len(vertices) < 2:
            self.logger.warning("Sistema vacío o insuficiente, omitiendo cálculo.")
            return None

        indice_emd = INT_ZERO

        for i in range(len(vertices) - 1):

            # ── Optimización 1: Poda temprana entre fases ──────────────────────
            # Si ya tenemos una partición con δ=0 en memoria, no hay nada mejor.
            for clave_mem, (emd_mem, _) in self.memoria_grupo_candidato.items():
                if emd_mem == INT_ZERO:
                    return clave_mem
            # ───────────────────────────────────────────────────────────────────

            omegas_ciclo = [vertices[0]]
            deltas_ciclo = vertices[1:]

            emd_particion_candidata = INFTY_POS
            dist_particion_candidata = None

            for j in range(len(deltas_ciclo) - 1):
                emd_local = 1e5
                indice_mip: int

                for k in range(len(deltas_ciclo)):
                    emd_union, emd_delta, dist_marginal_delta = self.funcion_submodular(
                        deltas_ciclo[k], omegas_ciclo
                    )

                    emd_iteracion = emd_union - emd_delta

                    if emd_iteracion < emd_local:
                        if emd_delta == INT_ZERO:
                            clave = (
                                tuple(deltas_ciclo[k])
                                if isinstance(deltas_ciclo[k], list)
                                else (deltas_ciclo[k],)
                            )
                            self.memoria_grupo_candidato[clave] = (
                                emd_delta,
                                dist_marginal_delta,
                            )
                            return clave

                        emd_local = emd_iteracion
                        indice_mip = k
                        emd_particion_candidata = emd_delta
                        dist_particion_candidata = dist_marginal_delta

                omegas_ciclo.append(deltas_ciclo[indice_mip])
                deltas_ciclo.pop(indice_mip)

            self.memoria_grupo_candidato[
                tuple(
                    deltas_ciclo[LAST_IDX]
                    if isinstance(deltas_ciclo[LAST_IDX], list)
                    else deltas_ciclo
                )
            ] = emd_particion_candidata, dist_particion_candidata

            par_candidato = (
                [omegas_ciclo[LAST_IDX]]
                if isinstance(omegas_ciclo[LAST_IDX], tuple)
                else omegas_ciclo[LAST_IDX]
            ) + (
                deltas_ciclo[LAST_IDX]
                if isinstance(deltas_ciclo[LAST_IDX], list)
                else deltas_ciclo
            )

            omegas_ciclo.pop()
            omegas_ciclo.append(par_candidato)

            vertices = omegas_ciclo

        return min(
            self.memoria_grupo_candidato,
            key=lambda k: self.memoria_grupo_candidato[k][indice_emd],
        )

    def funcion_submodular(
        self, deltas: Union[tuple, list[tuple]], omegas: list[Union[tuple, list[tuple]]]
    ):
        """
        Evalúa el impacto de combinar delta con omega calculando la diferencia
        de EMD entre la combinación y el delta individual.

        Optimización v2: las biparticiones se memoizan en `memoria_biparticion`
        indexadas por (tuple(alcance), tuple(mecanismo)) para evitar recalcular
        la misma bipartición en distintas iteraciones o fases.

        Args:
            deltas: Un nodo individual (tupla) o grupo de nodos (lista de tuplas).
            omegas: Lista de nodos ya agrupados.

        Returns:
            tuple: (emd_union, emd_delta, dist_marginal_delta)
        """
        vector_delta_marginal = None
        self.clave_submodular = [], []

        # ── Delta ──────────────────────────────────────────────────────────────
        clave_delta_actual, clave_delta_efecto = self.definir_clave(deltas)
        clave_delta = tuple(clave_delta_actual), tuple(clave_delta_efecto)

        idxs_alcance_delta = self.clave_submodular[EFFECT]
        dims_mecanismo_delta = self.clave_submodular[ACTUAL]

        if clave_delta not in self.memoria_delta:
            # Optimización 2: revisar también memoria_biparticion antes de calcular
            if clave_delta not in self.memoria_biparticion:
                particion_delta = self.sia_subsistema.bipartir(
                    np.array(idxs_alcance_delta, dtype=np.int8),
                    np.array(dims_mecanismo_delta, dtype=np.int8),
                )
                vector_delta_marginal = particion_delta.distribucion_marginal()
                emd_delta = emd_efecto(vector_delta_marginal, self.sia_dists_marginales)
                self.memoria_biparticion[clave_delta] = emd_delta, vector_delta_marginal
            else:
                emd_delta, vector_delta_marginal = self.memoria_biparticion[clave_delta]

            self.memoria_delta[clave_delta] = emd_delta, vector_delta_marginal
        else:
            emd_delta, vector_delta_marginal = self.memoria_delta[clave_delta]

        # ── Unión ──────────────────────────────────────────────────────────────
        for omega in omegas:
            self.definir_clave(omega)

        idxs_alcance_union = self.clave_submodular[EFFECT]
        dims_mecanismo_union = self.clave_submodular[ACTUAL]

        clave_union = tuple(sorted(idxs_alcance_union)), tuple(sorted(dims_mecanismo_union))

        if clave_union not in self.memoria_biparticion:
            particion_union = self.sia_subsistema.bipartir(
                np.array(idxs_alcance_union, dtype=np.int8),
                np.array(dims_mecanismo_union, dtype=np.int8),
            )
            vector_union_marginal = particion_union.distribucion_marginal()
            emd_union = emd_efecto(vector_union_marginal, self.sia_dists_marginales)
            self.memoria_biparticion[clave_union] = emd_union, vector_union_marginal
        else:
            emd_union, _ = self.memoria_biparticion[clave_union]

        return emd_union, emd_delta, vector_delta_marginal

    def definir_clave(
        self,
        conjunto: Union[tuple[int, int], list[tuple[int, int]]],
    ):
        if isinstance(conjunto, tuple):
            tiempo, indice = conjunto
            self.clave_submodular[tiempo].append(indice)
        else:
            for tiempo, indice in conjunto:
                self.clave_submodular[tiempo].append(indice)
        self.clave_submodular[ACTUAL].sort()
        self.clave_submodular[EFFECT].sort()
        return self.clave_submodular

    def nodes_complement(self, nodes: list[tuple[int, int]]):
        return list(set(self.vertices) - set(nodes))