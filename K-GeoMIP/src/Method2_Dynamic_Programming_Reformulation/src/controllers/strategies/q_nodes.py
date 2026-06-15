import time
from typing import Union
import numpy as np
from src.middlewares.slogger import SafeLogger
from src.funcs.base import emd_efecto, ABECEDARY
from src.middlewares.profile import profiler_manager, profile
from src.funcs.format import fmt_biparte_q
from src.controllers.manager import Manager
from src.models.base.sia import SIA

from src.models.core.solution import Solution
from src.constants.models import (
    QNODES_ANALYSIS_TAG,
    QNODES_LABEL,
    QNODES_STRAREGY_TAG,
)
from src.constants.base import (
    TYPE_TAG,
    NET_LABEL,
    INFTY_NEG,
    INFTY_POS,
    LAST_IDX,
    EFECTO,
    ACTUAL,
)


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
    - La clase implementa una versión secuencial del algoritmo Q para encontrar la partición que minimiza la pérdida de información.
    - Utiliza memoización para evitar recálculos innecesarios durante el proceso.
    - El análisis se realiza considerando dos tiempos: actual (presente) y
      efecto (futuro).
    """

    def __init__(self, gestor: Manager):
        # Lógica: Inicializa SIA con el gestor para configurar el acceso a la TPM y los
        #         atributos base del análisis antes de añadir los específicos de QNodes.
        # Sintaxis: `super().__init__(gestor)` llama al __init__ de SIA en la MRO;
        #           en herencia simple equivale a SIA.__init__(self, gestor).
        super().__init__(gestor)
        # Lógica: Abre una sesión de profiling nombrada por tamaño de red y página para
        #         que el reporte HTML agrupe todos los análisis de esta ejecución.
        # Sintaxis: f-string concatena NET_LABEL, longitud del estado (n nodos) y la letra
        #           de página; `profiler_manager` es la instancia global del módulo.
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        # Lógica: Declara m y n como anotaciones de tipo sin valor — se asignan en
        #         aplicar_estrategia cuando el subsistema ya está construido.
        # Sintaxis: `self.attr: Type` sin `=` es anotación PEP 526 sin inicialización;
        #           indica al linter el tipo esperado sin crear el atributo todavía.
        self.m: int
        self.n: int
        # Lógica: Declara tiempos como anotación — se asigna como tupla de dos arrays de
        #         ceros (t_actual, t_efecto) al inicio de aplicar_estrategia.
        # Sintaxis: `tuple[np.ndarray, np.ndarray]` es la anotación genérica para tupla
        #           de dos ndarray; Python no valida en runtime, solo el linter/mypy.
        self.tiempos: tuple[np.ndarray, np.ndarray]
        # Lógica: Genera las etiquetas de nodos en minúsculas (t_actual) y mayúsculas
        #         (t_efecto) para identificar vértices por tiempo en la visualización.
        # Sintaxis: List comprehension `[tuple(s.lower() for s in ABECEDARY), ABECEDARY]`
        #           crea dos secuencias; la primera en minúsculas, la segunda original.
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        # Lógica: Declara vertices como anotación de tipo — se asigna como set de tuplas
        #         (tiempo, índice) al construir el grafo en aplicar_estrategia.
        # Sintaxis: `set[tuple]` indica conjunto de tuplas; los sets garantizan unicidad
        #           y permiten operaciones de diferencia O(n) en nodes_complement.
        self.vertices: set[tuple]
        # self.memoria_delta = dict()
        # Lógica: Diccionario de memoización para almacenar la EMD y distribución marginal
        #         de cada conjunto omega evaluado, evitando recálculos costosos.
        # Sintaxis: `dict()` crea un diccionario vacío; las claves serán tuplas inmutables
        #           que representan los conjuntos omega evaluados.
        self.memoria_omega = dict()
        # Lógica: Diccionario de memoización para almacenar la EMD y distribución marginal
        #         de cada partición candidata formada durante el algoritmo Q.
        # Sintaxis: Las claves son tuplas inmutables que representan particiones candidatas;
        #           los valores son tuplas (emd, distribución_marginal).
        self.memoria_particiones = dict()

        # Lógica: Declara los índices de alcance y mecanismo como anotaciones — se asignan
        #         a partir del subsistema construido en aplicar_estrategia.
        # Sintaxis: `np.ndarray` como anotación indica que serán arrays NumPy de enteros.
        self.indices_alcance: np.ndarray
        self.indices_mecanismo: np.ndarray

        # Lógica: Crea el logger con el tag de estrategia QNodes para distinguir sus
        #         mensajes de los de otras estrategias en los archivos de log.
        # Sintaxis: `SafeLogger(tag)` construye logger con handlers de archivo y consola;
        #           QNODES_STRAREGY_TAG = "Q-Nodes_strategy".
        self.logger = SafeLogger(QNODES_STRAREGY_TAG)

    @profile(context={TYPE_TAG: QNODES_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
    ):
        # Lógica: Construye el subsistema condicionando y marginalizando el sistema completo
        #         según las cadenas de bits, preparando `sia_subsistema` y `sia_dists_marginales`.
        # Sintaxis: `sia_preparar_subsistema` modifica atributos de instancia como efecto
        #           secundario; no retorna valor.
        self.sia_preparar_subsistema(condicion, alcance, mecanismo)

        # Lógica: Construye la tupla de vértices EFECTO (t+1) a partir de los índices de
        #         los n-cubos del subsistema; cada vértice es la tupla (EFECTO, índice).
        # Sintaxis: Generator expression con `for efecto in .indices_ncubos`; EFECTO=1
        #           es la constante que identifica el tiempo futuro.
        futuro = tuple(
            (EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos
        )
        # Lógica: Construye la tupla de vértices ACTUAL (t) a partir de las dimensiones
        #         activas del subsistema; cada vértice es la tupla (ACTUAL, índice).
        # Sintaxis: ACTUAL=0 identifica el tiempo presente; `.dims_ncubos` retorna
        #           las dimensiones activas de los n-cubos del subsistema.
        presente = tuple(
            (ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos
        )  #

        # Lógica: Almacena los tamaños de futuros (m) y presentes (n) como atributos de
        #         instancia para que `funcion_submodular` los use sin recalcularlos.
        # Sintaxis: `.size` es el atributo NumPy que retorna el número total de elementos;
        #           equivale a `len(arr)` para arrays 1D.
        self.m = self.sia_subsistema.indices_ncubos.size
        self.n = self.sia_subsistema.dims_ncubos.size

        # Lógica: Almacena los índices de alcance y mecanismo como atributos de instancia
        #         para reutilizarlos en las biparticiones del algoritmo Q.
        # Sintaxis: Asignaciones directas de atributo; los ndarray se comparten por referencia.
        self.indices_alcance = self.sia_subsistema.indices_ncubos
        self.indices_mecanismo = self.sia_subsistema.dims_ncubos

        # Lógica: Inicializa los arrays de tiempo con ceros para marcar que ningún nodo
        #         tiene aún asignado un tiempo en la bipartición actual.
        # Sintaxis: `np.zeros(n, dtype=np.int8)` crea array de n ceros de 1 byte;
        #           la tupla tiempos = (t_actual, t_efecto) alinea con ACTUAL=0 y EFECTO=1.
        self.tiempos = (
            np.zeros(self.n, dtype=np.int8),
            np.zeros(self.m, dtype=np.int8),
        )

        # Lógica: Combina presentes y futuros en una lista plana de vértices para el
        #         algoritmo; el set paralelo permite lookups O(1) en nodes_complement.
        # Sintaxis: `list(a + b)` concatena dos tuplas en una lista mutable;
        #           `set(a + b)` crea un conjunto sin duplicados para diferencias de conjuntos.
        vertices = list(presente + futuro)
        self.vertices = set(presente + futuro)
        # Lógica: Ejecuta el algoritmo Q sobre la lista completa de vértices para encontrar
        #         la partición que minimiza la pérdida de información integrada.
        # Sintaxis: `self.algorithm(vertices)` retorna la clave (tupla) de la partición
        #           óptima en `self.memoria_particiones`.
        mip = self.algorithm(vertices)

        # Lógica: Formatea la partición óptima como string legible usando etiquetas de nodo
        #         para mostrar al usuario el resultado del algoritmo Q.
        # Sintaxis: `fmt_biparte_q(list(mip), complement)` espera dos listas de vértices;
        #           `nodes_complement(mip)` retorna el otro lado de la bipartición.
        fmt_mip = fmt_biparte_q(list(mip), self.nodes_complement(mip))

        # Lógica: Construye la Solution con la pérdida mínima, distribuciones y tiempo total,
        #         recuperando EMD y distribución de `memoria_particiones` por clave mip.
        # Sintaxis: `self.memoria_particiones[mip]` retorna tupla (emd, dist_marginal);
        #           `[0]` extrae el emd y `[1]` la distribución marginal.
        return Solution(
            estrategia=QNODES_LABEL,
            perdida=self.memoria_particiones[mip][0],
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=self.memoria_particiones[mip][1],
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    def algorithm(self, vertices: list[tuple[int, int]]):
        """
        Implementa el algoritmo Q para encontrar la partición óptima de un sistema que minimiza la pérdida de información, basándose en principios de submodularidad dentro de la teoría de lainformación.

        El algoritmo opera sobre un conjunto de vértices que representan nodos en diferentes tiempos del sistema (presente y futuro). La idea fundamental es construir incrementalmente grupos de nodos que, cuando se particionan, producen la menor pérdida posible de información en el sistema.

        Proceso Principal:
        -----------------
        El algoritmo comienza estableciendo dos conjuntos fundamentales: omega (W) y delta.
        Omega siempre inicia con el primer vértice del sistema, mientras que delta contiene todos los vértices restantes. Esta decisión no es arbitraria - al comenzar con un
        solo elemento en omega, podemos construir grupos de manera incremental evaluando cómo cada adición afecta la pérdida de información.

        La ejecución se desarrolla en fases, ciclos e iteraciones, donde cada fase representa un nivel diferente y conlleva a la formación de una partición candidata, cada ciclo representa un incremento de elementos al conjunto W y cada iteración determina al final cuál es el mejor elemento/cambio/delta para añadir en W.
        Fase >> Ciclo >> Iteración.

        1. Formación Incremental de Grupos:
        El algoritmo mantiene un conjunto omega que crece gradualmente en cada j-iteración. En cada paso, evalúa todos los deltas restantes para encontrar cuál, al unirse con omega produce la menor pérdida de información. Este proceso utiliza la función submodular para calcular la diferencia entre la EMD (Earth Mover's Distance) de la combinación y la EMD individual del delta evaluado.

        2. Evaluación de deltas:
        Para cada delta candidato el algoritmo:
        - Calcula su EMD individual si no está en memoria.
        - Calcula la EMD de su combinación con el conjunto omega actual
        - Determina la diferencia entre estas EMDs (el "costo" de la combinación)
        El delta que produce el menor costo se selecciona y se añade a omega.

        3. Formación de Nuevos Grupos:
        Al final de cada fase cuando omega crezca lo suficiente, el algoritmo:
        - Toma los últimos elementos de omega y delta (par candidato).
        - Los combina en un nuevo grupo
        - Actualiza la lista de vértices para la siguiente fase
        Este proceso de agrupamiento permite que el algoritmo construya particiones
        cada vez más complejas y reutilice estos "pares candidatos" para particiones en conjunto.

        Optimización y Memoria:
        ----------------------
        El algoritmo utiliza dos estructuras de memoria clave:
        - individual_memory: Almacena las EMDs y distribuciones de nodos individuales, evitando recálculos muy costosos.
        - partition_memory: Guarda las EMDs y distribuciones de las particiones completas, permitiendo comparar diferentes combinaciones de grupos teniendo en cuenta que su valor real está asociado al valor individual de su formación delta.

        La memoización es relevante puesto muchos cálculos de EMD son computacionalmente costosos y se repiten durante la ejecución del algoritmo.

        Resultado:
        ---------------
        Al terminar todas las fases, el algoritmo selecciona la partición que produjo la menor EMD global, representando la división del sistema que mejor preserva su información causal.

        Args:
            vertices (list[tuple[int, int]]): Lista de vértices donde cada uno es una
                tupla (tiempo, índice). tiempo=0 para presente (t_0), tiempo=1 para futuro (t_1).

        Returns:
            tuple[float, tuple[tuple[int, int], ...]]: El valor de pérdida en la primera posición, asociado con la partición óptima encontrada, identificada por la clave en partition_memory que produce la menor EMD.
        """
        # Lógica: Inicializa omega con el primer vértice y delta con el resto; el algoritmo
        #         Q requiere que omega empiece con exactamente un elemento para la construcción incremental.
        # Sintaxis: `np.array([vertices[0]])` crea array con el primer elemento como fila;
        #           `np.array(vertices[1:])` crea el array con todos los demás vértices.
        omegas_origen = np.array([vertices[0]])
        deltas_origen = np.array(vertices[1:])

        # Lógica: `vertices_fase` mantiene la lista de vértices que se actualiza al final
        #         de cada fase con los grupos candidatos formados durante esa fase.
        # Sintaxis: Asignación por referencia; la lista se reemplaza al final del bucle externo.
        vertices_fase = vertices

        omegas_ciclo = omegas_origen
        deltas_ciclo = deltas_origen

        # Lógica: El número de fases es `len(vertices) - 2` porque cada fase fusiona dos
        #         vértices en un grupo, reduciendo el tamaño en 1 hasta quedar 2 grupos.
        # Sintaxis: `range(len(vertices_fase) - 2)` genera los índices de fase 0..n-3;
        #           `total` se usa solo para el log de depuración de progreso.
        total = len(vertices_fase) - 2
        for i in range(len(vertices_fase) - 2):
            self.logger.debug(f"total: {total-i}")
            # Lógica: Reinicia omega con solo el primer vértice de la fase actual para
            #         construir el grupo incremental desde cero en cada ciclo.
            # Sintaxis: `[vertices_fase[0]]` crea lista de un elemento — el primer vértice
            #           de la fase actual, que sirve como semilla del crecimiento de omega.
            omegas_ciclo = [vertices_fase[0]]
            deltas_ciclo = vertices_fase[1:]

            # Lógica: Inicializa la EMD de la partición candidata con +∞ para que cualquier
            #         valor real la reemplace en la primera iteración del ciclo.
            # Sintaxis: `INFTY_POS = float("inf")` es la constante de infinito positivo
            #           importada; se usa como centinela de mínimo.
            emd_particion_candidata = INFTY_POS

            for j in range(len(deltas_ciclo) - 1):
                # self.logger.critic(f"   {j=}")
                # Lógica: Inicializa emd_local con un valor grande para el ciclo interno k
                #         que busca el delta con menor coste de unión con omega.
                # Sintaxis: `1e5` es notación científica para 100000.0 (float);
                #           actúa como techo de comparación dentro del ciclo k.
                emd_local = 1e5
                indice_mip: int

                for k in range(len(deltas_ciclo)):
                    # Lógica: Evalúa la función submodular para cada delta candidato, obteniendo
                    #         la EMD de la unión con omega y la EMD individual del delta.
                    # Sintaxis: `funcion_submodular` retorna (emd_union, emd_delta, dist_marginal);
                    #           el desempaquetado de 3 variables asigna los valores directamente.
                    emd_union, emd_delta, dist_marginal_delta = self.funcion_submodular(
                        deltas_ciclo[k], omegas_ciclo
                    )
                    # Lógica: La diferencia emd_union - emd_delta mide el "coste marginal" de
                    #         añadir este delta a omega; se busca el delta con menor coste.
                    # Sintaxis: Resta aritmética de floats; puede ser negativa (indica ganancia).
                    emd_iteracion = emd_union - emd_delta

                    # Lógica: Actualiza el índice del mejor delta si este tiene menor coste
                    #         que el mejor visto hasta ahora en esta iteración j.
                    # Sintaxis: `emd_iteracion < emd_local` es comparación de floats estándar;
                    #           `indice_mip` guarda el índice k del mejor delta encontrado.
                    if emd_iteracion < emd_local:
                        emd_local = emd_iteracion
                        indice_mip = k

                    # Lógica: El último delta evaluado en k se convierte en la partición
                    #         candidata de la fase — su EMD y distribución se registran
                    #         en `memoria_particiones` al final del ciclo j.
                    # Sintaxis: Las asignaciones se sobreescriben en cada k; solo importa
                    #           el valor del último delta del ciclo k.
                    emd_particion_candidata = emd_delta
                    dist_particion_candidata = dist_marginal_delta
                    ...
                # self.logger.critic(f"       [k]: {indice_mip}")

                # Lógica: Añade el delta con menor coste marginal a omega y lo elimina de
                #         deltas para la siguiente iteración j del ciclo.
                # Sintaxis: `list.append(elem)` añade al final en O(1);
                #           `list.pop(idx)` elimina el elemento por índice en O(n).
                omegas_ciclo.append(deltas_ciclo[indice_mip])
                deltas_ciclo.pop(indice_mip)
                ...

            # Lógica: Registra la partición candidata de esta fase en `memoria_particiones`
            #         con su EMD y distribución marginal para la comparación final.
            # Sintaxis: `deltas_ciclo[LAST_IDX]` accede al último elemento (LAST_IDX=-1);
            #           `isinstance(x, list)` distingue grupos ya fusionados de vértices simples.
            self.memoria_particiones[
                tuple(
                    deltas_ciclo[LAST_IDX]
                    if isinstance(deltas_ciclo[LAST_IDX], list)
                    else deltas_ciclo
                )
            ] = emd_particion_candidata, dist_particion_candidata

            # Lógica: Forma el par candidato fusionando el último omega con el último delta
            #         para crear el nuevo vértice compuesto de la siguiente fase.
            # Sintaxis: El operador `+` sobre listas concatena; `isinstance(..., tuple)` vs
            #           `isinstance(..., list)` distingue vértices simples de grupos ya fusionados.
            par_candidato = (
                [omegas_ciclo[LAST_IDX]]
                if isinstance(omegas_ciclo[LAST_IDX], tuple)
                else omegas_ciclo[LAST_IDX]
            ) + (
                deltas_ciclo[LAST_IDX]
                if isinstance(deltas_ciclo[LAST_IDX], list)
                else deltas_ciclo
            )

            # Lógica: Reemplaza el último omega con el par candidato fusionado para que
            #         la siguiente fase itere sobre la lista reducida de grupos candidatos.
            # Sintaxis: `list.pop()` elimina y retorna el último elemento;
            #           `list.append(elem)` añade el nuevo grupo fusionado al final.
            omegas_ciclo.pop()
            omegas_ciclo.append(par_candidato)

            # Lógica: Actualiza vertices_fase con los omegas del ciclo actual para que la
            #         siguiente fase itere sobre la lista reducida de grupos candidatos.
            # Sintaxis: Asignación de referencia; `vertices_fase` apunta ahora a omegas_ciclo.
            vertices_fase = omegas_ciclo
            ...

        # Lógica: Retorna la clave de la partición con menor EMD global en `memoria_particiones`,
        #         representando la división del sistema que mejor preserva la información causal.
        # Sintaxis: `min(dict, key=lambda k: dict[k][0])` retorna la clave cuyo valor[0]
        #           (EMD) es mínimo; la lambda es la función de comparación anónima.
        return min(
            self.memoria_particiones, key=lambda k: self.memoria_particiones[k][0]
        )

    def funcion_submodular(
        self, deltas: Union[tuple, list[tuple]], omegas: list[Union[tuple, list[tuple]]]
    ):
        """
        Evalúa el impacto de combinar el conjunto de nodos individual delta y su agrupación con el conjunto omega, calculando la diferencia entre EMD (Earth Mover's Distance) de las configuraciones, en conclusión los nodos delta evaluados individualmente y su combinación con el conjunto omega.

        El proceso se realiza en dos fases principales:

        1. Evaluación Individual:
           - Crea una copia del estado temporal del subsistema.
           - Activa los nodos delta en su tiempo correspondiente (presente/futuro).
           - Si el delta ya fue evaluado antes, recupera su EMD y distribución marginal de memoria
           - Si no, ha de:
             * Identificar dimensiones activas en presente y futuro.
             * Realiza bipartición del subsistema con esas dimensiones.
             * Calcular la distribución marginal y EMD respecto al subsistema.
             * Guarda resultados en memoria para seguro un uso futuro.

        2. Evaluación Combinada:
           - Sobre la misma copia temporal, activa también los nodos omega.
           - Calcula dimensiones activas totales (delta + omega).
           - Realiza bipartición del subsistema completo.
           - Obtiene EMD de la combinación.

        Args:
            deltas: Un nodo individual (tupla) o grupo de nodos (lista de tuplas)
                   donde cada tupla está identificada por su (tiempo, índice), sea el tiempo t_0 identificado como 0, t_1 como 1 y, el índice hace referencia a las variables/dimensiones habilitadas para operaciones de substracción/marginalización sobre el subsistema, tal que genere la partición.
            omegas: Lista de nodos ya agrupados, puede contener tuplas individuales
                   o listas de tuplas para grupos formados por los pares candidatos o más uniones entre sí (grupos candidatos).

        Returns:
            tuple: (
                EMD de la combinación omega y delta,
                EMD del delta individual,
                Distribución marginal del delta individual
            )
            Esto lo hice así para hacer almacenamiento externo de la emd individual y su distribución marginal en las particiones candidatas.
        """
        # Lógica: Inicializa emd_delta con INFTY_NEG como centinela para detectar si no se
        #         calculó (cualquier EMD real es ≥ 0, por lo que INFTY_NEG es imposible).
        # Sintaxis: `INFTY_NEG = float("-inf")` es la constante de infinito negativo importada.
        emd_delta = INFTY_NEG
        # Lógica: `temporal` acumula los índices de los vértices activados en dos sublistas
        #         [dims_presente, dims_futuro] para construir la bipartición del subsistema.
        # Sintaxis: `[[], []]` crea dos listas vacías independientes; se indexan con
        #           ACTUAL=0 y EFECTO=1 para distinguir presente y futuro.
        temporal = [[], []]

        # Lógica: Desempaqueta el/los vértice(s) delta y los acumula en temporal según su
        #         tiempo (ACTUAL o EFECTO) para construir las dimensiones de la bipartición.
        # Sintaxis: `isinstance(deltas, tuple)` distingue vértice simple (tiempo, idx)
        #           de grupo de vértices (lista de tuplas).
        if isinstance(deltas, tuple):
            d_tiempo, d_indice = deltas
            temporal[d_tiempo].append(d_indice)

        else:
            for delta in deltas:
                d_tiempo, d_indice = delta
                temporal[d_tiempo].append(d_indice)

        # Lógica: Obtiene la referencia al subsistema actual; las operaciones de bipartición
        #         crean nuevos objetos sin modificar el original (diseño inmutable).
        # Sintaxis: Asignación de referencia; `self.sia_subsistema` es el System inmutable.
        copia_delta = self.sia_subsistema

        # Lógica: Extrae las dimensiones de alcance (futuro) y mecanismo (presente) del
        #         delta para construir la bipartición del subsistema.
        # Sintaxis: `temporal[EFECTO]` = temporal[1] = lista de índices futuros acumulados;
        #           `temporal[ACTUAL]` = temporal[0] = lista de índices presentes.
        dims_alcance_delta = temporal[EFECTO]
        dims_mecanismo_delta = temporal[ACTUAL]

        # Lógica: Genera la bipartición del subsistema usando solo las dimensiones del delta,
        #         para evaluar su EMD individual respecto al subsistema completo.
        # Sintaxis: `.bipartir(alcance, mecanismo)` recibe NDArray[np.int8]; `np.array(list, dtype=np.int8)`
        #           convierte las listas de índices al tipo esperado.
        particion_delta = copia_delta.bipartir(
            np.array(dims_alcance_delta, dtype=np.int8),
            np.array(dims_mecanismo_delta, dtype=np.int8),
        )
        # Lógica: Calcula la distribución marginal de la bipartición del delta y su EMD
        #         respecto a la distribución marginal del subsistema original.
        # Sintaxis: `emd_efecto(u, v)` calcula Σ|u_i - v_i| — la suma de diferencias
        #           absolutas entre las distribuciones marginales de cada nodo.
        vector_delta_marginal = particion_delta.distribucion_marginal()
        emd_delta = emd_efecto(vector_delta_marginal, self.sia_dists_marginales)

        # Unión #

        # Lógica: Añade los vértices omega a `temporal` para construir la bipartición
        #         combinada delta+omega y evaluar el coste de la unión.
        # Sintaxis: `isinstance(omega, list)` distingue grupos compuestos (lista de tuplas)
        #           de vértices simples (tuplas); itera recursivamente si es lista.
        for omega in omegas:
            if isinstance(omega, list):
                for omg in omega:
                    o_tiempo, o_indice = omg
                    temporal[o_tiempo].append(o_indice)
            else:
                o_tiempo, o_indice = omega
                temporal[o_tiempo].append(o_indice)

        # Lógica: Obtiene la referencia al subsistema para la bipartición combinada;
        #         igual que copia_delta pero semánticamente indica la unión delta+omega.
        # Sintaxis: Asignación de referencia al mismo objeto System inmutable.
        copia_union = self.sia_subsistema

        # Lógica: Las dimensiones de la unión incluyen tanto los índices del delta como
        #         los de todos los omegas acumulados en temporal por el bucle anterior.
        # Sintaxis: `temporal[EFECTO]` y `temporal[ACTUAL]` contienen ahora todos los índices
        #           de delta + omega concatenados por las llamadas append anteriores.
        dims_alcance_union = temporal[EFECTO]
        dims_mecanismo_union = temporal[ACTUAL]

        # Lógica: Genera la bipartición combinada delta+omega del subsistema y calcula su
        #         EMD para medir el coste de la unión respecto al subsistema original.
        # Sintaxis: Mismo patrón que la bipartición del delta, pero con dimensiones combinadas.
        particion_union = copia_union.bipartir(
            np.array(dims_alcance_union, dtype=np.int8),
            np.array(dims_mecanismo_union, dtype=np.int8),
        )
        vector_union_marginal = particion_union.distribucion_marginal()
        emd_union = emd_efecto(vector_union_marginal, self.sia_dists_marginales)

        # Lógica: Retorna los tres valores necesarios: EMD de la unión (para el coste marginal
        #         emd_union - emd_delta), EMD del delta individual (para memoria_particiones)
        #         y su distribución marginal.
        # Sintaxis: `return a, b, c` retorna una tupla de 3 que se desempaqueta en el llamador.
        return emd_union, emd_delta, vector_delta_marginal

    def nodes_complement(self, nodes: list[tuple[int, int]]):
        # Lógica: Calcula el complemento de `nodes` respecto al conjunto total de vértices
        #         del sistema para obtener el "otro lado" de la bipartición en el formateo.
        # Sintaxis: `set(self.vertices) - set(nodes)` es la diferencia de conjuntos Python;
        #           `list(...)` convierte el set resultante a lista para fmt_biparte_q.
        return list(set(self.vertices) - set(nodes))
