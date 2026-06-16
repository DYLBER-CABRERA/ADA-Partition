import heapq
import random
import time
from typing import List

import numpy as np
from numpy.typing import NDArray

from src.constants.base import ACTUAL, EFECTO, NET_LABEL, TYPE_TAG
from src.constants.models import (
    K_MAX,
    K_MIN,
    KGEOMETRIC_ANALYSIS_TAG,
    KGEOMETRIC_LABEL,
    KGEOMETRIC_STRATEGY_TAG,
)
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.funcs.base import emd_efecto, seleccionar_subestado
from src.funcs.format import fmt_k_particion
from src.funcs.system import stirling
from src.middlewares.profile import profile
from src.middlewares.slogger import SafeLogger
from src.models.core.solution import Solution

# Caracteres Unicode de subíndice para las etiquetas S₁, S₂, S₃, S₄, S₅
_SUBSCRIPTS: str = "₀₁₂₃₄₅"

# Lógica: Número total de candidatos k-partición a evaluar con EMD en _generar_candidatos_k.
#         3 son las estrategias deterministas base (LPT, round-robin, bloques); los restantes
#         (_C_CANDIDATOS_TOTAL - 3) son perturbaciones aleatorias del vector de costos.
#         Valor 25 elegido porque: (a) O(25·n log n) << Θ(n·2^n) para n≥8, por lo que el
#         costo extra de búsqueda no domina el tiempo total; (b) 25 candidatos cubren ~8×
#         más espacio que C=3 con un overhead de evaluación EMD que solo multiplica por ~8
#         el tiempo de la Fase 5, que es despreciable frente a la Fase BFS dominante.
# Sintaxis: Constante de módulo en SCREAMING_SNAKE_CASE; tipo int anotado explícitamente.
_C_CANDIDATOS_TOTAL: int = 25

# Lógica: Presupuesto máximo de evaluaciones EMD que puede consumir la búsqueda local de
#         refinamiento (Fase 6.5, Opt 7). Acota el costo extra a O(_MAX_REFINAMIENTO_EVALS · 2^d)
#         garantizando que el refinamiento nunca domine sobre la fase BFS Θ(n·2^n). Cada evaluación
#         es barata porque reutiliza el caché de marginales por (cubo, mecanismo) de la Opt 6.
# Sintaxis: Constante de módulo entera; se compara contra el contador `evals` en _refinar_local.
_MAX_REFINAMIENTO_EVALS: int = 40

# Lógica: Cota superior de n (número de variables del subsistema) para activar la búsqueda local.
#         Para n ≤ 16 cada marginalización opera sobre ≤ 2^16 celdas, costo despreciable frente al
#         BFS; para n mayores se desactiva el refinamiento para NO añadir trabajo a los sistemas
#         grandes (donde la prioridad es reducir tiempo, no invertir más evaluaciones costosas).
# Sintaxis: Constante de módulo entera; se compara contra `len(estado_inicial)` en _refinar_local.
_REFINAMIENTO_N_MAX: int = 16


class KGeometricSIA(GeometricSIA):
    """
    K-GeoMIP SIA — Extiende GeometricSIA a k-particiones con k ∈ {2,3,4,5}.

    Principio algorítmico (ADA 24A §5 — Algoritmos Voraces):
        Sea V = {v₀,...,v_{n-1}} un subsistema con vector de costos c ∈ ℝⁿ
        obtenido de la tabla de transiciones geométrica. La heurística greedy
        aproxima el k-MIP generando O(1) candidatos en lugar de S(n,k)² exhaustivos.

    Fases del algoritmo:
        Fase 1 — Preparar subsistema:         Θ(n·2^n)  [SIA.sia_preparar_subsistema]
        Fase 2 — Construir tabla de costos:   Θ(n·2^n)  [GeometricSIA, heredado]
        Fase 3 — Generar candidatos greedy:   O(n log n) [Algoritmo Voraz, ADA §5]
        Fase 4 — Evaluar candidatos con EMD:  O(C·n·2^d) C=3 constante

    Complejidad total: Θ(n·2^n) — dominada por Fases 1 y 2.

    Mejora vs exhaustivo (k=3, n=10):
        S(10,3)² / C = 9330² / 3 ≈ 29M× speedup en la búsqueda de particiones.

    Notación asintótica (ADA 24A §1.1):
        f(n) ∈ Θ(g(n)) ⟺ ∃c₁,c₂>0, n₀: ∀n≥n₀: c₁·g(n) ≤ f(n) ≤ c₂·g(n)
        La fase greedy satisface f(n) ∈ O(n log n) ⊂ O(n·2^n) = Θ(total).

    Validación k=2: delega a GeometricSIA.aplicar_estrategia() → resultado idéntico.

    Args:
        gestor (Manager): Gestor del sistema con configuración, TPM y estado inicial.
    """

    def __init__(self, gestor: Manager) -> None:
        # Lógica: Invoca __init__ del padre (GeometricSIA) que configura tabla_transiciones,
        #         vertices, etiquetas, logger base y demás atributos heredados.
        # Sintaxis: `super().__init__(arg)` invoca el constructor de la clase padre en el MRO.
        super().__init__(gestor)

        # Lógica: Reemplaza el logger del padre por uno identificado con la estrategia KGeometric.
        # Sintaxis: `SafeLogger(tag)` crea un logger thread-safe con prefijo de identificación.
        self.logger = SafeLogger(KGEOMETRIC_STRATEGY_TAG)

        # Lógica: Atributo que almacena el k activo para acceso en métodos internos durante la ejecución.
        # Sintaxis: `int` es la anotación de tipo; `K_MIN` es la constante 2 del módulo models.
        self.k: int = K_MIN

        # Lógica: Diccionario exclusivo para k-particiones; separado de memoria_particiones (usada para k=2 en padre).
        # Sintaxis: `dict` vacío — llave: clave hashable (tupla anidada), valor: tupla (emd, dist, particion).
        self.memoria_k_particiones: dict = {}

        # Lógica: Caché inter-k que persiste entre llamadas sucesivas a aplicar_estrategia con distintos k.
        #         Permite warm-start: la mejor (k-1)-partición encontrada sirve de semilla para generar
        #         un candidato k-partición dividiendo el grupo de mayor costo acumulado en dos sub-grupos con LPT.
        #         NO se reinicia entre llamadas — sólo se actualiza al finalizar cada aplicar_estrategia(k).
        #         PRECAUCIÓN: si se reutiliza la instancia con un subsistema diferente, crear una nueva instancia.
        # Sintaxis: dict[int, list] — llave: k entero, valor: list[tuple[NDArray, NDArray]] de la partición ganadora.
        self._cache_mejor_por_k: dict = {}

        # Lógica: Caché del subsistema completo (Fases 1–3) — el cálculo más costoso del método geométrico.
        #         La tabla BFS de costos de transición es Θ(n·2^n) y depende únicamente de
        #         (condicion, alcance, mecanismo): el mismo subsistema produce la misma tabla.
        #         Al llamar aplicar_estrategia(k=3), luego (k=4), luego (k=5) sobre el mismo subsistema,
        #         la tabla se calcula UNA SOLA VEZ y se reutiliza las dos siguientes, eliminando
        #         2·Θ(n·2^n) de cómputo redundante. Este es el requisito de reutilización eficiente
        #         de componentes existentes descrito en la fundamentación teórica del proyecto.
        # Sintaxis: dict[(str,str,str), dict] — llave: tupla (condicion, alcance, mecanismo);
        #           valor: snapshot completo de todos los atributos de estado de Fases 1–3.
        self._cache_subsistema: dict = {}

        # Lógica: Caché de marginales por (índice_cubo, mecanismo) usado por _dist_particion (Opt 6).
        #         La distribución marginal de una k-partición se factoriza por n-cubo: el valor del
        #         cubo i depende ÚNICAMENTE de su índice y del conjunto-mecanismo de la parte que lo
        #         contiene en su alcance. Como los 25 candidatos y los movimientos de la búsqueda
        #         local comparten muchos pares (cubo, mecanismo), cachear el valor marginal evita
        #         re-marginalizar (np.mean sobre 2^d celdas) el mismo cubo una y otra vez.
        #         Se REINICIA al comienzo de cada aplicar_estrategia(k>2) porque los valores dependen
        #         del subsistema activo; mantenerlo entre subsistemas distintos daría valores obsoletos.
        # Sintaxis: dict[(int, frozenset[int]), float] — llave hashable; valor: probabilidad OFF 1-p.
        self._cache_marg: dict = {}

    @profile(context={TYPE_TAG: KGEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
        k: int = K_MIN,
    ):
        """
        Punto de entrada principal de la estrategia K-GeoMIP.

        Para k=2 delega al flujo exacto de GeometricSIA (garantía de equivalencia).
        Para k∈{3,4,5} aplica la heurística greedy multiway partition sobre la
        tabla de costos construida con los métodos heredados de GeometricSIA.

        Diagrama de decisión:
            aplicar_estrategia(k)
              ├── k=2  → super().aplicar_estrategia()        [GeometricSIA exacto]
              └── k>2  → sia_preparar_subsistema()
                          → _construir_tabla_costos()
                          → _generar_candidatos_k(k)         [3 estrategias greedy]
                          → [k_partir(P) + emd_efecto()] × C
                          → Solution(min_emd, fmt_k_mip)

        Args:
            condicion (str): Cadena binaria — bit=0 condiciona esa variable de fondo.
            alcance   (str): Cadena binaria — bit=0 substrae esa variable del alcance.
            mecanismo (str): Cadena binaria — bit=0 substrae esa variable del mecanismo.
            tpm       (np.ndarray): Matriz de probabilidad de transición del sistema completo.
            k         (int): Número de partes k ∈ {K_MIN,...,K_MAX}. Default: K_MIN=2.

        Returns:
            Solution: Objeto con la k-MIP de mínima pérdida δ_k, distribuciones y tiempo.

        Raises:
            ValueError: Si k ∉ {K_MIN,...,K_MAX}.

        Complejidad temporal:  Θ(n·2^n)  [dominada por construcción tabla de costos]
        Complejidad espacial:  O(n·2^n)  [tabla de transiciones + sistema k-partido]
        """
        # Lógica: Valida dominio de k antes de cualquier cómputo costoso.
        #         La notación `K_MIN ≤ k ≤ K_MAX` expresa el invariante de entrada.
        # Sintaxis: `not (A <= k <= B)` es encadenamiento de comparadores de Python (chain comparison).
        if not (K_MIN <= k <= K_MAX):
            raise ValueError(
                f"k debe estar en [{K_MIN},{K_MAX}], se recibió k={k}"
            )

        # Lógica: Persiste k en la instancia para uso en métodos auxiliares del flujo actual.
        # Sintaxis: Asignación directa de atributo de instancia vía `self.`.
        self.k = k

        # ── Delegación k=2: comportamiento idéntico a GeometricSIA ───────────
        # Lógica: Para k=2 la k-partición óptima coincide con la bi-partición óptima de GeometricSIA.
        #         Delegar garantiza KGeometricSIA(k=2) ≡ GeometricSIA por construcción (validación formal).
        # Sintaxis: `super().metodo(args)` invoca la implementación del padre según el MRO de Python.
        if k == 2:
            return super().aplicar_estrategia(condicion, alcance, mecanismo, tpm)

        # Lógica: Reinicia la memoria de k-particiones para evitar contaminación entre llamadas sucesivas.
        #         Se hace SIEMPRE al inicio — incluso en cache-hit — porque cada k produce candidatos distintos.
        # Sintaxis: Asignación a dict vacío `{}` — más rápido que `.clear()` para diccionarios grandes.
        self.memoria_k_particiones = {}

        # ── Caché de subsistema: reutilización de la tabla BFS entre valores de k ──────
        # Lógica: La clave identifica unívocamente el subsistema dentro de la misma sesión.
        #         Condicion, alcance y mecanismo son cadenas binarias que determinan por completo
        #         qué subconjunto de la TPM se analiza — la TPM en sí es estable en toda la sesión.
        #         Así, mismo (condicion, alcance, mecanismo) → mismo subsistema → misma tabla BFS.
        # Sintaxis: Tupla de 3 strings — hasheable en O(len_str) y comparable en O(1) amortizado como llave.
        _clave_sub: tuple = (condicion, alcance, mecanismo)

        if _clave_sub in self._cache_subsistema:
            # ── HIT: restaurar estado de Fases 1–3 sin recalcular — ahorra Θ(n·2^n) ──────
            # Lógica: Todos los atributos de estado del subsistema y la tabla BFS ya fueron calculados
            #         en una llamada anterior con el mismo subsistema (distinto k).
            #         Se restauran directamente desde el snapshot almacenado.
            #         Solo self.sia_tiempo_inicio se reinicia para medir el tiempo de ESTA llamada.
            # Sintaxis: Acceso a dict por tupla-llave en O(1); asignación directa de atributos de instancia.
            _c = self._cache_subsistema[_clave_sub]
            self.sia_subsistema        = _c["sia_subsistema"]
            self.sia_dists_marginales  = _c["sia_dists_marginales"]
            self.sia_tiempo_inicio     = time.time()
            self._flat_data            = _c["_flat_data"]
            self._flat_matrix          = _c["_flat_matrix"]
            self.vertices              = _c["vertices"]
            self.estado_inicial        = _c["estado_inicial"]
            self.estado_final          = _c["estado_final"]
            self.idx_ncubos            = _c["idx_ncubos"]
            self.caminos               = _c["caminos"]
            self._trans_matrix         = _c["_trans_matrix"]
            self._trans_valid          = _c["_trans_valid"]

        else:
            # ── MISS: calcular Fases 1–3 desde cero y guardar en caché ───────────────────

            # ── Fase 1: Preparar subsistema ──────────────────────────────────────
            # Lógica: Construye el subsistema completo → condicionado → substraído desde la TPM.
            #         Establece self.sia_subsistema y self.sia_dists_marginales para fases posteriores.
            # Sintaxis: Método heredado de SIA; modifica atributos de instancia in-place.
            self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)

            # ── Fase 2: Construir infraestructura de costos (patrones de GeometricSIA) ──
            # Lógica: Genera los identificadores de nodos futuros como pares (EFECTO=1, idx).
            #         EFECTO marca la dimensión temporal t+1 en la representación de vértices del grafo.
            # Sintaxis: `tuple(generator)` materializa la expresión generadora en una tupla inmutable.
            futuro = tuple(
                (EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos
            )

            # Lógica: Genera los identificadores de nodos presentes como pares (ACTUAL=0, idx).
            #         ACTUAL marca la dimensión temporal t en la representación de vértices del grafo.
            # Sintaxis: Mismo patrón que `futuro`; ACTUAL y EFECTO son constantes importadas de base.
            presente = tuple(
                (ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos
            )

            # Lógica: Aplana los datos de cada n-cubo a 1D para acceso por índice de estado en O(1).
            #         `flat_data[i][estado]` = probabilidad del n-cubo i en el estado dado.
            # Sintaxis: List comprehension; `.ravel()` aplana sin copiar (retorna vista) en O(1).
            self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]

            # Lógica: Matriz 2D (n_fut × 2^n_mec) de probabilidades aplanadas para la extracción
            #         vectorizada de columnas en calcular_costo (Opt 5, heredada de GeometricSIA).
            #         Debe construirse ANTES de calcular_costos_nivel (Fase 3) porque el BFS la consume.
            # Sintaxis: `np.stack` apila la lista de arrays 1D en un array 2D; el guard evita el error
            #           de stack sobre lista vacía produciendo una matriz vacía coherente.
            self._flat_matrix = (
                np.stack(self._flat_data) if self._flat_data else np.empty((0, 0))
            )

            # Lógica: El conjunto de vértices del grafo de costos es la unión de nodos presentes y futuros.
            # Sintaxis: `set(tupla_a + tupla_b)` concatena las tuplas y elimina duplicados en O(n).
            self.vertices = set(presente + futuro)

            # Lógica: Extrae las dimensiones activas del subsistema para indexar el estado inicial.
            # Sintaxis: `dims_ncubos` es una @property de System que retorna dims del primer n-cubo.
            dims = self.sia_subsistema.dims_ncubos

            # Lógica: Fija el estado inicial del subsistema recortado a sus dimensiones activas.
            # Sintaxis: `array[indices]` es fancy indexing de NumPy — extrae las posiciones en dims.
            self.estado_inicial = self.sia_subsistema.estado_inicial[dims]

            # Lógica: El estado final es la inversión completa de bits del estado inicial (todos los bits flipped).
            # Sintaxis: `1 - array` usa NumPy broadcasting — resta cada elemento del escalar 1.
            self.estado_final = 1 - self.estado_inicial

            # ── Fase 3: Construir tabla de costos (heredado de GeometricSIA) ─────
            # Lógica: Lista de índices [0,...,n-1] que identifica cada n-cubo del subsistema.
            # Sintaxis: `list(range(n))` genera [0,1,...,n-1] como lista Python nativa.
            self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))

            # Lógica: Inicializa la estructura de niveles del grafo BFS; nivel 0 contiene solo el estado inicial.
            # Sintaxis: `.tolist()` convierte el ndarray a lista Python nativa (necesario para serialización como clave).
            self.caminos = {0: [self.estado_inicial.tolist()]}

            # Lógica: Inicializa la matriz numpy de transiciones que reemplaza a tabla_transiciones (dict).
            #         Tiene 2^n_mec filas (una por cada estado posible del mecanismo) y n_fut columnas
            #         (una por cada nodo futuro t+1). float32 usa la mitad de memoria que float64.
            #         Equivale al dict vacío {} anterior; el estado ini→ini tiene costo 0 (np.zeros).
            # Sintaxis: `1 << n_mec` = 2^n_mec con desplazamiento bit a bit; más rápido que `2**n_mec`.
            #           `np.zeros(shape, dtype)` asigna y pone a cero en O(2^n_mec · n_fut).
            n_mec = len(self.estado_inicial)
            n_fut = len(self.sia_subsistema.indices_ncubos)
            self._trans_matrix = np.zeros((1 << n_mec, n_fut), dtype=np.float32)

            # Lógica: Array booleano de memoización: _trans_valid[i]=True cuando la fila i ya fue calculada.
            #         Evita recalcular estados ya visitados en calcular_costo (O(1) por consulta).
            # Sintaxis: `np.zeros(..., dtype=bool)` crea array de False; bool ocupa 1 byte por elemento.
            self._trans_valid = np.zeros(1 << n_mec, dtype=bool)

            # Lógica: Marca el estado inicial como válido con costo 0 (ini→ini no tiene transición real).
            #         Equivale a `tabla_transiciones[(ini,ini)] = [0.0]*n_fut` del código anterior.
            # Sintaxis: `_estado_a_idx` convierte la lista del estado inicial a índice entero little-endian.
            ini_idx = self._estado_a_idx(self.caminos[0][0])
            self._trans_valid[ini_idx] = True

            # Lógica: Expande el grafo BFS nivel por nivel; nivel i = estados a distancia Hamming i del inicial.
            #         Al llegar a nivel n, todos los bits han sido flipeados → estado_final alcanzado.
            # Sintaxis: `range(1, n+1)` itera los enteros 1,2,...,n; `len(estado_inicial)` = n variables.
            for nivel in range(1, len(self.estado_inicial) + 1):
                # Lógica: Calcula y almacena los costos de transición para todos los estados del nivel actual.
                #         Este método modifica self.caminos y self._trans_matrix in-place.
                # Sintaxis: Llamada a método heredado de GeometricSIA que recibe estado_final y número de nivel.
                self.calcular_costos_nivel(self.estado_final, nivel)

            # ── Guardar snapshot en caché tras completar Fases 1–3 ───────────────
            # Lógica: Se almacena el estado completo del subsistema y la tabla BFS una vez que el cómputo
            #         Θ(n·2^n) terminó. Las llamadas subsiguientes con el mismo subsistema (k distinto)
            #         saltarán directamente al bloque HIT sin recalcular nada.
            #         _trans_matrix y _trans_valid son arrays NumPy ya finalizados — no se modificarán más.
            # Sintaxis: Dict literal con todas las llaves necesarias para restaurar el estado completo.
            self._cache_subsistema[_clave_sub] = {
                "sia_subsistema":       self.sia_subsistema,
                "sia_dists_marginales": self.sia_dists_marginales,
                "_flat_data":           self._flat_data,
                "_flat_matrix":         self._flat_matrix,
                "vertices":             self.vertices,
                "estado_inicial":       self.estado_inicial,
                "estado_final":         self.estado_final,
                "idx_ncubos":           self.idx_ncubos,
                "caminos":              self.caminos,
                "_trans_matrix":        self._trans_matrix,
                "_trans_valid":         self._trans_valid,
            }

        # ── Fase 4: Generar candidatos k-partición con heurística greedy ─────
        # Lógica: Genera C=3 candidatos k-partición usando estrategias voraces complementarias (ADA §5).
        #         O(n log n) total — dominado por el ordenamiento de variables por costo.
        # Sintaxis: Método interno que retorna lista de candidatos; cada candidato es list[(NDArray, NDArray)].
        candidatos = self._generar_candidatos_k(k)

        # Lógica: Reinicia el caché de marginales por (cubo, mecanismo) para esta evaluación (Opt 6).
        #         Los valores marginales dependen del subsistema activo; reiniciarlo evita arrastrar
        #         entradas de una llamada anterior con otro subsistema. Dentro de ESTA llamada el caché
        #         se llena durante la Fase 5 y se reutiliza tanto en candidatos repetidos como en la
        #         búsqueda local (Fase 6.5), donde la mayoría de cubos conservan su mecanismo.
        # Sintaxis: Reasignación a dict vacío — más rápida que `.clear()` para dicts grandes.
        self._cache_marg = {}

        # ── Fase 5: Evaluar cada candidato con EMD ───────────────────────────
        # Lógica: Para cada candidato P_k: calcula su distribución marginal y mide la pérdida δ_k(P).
        #         El costo total de esta fase es O(C · n · 2^d) ⊆ O(n · 2^n) (C constante).
        # Sintaxis: `for particion in candidatos` itera la lista de candidatos.
        for particion in candidatos:
            # Lógica: Obtiene la distribución marginal de la k-partición mediante el evaluador cacheado
            #         (Opt 6) en lugar de reconstruir un System completo con `k_partir(P)`.
            #         `_dist_particion` reutiliza marginales por (cubo, mecanismo) ya calculados,
            #         evitando re-marginalizar cubos cuyo mecanismo se repite entre candidatos.
            #         El resultado es numéricamente idéntico a `k_partir(P).distribucion_marginal()`.
            # Sintaxis: Llamada a método interno que retorna NDArray[float32] de probabilidades OFF.
            dist = self._dist_particion(particion)

            # Lógica: Mide δ_k(P) = EMD entre la distribución k-partida y la distribución original del subsistema.
            #         EMD_efecto(u,v) = Σⱼ |u[j]-v[j]| — solución analítica para variables independientes.
            # Sintaxis: `emd_efecto(u, v)` función importada de funcs.base; opera sobre dos NDArray[float32].
            emd = emd_efecto(dist, self.sia_dists_marginales)

            # Lógica: Construye clave hashable para el diccionario de memoria — permite comparar particiones.
            # Sintaxis: Método interno que retorna tupla anidada inmutable desde la lista de (NDArray, NDArray).
            clave = self._particion_a_clave(particion)

            # Lógica: Almacena (emd, dist, particion) asociados a la clave para recuperar el mínimo después.
            # Sintaxis: `dict[clave] = valor` inserta o sobreescribe la entrada; O(1) amortizado.
            self.memoria_k_particiones[clave] = (emd, dist, particion)

        # ── Fase 6: Seleccionar la k-MIP de pérdida mínima ──────────────────
        # Lógica: k-MIP = argmin_{P} δ_k(P) — la k-partición que minimiza la pérdida EMD.
        #         Recorre las claves del dict y devuelve la de menor valor en posición 0 de la tupla.
        # Sintaxis: `min(dict, key=lambda c: ...)` evalúa el predicado sobre cada clave del diccionario.
        mejor_clave = min(
            self.memoria_k_particiones,
            key=lambda c: self.memoria_k_particiones[c][0],
        )

        # Lógica: Extrae los tres valores de la entrada ganadora: pérdida, distribución y partición.
        # Sintaxis: Desempaquetado de tupla de 3 elementos en una sola línea de asignación.
        mejor_emd, mejor_dist, mejor_particion = self.memoria_k_particiones[mejor_clave]

        # Lógica: Almacena la mejor k-partición PRE-REFINAMIENTO en el caché inter-k para el warm-start.
        #         IMPORTANTE: se guarda la partición ANTES de la búsqueda local (Fase 6.5) a propósito.
        #         Así la generación de candidatos del siguiente k (que deriva un candidato dividiendo el
        #         grupo más costoso de la mejor (k-1)-partición) es DETERMINISTA e idéntica a la versión
        #         sin refinamiento. Esto garantiza que, para todo k, el pool de candidatos contenga la
        #         misma solución base que antes y, por tanto, que el refinamiento solo pueda IGUALAR o
        #         REDUCIR la pérdida respecto a la versión previa (mejora monótona, sin regresión).
        # Sintaxis: `self._cache_mejor_por_k[k] = lista` — inserta o sobreescribe la entrada en O(1) amortizado.
        self._cache_mejor_por_k[k] = mejor_particion

        # ── Fase 6.5: Refinamiento por búsqueda local (Opt 7) ────────────────
        # Lógica: Pule la mejor k-partición moviendo variables entre grupos y conservando solo los
        #         movimientos que REDUCEN estrictamente δ_k. Solo afecta la Solution retornada, NO la
        #         cadena de warm-start (que ya guardó la partición pre-refinamiento). El refinamiento es
        #         barato porque reutiliza el caché de marginales (Opt 6) y está acotado por
        #         _MAX_REFINAMIENTO_EVALS y por _REFINAMIENTO_N_MAX.
        # Sintaxis: Reasignación múltiple — el método retorna la mejor terna (partición, emd, dist),
        #           que puede ser la misma de entrada si ningún movimiento mejoró la pérdida.
        mejor_particion, mejor_emd, mejor_dist = self._refinar_local(
            mejor_particion, mejor_emd, mejor_dist
        )

        # ── Fase 7: Formatear y construir Solution ───────────────────────────
        # Lógica: Genera las etiquetas S₁,...,Sₖ usando subíndices Unicode para la visualización.
        # Sintaxis: f-string con `_SUBSCRIPTS[i+1]` indexa la cadena "₀₁₂₃₄₅"; i+1 para empezar en ₁.
        etiquetas = [f"S{_SUBSCRIPTS[i + 1]}" for i in range(k)]

        # Lógica: Convierte la k-partición al formato list[list[tuple[int,int]]] que espera fmt_k_particion.
        # Sintaxis: Método interno que genera pares (tiempo, idx) agrupados por parte.
        partes_fmt = self._particion_a_partes_fmt(mejor_particion)

        # Lógica: Genera la representación visual multi-columna de la k-MIP para mostrar en consola.
        #         Cada columna muestra los alcances (mayúsculas) y mecanismos (minúsculas) de cada parte.
        # Sintaxis: `fmt_k_particion(partes, etiquetas)` retorna string con k columnas separadas por '|'.
        fmt_mip = fmt_k_particion(partes_fmt, etiquetas)

        # Lógica: Empaqueta todos los resultados en Solution para presentación uniforme con el resto del sistema.
        # Sintaxis: Constructor con keyword arguments — evita errores de posición y mejora legibilidad.
        return Solution(
            estrategia=KGEOMETRIC_LABEL,
            perdida=mejor_emd,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=mejor_dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    def _generar_candidatos_k(self, k: int) -> list:
        """
        Genera hasta n_objetivo candidatos k-partición y los retorna para
        evaluación con EMD en la Fase 5 de aplicar_estrategia.

        Fase A — 3 estrategias deterministas (ADA 24A §5 — Algoritmos Voraces):
            E₁ — LPT (Longest Processing Time):  c↓, asigna al grupo de menor peso acumulado
            E₂ — Cíclico ascendente:              c↑, asignación round-robin (pos mod k)
            E₃ — Bloques consecutivos:            grupos de ⌊n/k⌋ variables contiguas

        Conteo adaptativo (v0.8):
            n_objetivo = min(_C_CANDIDATOS_TOTAL, stirling(n, k))
            Para sistemas pequeños donde S(n,k) < 25, limita las iteraciones al número
            real de particiones distintas posibles, evitando bucles inútiles.

        Estrategia 4 — Warm-start inter-k (v0.8):
            Si self._cache_mejor_por_k[k-1] existe, genera un candidato k-partición
            dividiendo el grupo de mayor costo BFS de la mejor (k-1)-partición con LPT.
            Solo aplica cuando la misma instancia se usa secuencialmente para k=3,4,5.

        Fase B — (n_objetivo - len(candidatos_actuales)) perturbaciones aleatorias:
            Cada perturbación escala c[i] con factor uniforme ∈ [0.6, 1.4] y aplica
            LPT (iteraciones pares) o SPT (iteraciones impares) sobre c perturbado.
            Los candidatos duplicados (misma firma de grupos) se descartan antes de
            evaluar con EMD, evitando O(2^n) por duplicado.

        Garantía de E₁ (Graham, 1969):
            makespan(E₁) ≤ (4/3 - 1/(3k)) · OPT_makespan
            Para k=3: ≤ 1.22 · OPT_makespan  (cota sobre makespan, no sobre EMD)

        Complejidad:
            Fase A:          O(3 · n log n)
            Warm-start:      O(n log n)
            Fase B:          O((n_objetivo - len_base) · n log n)
            Total:           O(n_objetivo · n log n) = O(n log n)  [n_objetivo ≤ 25]
            Relación con BFS: O(C·n log n) << Θ(n·2^n) para n≥8 → costo despreciable

        Args:
            k: Número de partes k ∈ {3,4,5}.

        Returns:
            list: Hasta n_objetivo candidatos válidos y únicos. Cada candidato:
                  list[tuple[NDArray[np.int8], NDArray[np.int8]]] de longitud k.
        """
        # Lógica: Recupera el vector de costos c para la transición completa ini→fin directamente
        #         de _trans_matrix usando el índice entero del estado final.
        #         Reemplaza `tabla_transiciones.get((ini, fin), [])` con acceso O(1) a array NumPy.
        #         La fila fin_idx existe porque la Fase 3 completó todos los niveles hasta Hamming=n.
        # Sintaxis: `_estado_a_idx` convierte lista de bits a entero little-endian para indexar filas.
        #           `_trans_matrix[fin_idx]` devuelve view numpy de la fila — sin copia de datos.
        fin_idx = self._estado_a_idx(self.estado_final.tolist())
        costos_raw = self._trans_matrix[fin_idx]

        # Lógica: Convierte la fila numpy a lista Python de float64 para compatibilidad con
        #         `_greedy_multiway` y el resto del código que opera sobre listas nativas.
        #         No hay None en _trans_matrix (np.zeros garantiza 0.0 inicial), por lo que
        #         la sanitización anterior `c if c is not None else 0.0` ya no es necesaria.
        # Sintaxis: `.tolist()` convierte array NumPy a lista Python; cada elemento → float nativo.
        costos: List[float] = costos_raw.tolist()

        # Lógica: Recupera los arrays de índices de alcances (t+1) y mecanismos (t) del subsistema activo.
        # Sintaxis: @property de System; cada uno devuelve NDArray[np.int8] con los índices de variables.
        alcances = self.sia_subsistema.indices_ncubos
        mecanismos = self.sia_subsistema.dims_ncubos

        # Lógica: n = número de variables del subsistema = tamaño de cada grupo de partición.
        #         Asume |alcances| = |mecanismos| = n (caso típico del subsistema bien formado).
        # Sintaxis: `len(ndarray)` devuelve el número de elementos en la primera dimensión del array.
        n = len(alcances)

        # Lógica: Caso degenerado: si hay menos variables que partes, no se pueden formar k partes no vacías.
        # Sintaxis: Early return con lista vacía — el llamador maneja el caso sin candidatos.
        if n < k:
            return []

        # Lógica: Lista acumuladora de candidatos válidos para evaluación posterior.
        # Sintaxis: Lista vacía que se llenará con `.append()` si el candidato pasa la validación.
        candidatos: list = []

        # ── Estrategia 1: LPT Greedy (Algoritmo Voraz, ADA §5) ──────────────
        # Lógica: LPT = Longest Processing Time first. Ordena c↓ y asigna al grupo de menor carga.
        #         Garantía: makespan(LPT) ≤ (4/3 - 1/(3k))·OPT [Graham 1969].
        # Sintaxis: `_greedy_multiway(costos, n, k, descending=True)` retorna k listas de índices locales.
        grupos_1 = self._greedy_multiway(costos, n, k, descending=True)

        # Lógica: Mapea los índices locales [0..n-1] a los índices reales de alcances y mecanismos.
        # Sintaxis: `_grupos_a_particion` construye los NDArray[int8] finales del formato k_partir.
        p1 = self._grupos_a_particion(grupos_1, alcances, mecanismos, k)

        # Lógica: Agrega p1 solo si todas sus k partes son no vacías (precondición de System.k_partir).
        # Sintaxis: `if self._particion_valida(p)` llama al predicado booleano interno.
        if self._particion_valida(p1):
            candidatos.append(p1)

        # ── Estrategia 2: Round-robin ascendente ─────────────────────────────
        # Lógica: Ordena variables c↑ y las asigna cíclicamente (pos mod k).
        #         Distribuye variables baratas y caras uniformemente sin usar heap.
        # Sintaxis: `sorted(range(n), key=lambda i: costos[i])` genera índices ordenados ascendente.
        grupos_2: List[list] = [[] for _ in range(k)]
        orden_asc = sorted(range(n), key=lambda i: costos[i])
        for pos, idx in enumerate(orden_asc):
            # Lógica: `pos % k` asigna cíclicamente las variables a los k grupos en orden.
            # Sintaxis: Operador módulo `%` devuelve el residuo de la división enteras pos / k.
            grupos_2[pos % k].append(idx)

        # Lógica: Convierte grupos de índices a formato partición y valida partes no vacías.
        # Sintaxis: Mismo patrón que Estrategia 1.
        p2 = self._grupos_a_particion(grupos_2, alcances, mecanismos, k)
        if self._particion_valida(p2):
            candidatos.append(p2)

        # ── Estrategia 3: Bloques consecutivos ───────────────────────────────
        # Lógica: Divide los n índices en k bloques de tamaño ⌊n/k⌋; el último bloque absorbe el residuo.
        #         Captura estructuras de dependencia geométricamente contiguas en el n-cubo.
        # Sintaxis: `n // k` es división entera (floor division); el último bloque va hasta n.
        tam_bloque: int = n // k
        grupos_3: List[list] = []
        for j in range(k):
            # Lógica: Calcula los límites del bloque j; el último bloque (j=k-1) va hasta n para cubrir el residuo.
            # Sintaxis: Operador ternario `A if cond else B`; `j < k - 1` identifica todos los bloques salvo el último.
            inicio: int = j * tam_bloque
            fin: int = inicio + tam_bloque if j < k - 1 else n
            grupos_3.append(list(range(inicio, fin)))

        # Lógica: Convierte grupos de índices a formato partición y valida.
        # Sintaxis: Mismo patrón que Estrategias 1 y 2.
        p3 = self._grupos_a_particion(grupos_3, alcances, mecanismos, k)
        if self._particion_valida(p3):
            candidatos.append(p3)

        # ── Conteo adaptativo de candidatos objetivo ─────────────────────────
        # Lógica: stirling(n, k) = S(n,k) = número exacto de k-particiones distintas de n elementos.
        #         Para sistemas pequeños (ej. n=4, k=3 → S=6; n=5, k=5 → S=1), generar 25 candidatos
        #         es imposible porque no existen 25 particiones distintas. El límite adaptativo evita
        #         iterar _C_CANDIDATOS_TOTAL veces produciendo solo duplicados descartados.
        #         Para sistemas grandes (n≥8), stirling(n,k) >> 25, por lo que n_objetivo = 25 como antes.
        #         La función stirling calcula S(n,k) en Θ(n·k) — despreciable frente al BFS dominante.
        # Sintaxis: `min(A, B)` retorna el menor de los dos enteros; `stirling(n, k)` importado de funcs.system.
        n_objetivo: int = min(_C_CANDIDATOS_TOTAL, stirling(n, k))

        # ── Estrategia 4: Warm-start desde el caché inter-k ──────────────────
        # Lógica: Si existe la mejor (k-1)-partición en self._cache_mejor_por_k, genera un candidato
        #         k-partición dividiendo el grupo de mayor costo acumulado BFS en dos sub-grupos con LPT.
        #         Esta estrategia explora la región del espacio de búsqueda "cerca" del óptimo k-1,
        #         que estadísticamente es donde reside el óptimo k: refinar un sistema ya bien dividido
        #         es más eficiente que comenzar desde cero con una heurística sin contexto previo.
        #         El warm-start solo aplica cuando la misma instancia se usa para k=3, luego k=4, k=5.
        # Sintaxis: `_generar_candidato_warm_start` retorna list[tuple[NDArray,NDArray]] o None si no aplica.
        ws_candidato = self._generar_candidato_warm_start(k, costos)

        # Lógica: Añade el candidato warm-start si existe y supera la validación de partes no vacías.
        #         Al agregarlo ANTES de inicializar firmas_vistas, su firma queda precargada automáticamente,
        #         lo que impide que la Fase B lo regenere como duplicado.
        # Sintaxis: Doble condición: `is not None` verifica existencia; `_particion_valida` verifica invariante.
        if ws_candidato is not None and self._particion_valida(ws_candidato):
            candidatos.append(ws_candidato)

        # ── Fase B: Expansión por perturbación aleatoria ─────────────────────
        # Lógica: Las estrategias deterministas (E₁, E₂, E₃) y el warm-start cubren puntos fijos del espacio.
        #         Para n>8 existen millones de particiones distintas; generar candidatos adicionales con
        #         perturbaciones aleatorias del vector de costos amplía la cobertura ~8× sin salir de O(n log n).
        #         El costo extra O(C·2^n) en evaluaciones EMD (Fase 5) sigue siendo << Θ(n·2^n) dominante.
        #         n_objetivo (adaptativo) sustituye a _C_CANDIDATOS_TOTAL para evitar iteraciones inútiles
        #         cuando S(n,k) < 25 (sistemas pequeños donde ya no existen más particiones distintas).
        # Sintaxis: `n_objetivo - len(candidatos)` refleja cuántos candidatos faltan para alcanzar el objetivo.
        n_extra: int = n_objetivo - len(candidatos)

        # Lógica: Generador pseudoaleatorio local, independiente del estado global de random.
        #         La semilla es el hash del vector de costos: mismos datos → mismo resultado,
        #         lo que garantiza reproducibilidad de la búsqueda entre ejecuciones.
        # Sintaxis: `random.Random(seed)` crea instancia privada del Mersenne Twister;
        #           `hash(tuple(costos))` convierte la lista a tupla hasheable antes de hashear.
        _rng: random.Random = random.Random(hash(tuple(costos)))

        # Lógica: Conjunto de firmas de particiones ya generadas (base + expansión).
        #         Una firma = frozenset de frozensets de los índices de alcance de cada parte.
        #         Comparar firmas en O(k) evita evaluar con EMD (O(2^n)) particiones repetidas.
        # Sintaxis: `set()` mutable de Python; los frozensets son hasheables → válidos como elementos.
        firmas_vistas: set = set()

        # Lógica: Precarga las firmas de los 3 candidatos base para no regenerarlos en Fase B.
        #         `parte[0]` = NDArray de índices de alcances de esa parte (primera componente de la tupla).
        # Sintaxis: generator expression dentro de `frozenset(...)`; `.tolist()` convierte NDArray a lista.
        for _cand in candidatos:
            firmas_vistas.add(frozenset(frozenset(parte[0].tolist()) for parte in _cand))

        # Lógica: Itera hasta completar n_extra perturbaciones válidas y únicas.
        #         El bucle puede terminar antes si todas las perturbaciones generan duplicados
        #         (improbable para n≥4, pero posible para sistemas muy pequeños).
        # Sintaxis: `range(n_extra)` genera exactamente n_extra índices 0,1,...,n_extra-1.
        for _iter in range(n_extra):

            # Lógica: Perturba cada c[i] multiplicándolo por un factor uniforme ∈ [0.6, 1.4].
            #         El factor ±40% es suficiente para reordenar variables de costo similar
            #         (que son las que más influyen en la asignación greedy) sin destruir
            #         la información de rango del vector original.
            # Sintaxis: list comprehension; `_rng.uniform(a, b)` → float ∈ [a,b] del RNG local.
            c_pert: List[float] = [c * _rng.uniform(0.6, 1.4) for c in costos]

            # Lógica: Alterna LPT (c↓, iteraciones pares) y SPT (c↑, iteraciones impares).
            #         LPT prioriza variables caras; SPT prioriza variables baratas. Alternar
            #         explora los dos extremos del espacio greedy con cada par de perturbaciones.
            # Sintaxis: `_iter % 2 == 0` es True para 0,2,4,...; False para 1,3,5,...
            _desc: bool = (_iter % 2 == 0)

            # Lógica: Aplica la heurística greedy multiway sobre el vector perturbado.
            #         Genera k listas de índices locales [0..n-1] que forman los grupos.
            # Sintaxis: `_greedy_multiway(costos, n, k, descending)` es método interno heredado.
            grupos_pert = self._greedy_multiway(c_pert, n, k, descending=_desc)

            # Lógica: Convierte los grupos de índices locales a formato NDArray (alcances, mecanismos)
            #         compatible con System.k_partir que espera arrays de índices reales del subsistema.
            # Sintaxis: `_grupos_a_particion` mapea índices locales 0..n-1 → índices reales NDArray[int8].
            p_pert = self._grupos_a_particion(grupos_pert, alcances, mecanismos, k)

            # Lógica: Descarta la perturbación si alguna de las k partes quedó vacía.
            #         k_partir exige k partes no vacías; una parte vacía genera error en Fase 5.
            # Sintaxis: `continue` salta al siguiente _iter sin ejecutar el resto del bloque.
            if not self._particion_valida(p_pert):
                continue

            # Lógica: Calcula la firma del candidato perturbado para detectar duplicados.
            #         Dos particiones con los mismos conjuntos de alcances (sin importar el orden
            #         de las partes) producen la misma firma y se consideran equivalentes.
            # Sintaxis: `frozenset(frozenset(parte[0].tolist()) for parte in p_pert)` es O(k·n).
            firma = frozenset(frozenset(parte[0].tolist()) for parte in p_pert)

            # Lógica: Si la firma ya existe, este candidato es idéntico a uno anterior.
            #         Descartarlo aquí ahorra una evaluación EMD de O(2^n) en Fase 5.
            # Sintaxis: `in set` es O(1) amortizado por hash; `continue` salta al siguiente iter.
            if firma in firmas_vistas:
                continue

            # Lógica: Registra la firma y agrega el nuevo candidato único a la lista final.
            # Sintaxis: `.add(firma)` al set en O(1); `.append(p_pert)` a la lista en O(1) amortizado.
            firmas_vistas.add(firma)
            candidatos.append(p_pert)

        # Lógica: Retorna los candidatos válidos y únicos acumulados en Fases A y B.
        #         Fallback a [p1] garantiza al menos 1 candidato aunque todas las validaciones fallen
        #         (posible solo para n < k, que el guard al inicio ya maneja con return []).
        # Sintaxis: Operador ternario: `A if cond else B`; lista vacía es falsy en Python.
        return candidatos if candidatos else [p1]

    def _generar_candidato_warm_start(
        self,
        k: int,
        costos: List[float],
    ) -> "list | None":
        """
        Genera un candidato k-partición por warm-start desde la mejor (k-1)-partición cacheada.

        Estrategia de warm-start (extensión del enfoque voraz ADA §5):
            1. Recuperar la mejor (k-1)-partición del caché `_cache_mejor_por_k[k-1]`.
            2. Calcular el costo acumulado BFS de cada grupo: costo_j = Σ_{i ∈ Gⱼ} c[i].
            3. Identificar el grupo j* de mayor costo (cuello de botella del makespan).
            4. Dividir j* en dos sub-grupos con LPT (k=2 máquinas) sobre sus variables.
            5. Retornar la (k-1)-partición con j* reemplazado por los dos sub-grupos.

        Justificación teórica:
            El óptimo k-MIP generalmente se obtiene refinando el peor grupo del (k-1)-MIP.
            Esta heurística explora la región "cerca" del óptimo k-1 sin evaluar EMD hasta
            la Fase 5 (el warm-start solo construye el candidato en O(n log n)).
            Para sistemas donde el vector de costos tiene un "pico" dominante, el warm-start
            supera estadísticamente a las perturbaciones aleatorias de la Fase B.

        Args:
            k:      Número de partes de la nueva k-partición a generar.
            costos: Lista de costos BFS [c₀,...,c_{n-1}] del subsistema (sin None).
                    Los alcances y mecanismos se obtienen directamente del caché cacheado.

        Returns:
            list[tuple[NDArray, NDArray]]: k-partición por warm-start, o None si:
                - No existe (k-1)-partición en el caché (primera llamada o k=3 sin k=2 cacheado).
                - Ningún grupo de la (k-1)-partición tiene ≥ 2 variables de alcance para dividir.
                - Los sub-grupos resultantes no superan _particion_valida (partes vacías).

        Complejidad temporal: O(n log n) — dominada por _greedy_multiway del sub-split.
        Complejidad espacial: O(n) — arrays de índices de las k partes resultantes.
        """
        # Lógica: Si no existe caché para k-1, el warm-start no aplica en esta llamada.
        #         Para k=3 en la primera ejecución, k-1=2 no está en el caché porque k=2
        #         delega a super() y no actualiza _cache_mejor_por_k.
        # Sintaxis: `in dict` es O(1) amortizado; retorno anticipado evita lógica innecesaria.
        if (k - 1) not in self._cache_mejor_por_k:
            return None

        # Lógica: Recupera la mejor (k-1)-partición del caché inter-k.
        #         Es una list[tuple[NDArray, NDArray]] de longitud k-1.
        # Sintaxis: Acceso a dict por llave entera en O(1).
        particion_km1: list = self._cache_mejor_por_k[k - 1]

        # Lógica: Identifica el grupo de mayor costo acumulado BFS para dividirlo.
        #         "Costo del grupo j" = Σ_{v ∈ alc_j} c[v]; mide el peso computacional del grupo.
        #         Solo considera grupos con ≥ 2 variables de alcance (mínimo para dividir en 2).
        # Sintaxis: Variables sentinela inicializadas a valores imposibles para detectar "no encontrado".
        mejor_idx: int = -1
        mejor_costo_grupo: float = -1.0

        # Lógica: Itera sobre las k-1 partes de la partición anterior buscando el grupo más costoso.
        # Sintaxis: `enumerate(iterable)` desempaqueta (índice, elemento); el `_` descarta mecanismo_i.
        for i, (alc_i, _) in enumerate(particion_km1):

            # Lógica: Guardia de tamaño mínimo — un grupo de 1 elemento no puede dividirse en 2 sub-grupos no vacíos.
            # Sintaxis: `len(ndarray)` devuelve el número de elementos en la primera dimensión.
            if len(alc_i) < 2:
                continue

            # Lógica: Suma los costos BFS de las variables de alcance en este grupo.
            #         `int(v)` convierte np.int8 → int Python para indexar la lista costos (tipado estricto).
            #         La guardia `int(v) < len(costos)` protege contra índices fuera de rango si hay desajuste.
            # Sintaxis: Generator expression dentro de sum() — evaluación lazy, O(|alc_i|) pasos.
            costo_grupo: float = sum(
                costos[int(v)] for v in alc_i if int(v) < len(costos)
            )

            # Lógica: Actualiza el grupo candidato si este tiene mayor costo acumulado.
            # Sintaxis: Comparación de floats con `>`; asignación directa de índice y valor.
            if costo_grupo > mejor_costo_grupo:
                mejor_costo_grupo = costo_grupo
                mejor_idx = i

        # Lógica: Si ningún grupo tiene ≥ 2 elementos de alcance, el warm-start no puede generar
        #         una partición válida (no hay grupos divisibles). Retorno seguro con None.
        # Sintaxis: `== -1` verifica el sentinela de "no encontrado"; early return evita código defensivo.
        if mejor_idx == -1:
            return None

        # Lógica: Recupera los arrays de alcances y mecanismos del grupo identificado como cuello de botella.
        # Sintaxis: Indexación de lista con entero; desempaquetado de tupla en dos variables.
        alc_grande: NDArray = particion_km1[mejor_idx][0]
        mec_grande: NDArray = particion_km1[mejor_idx][1]

        # Lógica: Construye la lista de costos BFS de las variables del grupo a dividir.
        #         Se necesita un sub-vector de costos para aplicar LPT dentro del grupo.
        # Sintaxis: List comprehension con guardia de rango; `int(v)` para compatibilidad de tipos.
        costos_alc_grande: List[float] = [
            costos[int(v)] for v in alc_grande if int(v) < len(costos)
        ]

        # Lógica: Aplica LPT con k=2 para dividir el grupo grande de alcances en dos sub-grupos equilibrados.
        #         LPT minimiza el makespan del split — la garantía Graham (4/3 - 1/6)·OPT ≈ 1.17·OPT para k=2.
        # Sintaxis: `_greedy_multiway(costos, n, k=2, descending=True)` retorna 2 listas de índices locales [0..m-1].
        n_alc_grande: int = len(alc_grande)
        sub_grupos_alc: List[list] = self._greedy_multiway(
            costos_alc_grande, n_alc_grande, 2, descending=True
        )

        # Lógica: Construye los NDArray de alcances de los dos sub-grupos resultantes del split.
        #         Los índices locales de sub_grupos_alc[j] mapean posiciones dentro de alc_grande.
        # Sintaxis: `int(alc_grande[i])` convierte np.int8 → int → np.int8 para NDArray limpio.
        alc_sub1: NDArray = np.array(
            [int(alc_grande[i]) for i in sub_grupos_alc[0]], dtype=np.int8
        )
        alc_sub2: NDArray = np.array(
            [int(alc_grande[i]) for i in sub_grupos_alc[1]], dtype=np.int8
        )

        # Lógica: Para los mecanismos del grupo dividido se aplica la misma lógica de split con LPT.
        #         Tres casos posibles según el tamaño de mec_grande:
        #           ≥ 2: split con LPT de 2 → dos sub-grupos equilibrados de mecanismos.
        #           = 1: el único mecanismo va al primer sub-grupo; el segundo queda vacío → fallará validación.
        #           = 0: ambos sub-grupos vacíos → ambos fallarán _particion_valida → descarte seguro.
        n_mec_grande: int = len(mec_grande)

        # Lógica: Caso general con ≥ 2 mecanismos — aplica LPT sobre sus costos BFS.
        # Sintaxis: `if n_mec_grande >= 2` primera rama del árbol de casos.
        if n_mec_grande >= 2:
            # Lógica: Sub-vector de costos BFS de los mecanismos del grupo para guiar su split.
            # Sintaxis: List comprehension con misma guardia de rango que la usada para alcances.
            costos_mec_grande: List[float] = [
                costos[int(v)] for v in mec_grande if int(v) < len(costos)
            ]
            # Lógica: LPT con k=2 sobre los mecanismos del grupo grande.
            # Sintaxis: Mismo patrón que el split de alcances; `descending=True` para LPT.
            sub_grupos_mec: List[list] = self._greedy_multiway(
                costos_mec_grande, n_mec_grande, 2, descending=True
            )
            mec_sub1: NDArray = np.array(
                [int(mec_grande[i]) for i in sub_grupos_mec[0]], dtype=np.int8
            )
            mec_sub2: NDArray = np.array(
                [int(mec_grande[i]) for i in sub_grupos_mec[1]], dtype=np.int8
            )

        # Lógica: Caso especial con exactamente 1 mecanismo — asignarlo al primer sub-grupo.
        #         El segundo sub-grupo queda con mecanismo vacío → _particion_valida retornará False → descarte.
        # Sintaxis: `elif` encadena la condición; asignación directa del array original (sin copiar).
        elif n_mec_grande == 1:
            mec_sub1 = mec_grande
            mec_sub2 = np.array([], dtype=np.int8)

        # Lógica: Caso degenerado con 0 mecanismos — ambos sub-grupos inválidos → descarte en _particion_valida.
        # Sintaxis: `else` cubre el único caso restante (n_mec_grande == 0).
        else:
            mec_sub1 = np.array([], dtype=np.int8)
            mec_sub2 = np.array([], dtype=np.int8)

        # Lógica: Construye la k-partición resultante:
        #         — Todos los grupos de la (k-1)-partición anterior EXCEPTO el grupo dividido.
        #         — Más los dos sub-grupos (alc_sub1,mec_sub1) y (alc_sub2,mec_sub2).
        #         El orden final tiene k elementos: k-2 grupos inalterados + 2 sub-grupos nuevos.
        # Sintaxis: List comprehension con `if i != mejor_idx` filtra el grupo dividido; O(k) iteraciones.
        nueva_particion: list = [
            parte for i, parte in enumerate(particion_km1) if i != mejor_idx
        ]

        # Lógica: Agrega los dos sub-grupos al final de la nueva k-partición.
        # Sintaxis: `.append(tupla)` en O(1) amortizado; dos llamadas secuenciales.
        nueva_particion.append((alc_sub1, mec_sub1))
        nueva_particion.append((alc_sub2, mec_sub2))

        # Lógica: Valida que todos los k grupos tengan alcance y mecanismo no vacíos.
        #         Si algún sub-grupo quedó vacío (ej. n_mec_grande=1), retorna None para descarte silencioso.
        # Sintaxis: Operador ternario: `A if cond else B` — retorno en una línea sin if/else explícito.
        return nueva_particion if self._particion_valida(nueva_particion) else None

    def _greedy_multiway(
        self,
        costos: List[float],
        n: int,
        k: int,
        descending: bool = True,
    ) -> List[list]:
        """
        Greedy Multiway Partition — algoritmo de balanceo de carga (ADA 24A §5).

        Problema de balanceo de carga (Load Balancing):
            Dado n trabajos con tiempos t₁,...,tₙ y k máquinas,
            asignar cada trabajo a una máquina minimizando el makespan = max_j(Σᵢ∈Grupo_j tᵢ).

        Algoritmo LPT (Longest Processing Time first):
            1. Ordenar trabajos por tᵢ descendente — O(n log n)
            2. Para cada trabajo: asignar a la máquina de menor carga actual — O(log k) via heap
            3. Total: O(n log n) + O(n log k) = O(n log n)  [k ≤ 5, log k es constante]

        Estructura de datos: min-heap de pares (peso_acumulado, id_grupo).
            - heapq.heappop:  O(log k) — extrae el grupo de menor peso
            - heapq.heappush: O(log k) — reinserta el grupo con el nuevo peso

        Invariante de conservación:
            Σⱼ peso(grupo_j) = Σᵢ costos[i]   (el costo total se conserva)

        Args:
            costos:     Vector de costos c₀,...,c_{n-1} (sin None, sanitizado).
            n:          Número de variables a repartir.
            k:          Número de grupos.
            descending: True → LPT (c↓). False → SPT (c↑, menor primero).

        Returns:
            List[list]: k listas de índices locales [0..n-1], una por grupo.

        Complejidad temporal: O(n log n)
        Complejidad espacial: O(n) — k grupos + O(k) heap
        """
        # Lógica: Genera el orden de procesamiento de los n índices según la estrategia escogida.
        #         LPT (descending=True) ordena los índices del mayor al menor costo.
        # Sintaxis: `sorted(range(n), key=..., reverse=descending)` retorna lista de índices ordenados.
        orden: list = sorted(range(n), key=lambda i: costos[i], reverse=descending)

        # Lógica: Inicializa el min-heap con k entradas (0.0, gid) — k grupos con peso inicial cero.
        #         El invariante del heap garantiza que el grupo de menor peso esté siempre en la raíz.
        # Sintaxis: `[(0.0, gid) for gid in range(k)]` genera la lista inicial de tuplas para el heap.
        heap: list = [(0.0, gid) for gid in range(k)]

        # Lógica: `heapq.heapify` reorganiza la lista en heap válido en O(k) tiempo.
        # Sintaxis: Función del módulo `heapq` de la stdlib de Python; opera in-place.
        heapq.heapify(heap)

        # Lógica: k listas vacías que acumularán los índices asignados a cada grupo durante el greedy.
        # Sintaxis: `[[] for _ in range(k)]` — list comprehension con `_` para ignorar el contador.
        grupos: List[list] = [[] for _ in range(k)]

        # Lógica: Recorre cada variable en el orden establecido y la asigna al grupo de menor peso.
        #         Esta es la decisión voraz local que minimiza el desbalance en cada paso.
        # Sintaxis: `for idx in orden` itera los índices en el orden de costo establecido.
        for idx in orden:
            # Lógica: Extrae el grupo de menor peso acumulado del heap (decisión greedy principal).
            #         `peso` = costo total del grupo, `gid` = identificador del grupo (0..k-1).
            # Sintaxis: `heapq.heappop(heap)` desempaqueta la tupla mínima en O(log k).
            peso, gid = heapq.heappop(heap)

            # Lógica: Añade el índice de la variable actual al grupo seleccionado.
            # Sintaxis: `.append(idx)` modifica la lista del grupo in-place en O(1) amortizado.
            grupos[gid].append(idx)

            # Lógica: Reinserta el grupo en el heap con su nuevo peso = anterior + costo de la variable asignada.
            #         Esto actualiza la prioridad del grupo para el siguiente paso greedy.
            # Sintaxis: `heapq.heappush(heap, tupla)` inserta manteniendo la propiedad del heap en O(log k).
            heapq.heappush(heap, (peso + costos[idx], gid))

        # Lógica: Retorna los k grupos con sus índices asignados tras la ejecución completa del greedy.
        # Sintaxis: `return grupos` — lista de k listas de enteros (índices locales 0..n-1).
        return grupos

    def _grupos_a_particion(
        self,
        grupos: List[list],
        alcances: NDArray,
        mecanismos: NDArray,
        k: int,
    ) -> list:
        """
        Convierte grupos de índices locales [0..n-1] al formato k-partición de `System.k_partir()`.

        `System.k_partir()` espera `list[tuple[NDArray[int8], NDArray[int8]]]` donde:
            - `alcances_i`:   índices de las variables FUTURAS (t+1) asignadas a la parte i.
            - `mecanismos_i`: índices de las variables PRESENTES (t) asignadas a la parte i.

        Estrategia de asignación de mecanismos:
            Primero se asigna cada mecanismo al grupo cuyo alcance análogo (mismo índice)
            fue asignado por el greedy. Si el índice del mecanismo no aparece en alcances
            (caso de subsistemas asimétricamente substraídos), se usa round-robin (i % k).
            Esto garantiza que cada mecanismo quede en algún grupo sin importar la asimetría.

        Precondición:
            - len(alcances) == n (el número de variables usadas para las decisiones greedy).
            - len(grupos) == k, y cada índice en 0..n-1 aparece exactamente una vez.

        Args:
            grupos:     Lista de k listas; `grupos[j]` contiene los índices locales [0..n-1]
                        asignados a la parte j por el algoritmo greedy.
            alcances:   NDArray[int8] con los índices globales de las variables futuras (t+1).
            mecanismos: NDArray[int8] con los índices globales de las variables presentes (t).
            k:          Número de partes de la k-partición resultante.

        Returns:
            list[tuple[NDArray[int8], NDArray[int8]]]: k-partición en el formato esperado
            por `System.k_partir()`. Cada tupla = (alcances_parte, mecanismos_parte).

        Complejidad temporal: O(n + m) donde n = len(alcances), m = len(mecanismos).
        Complejidad espacial: O(n + m) — arrays resultantes de la k-partición.
        """
        # Lógica: Mapea cada ID de variable real proveniente de 'alcances' a su parte k asignada
        nodo_a_grupo = {}
        for j in range(k):
            for i in grupos[j]:
                if i < len(alcances):
                    nodo_a_grupo[alcances[i]] = j
        
        alcances_k = [[] for _ in range(k)]
        mecanismos_k = [[] for _ in range(k)]
        
        # Asignar alcances a su grupo respectivo
        for v in alcances:
            if v in nodo_a_grupo:
                alcances_k[nodo_a_grupo[v]].append(v)
                
        # Asignar mecanismos al mismo grupo que su alcance análogo,
        # si el mecanismo no está en alcances, se distribuye por round-robin.
        for i, v in enumerate(mecanismos):
            grupo = nodo_a_grupo.get(v, i % k)
            mecanismos_k[grupo].append(v)

        return [
            (
                np.array(alcances_k[j], dtype=np.int8),
                np.array(mecanismos_k[j], dtype=np.int8),
            )
            for j in range(k)
        ]

    def _particion_valida(
        self,
        particion: "list[tuple[NDArray, NDArray]]",
    ) -> bool:
        """
        Verifica que todas las k partes sean no vacías (precondición de `System.k_partir()`).

        Precondición formal:
            ∀i ∈ {0,...,k-1}: |Aᵢ| ≥ 1  ∧  |Mᵢ| ≥ 1

        Args:
            particion: Lista de k tuplas (alcance_i, mecanismo_i).

        Returns:
            bool: True si todos los alcances y mecanismos son arrays no vacíos.

        Complejidad temporal: O(k) — un chequeo de longitud por parte.
        """
        # Lógica: Verifica que ninguna parte tenga alcance o mecanismo de longitud 0.
        #         Si alguna parte fuera vacía, System.k_partir generaría una marginalización inválida.
        # Sintaxis: `all(pred for a, m in lista)` — generator expression con all(); cortocircuita al primer False.
        return all(len(alc) > 0 and len(mec) > 0 for alc, mec in particion)

    def _particion_a_clave(
        self,
        particion: "list[tuple[NDArray, NDArray]]",
    ) -> tuple:
        """
        Convierte una k-partición a clave hashable para `memoria_k_particiones`.

        Formato canónico de la clave (tupla de k sub-tuplas ordenadas):
            clave = (
                tuple(sorted([(0,m₀),(0,m₁),...,(1,a₀),(1,a₁),...]))  ← parte 0
                tuple(sorted([...]))                                    ← parte 1
                ...
            )
        donde tiempo=0 → mecanismo (ACTUAL), tiempo=1 → alcance (EFECTO).

        El ordenamiento canónico garantiza que la misma partición siempre produzca
        la misma clave, independientemente del orden de los elementos en los arrays.

        Args:
            particion: Lista de k tuplas (alcance_i, mecanismo_i).

        Returns:
            tuple: Representación hashable e inmutable de la k-partición.

        Complejidad temporal: O(n log n) — por el `sorted` interno.
        Complejidad espacial: O(n) — tamaño total de la clave.
        """
        # Lógica: Para cada parte, combina pares (0=mecanismo, idx) y (1=alcance, idx) en sub-tupla ordenada.
        #         El sorted garantiza un orden canónico independiente del orden de llegada.
        # Sintaxis: Generator expression dentro de tuple(); sorted() con lista concatenada `+`.
        return tuple(
            tuple(
                sorted(
                    # Lógica: Pares de mecanismo (tiempo=0=ACTUAL) del n-cubo presente.
                    # Sintaxis: List comprehension; `int(m)` convierte np.int8 a int Python nativo para hashabilidad.
                    [(0, int(m)) for m in mec_i]
                    # Lógica: Concatenación `+` con pares de alcance (tiempo=1=EFECTO) del n-cubo futuro.
                    # Sintaxis: Operador `+` concatena las dos listas antes de pasarlas a sorted().
                    + [(1, int(a)) for a in alc_i]
                )
            )
            for alc_i, mec_i in particion
        )

    def _particion_a_partes_fmt(
        self,
        particion: "list[tuple[NDArray, NDArray]]",
    ) -> "list[list[tuple[int, int]]]":
        """
        Convierte una k-partición al formato esperado por `fmt_k_particion`.

        `fmt_k_particion` espera `partes: list[list[tuple[int, int]]]` donde
        cada par (tiempo, idx) sigue la convención de `fmt_parte_q`:
            tiempo = 0 (ACTUAL)  → variable presente / mecanismo  → letras minúsculas
            tiempo = 1 (EFECTO)  → variable futura  / alcance     → letras MAYÚSCULAS

        Ejemplo para parte i = (alcance=[0,2], mecanismo=[0,2]):
            → [(0,0),(0,2),(1,0),(1,2)]
            → fmt_parte_q → top="|A,C|", bottom="|a,c|"

        Args:
            particion: Lista de k tuplas (alcance_i, mecanismo_i).

        Returns:
            list[list[tuple[int, int]]]: k listas de pares (tiempo, idx).

        Complejidad temporal: Θ(n) — un pase lineal por todos los elementos.
        """
        # Lógica: Para cada parte, combina pares de mecanismo (tiempo=0) y alcance (tiempo=1).
        #         El orden mecanismo → alcance sigue la convención de fmt_parte_q.
        # Sintaxis: List comprehension externo sobre k partes; `+` concatena las dos sub-listas.
        return [
            # Lógica: Pares (0, idx) para los mecanismos (variables presentes en t) de la parte i.
            # Sintaxis: `[(0, int(m)) for m in mec_i]` — list comprehension; int() para tipo Python nativo.
            [(0, int(m)) for m in mec_i]
            # Lógica: Concatenación con pares (1, idx) para los alcances (variables futuras en t+1) de la parte i.
            # Sintaxis: `+` entre listas Python concatena en una nueva lista; O(|mec_i|+|alc_i|).
            + [(1, int(a)) for a in alc_i]
            for alc_i, mec_i in particion
        ]

    def _dist_particion(self, particion: list) -> NDArray:
        """
        Calcula la distribución marginal de una k-partición reutilizando un caché de marginales
        por (índice de cubo, conjunto-mecanismo). Equivalente exacto, pero más rápido, a
        `self.sia_subsistema.k_partir(particion).distribucion_marginal()` (Optimización 6).

        Fundamento de la factorización:
            En `System.k_partir`, cada n-cubo c con c.indice ∈ Aᵢ se transforma en
            c' = c.marginalizar(c.dims ∖ Mᵢ). Luego `distribucion_marginal` evalúa cada c'
            en el sub-estado inicial restringido a c'.dims y guarda 1 − P(c'). Por tanto el
            valor marginal del cubo i depende ÚNICAMENTE de (c.indice, Mᵢ): NO depende del
            resto de la partición. Esto permite cachear el valor por (índice, mecanismo) y
            reutilizarlo en todos los candidatos y movimientos de búsqueda local que compartan
            ese mismo par, evitando re-ejecutar el costoso `np.mean` sobre 2^d celdas.

        Args:
            particion: Lista de k tuplas (alcance_i, mecanismo_i) como NDArray[int8].

        Returns:
            NDArray[np.float32]: Distribución marginal (probabilidad OFF por n-cubo), en el
            mismo orden que `sia_subsistema.ncubos`, idéntica a la de k_partir+distribucion_marginal.

        Complejidad temporal:  O(n) por consulta cacheada; O(n · 2^d) la primera vez por (cubo, Mᵢ).
        Complejidad espacial:  O(número de pares (cubo, mecanismo) distintos) en el caché.
        """
        # Lógica: Alias local del subsistema y de su estado inicial para evitar dereferencias `self.`
        #         repetidas dentro del bucle (microoptimización de legibilidad y velocidad).
        # Sintaxis: Asignación de referencias — no copia los objetos, solo crea nombres locales.
        sub = self.sia_subsistema
        estado = sub.estado_inicial

        # Lógica: Mapa índice_de_cubo → mecanismo de la parte que lo contiene en su ALCANCE.
        #         Replica exactamente el `indice_a_mecanismo` que construye System.k_partir.
        # Sintaxis: Doble bucle sobre la partición; `int(idx)` normaliza np.int8 → int como clave.
        indice_a_mec: dict = {}
        for alc_i, mec_i in particion:
            for idx in alc_i:
                indice_a_mec[int(idx)] = mec_i

        # Lógica: Array de salida con un valor por n-cubo, en el orden de sub.ncubos (igual que
        #         distribucion_marginal, que itera enumerate(self.ncubos)).
        # Sintaxis: `np.empty(size, dtype)` reserva memoria sin inicializar — se llena en el bucle.
        dist = np.empty(sub.indices_ncubos.size, dtype=np.float32)

        # Lógica: Recorre cada n-cubo del subsistema calculando (o recuperando del caché) su marginal.
        # Sintaxis: `enumerate(sub.ncubos)` produce (posición i, objeto NCube) — i indexa `dist`.
        for i, cube in enumerate(sub.ncubos):
            # Lógica: Índice global del cubo, usado tanto para el mapa como para la clave de caché.
            # Sintaxis: `int(...)` convierte np.int8 a int Python nativo (hashable y comparable).
            ind = int(cube.indice)

            # Lógica: Mecanismo de la parte que contiene este cubo en su alcance; None si el cubo no
            #         pertenece a ninguna parte (rama defensiva, igual que el `else cube` de k_partir).
            # Sintaxis: `dict.get(clave)` retorna None si la clave no existe, sin lanzar KeyError.
            mec_i = indice_a_mec.get(ind)

            if mec_i is not None:
                # Lógica: Clave de caché — el conjunto-mecanismo se vuelve frozenset para ser hashable
                #         e independiente del orden de los índices dentro del array.
                # Sintaxis: `frozenset(generador)` crea un conjunto inmutable; `(ind, fs)` es la tupla-llave.
                clave = (ind, frozenset(int(m) for m in mec_i))

                # Lógica: Si el valor marginal de este (cubo, mecanismo) ya fue calculado, se reutiliza
                #         directamente, ahorrando la marginalización y la indexación.
                # Sintaxis: `.get(clave)` retorna el valor cacheado o None; `continue` salta al próximo cubo.
                val = self._cache_marg.get(clave)
                if val is not None:
                    dist[i] = val
                    continue

                # Lógica: Cache miss — marginaliza el cubo eliminando las dimensiones que NO están en
                #         el mecanismo Mᵢ, exactamente como `cube.marginalizar(setdiff(dims, Mᵢ))` en k_partir.
                # Sintaxis: `np.setdiff1d(A, B)` = elementos de A no presentes en B = dims ∖ Mᵢ.
                mcube = cube.marginalizar(np.setdiff1d(cube.dims, mec_i))
            else:
                # Lógica: Cubo fuera de todo alcance — se evalúa el cubo intacto (rama `else cube` de k_partir).
                #         No se cachea porque es un caso límite poco frecuente.
                # Sintaxis: `clave = None` marca que no se debe escribir en el caché al final.
                clave = None
                mcube = cube

            # Lógica: Evalúa el cubo marginalizado en el sub-estado inicial, idéntico a distribucion_marginal:
            #         si conserva dimensiones, selecciona la celda del estado inicial; si no, usa el escalar.
            # Sintaxis: `mcube.dims.size` es 0 (falsy) cuando el cubo quedó sin dimensiones tras marginalizar.
            if mcube.dims.size:
                # Lógica: Sub-estado inicial restringido a las dimensiones que sobreviven en el cubo.
                # Sintaxis: Generator expression dentro de tuple(); `estado[j]` indexa el estado inicial.
                sub_estado = tuple(estado[j] for j in mcube.dims)
                # Lógica: Selección de la celda según la notación activa (big/little endian) del sistema.
                # Sintaxis: `seleccionar_subestado(tupla)` reordena la tupla según la notación; indexa el ndarray.
                prob = mcube.data[seleccionar_subestado(sub_estado)]
            else:
                # Lógica: Cubo colapsado a escalar — su único valor es la probabilidad buscada.
                # Sintaxis: `mcube.data` es un ndarray 0-dimensional; participa en aritmética como escalar.
                prob = mcube.data

            # Lógica: La distribución marginal almacena la probabilidad de estado OFF = 1 − P(ON).
            # Sintaxis: `1.0 - prob` opera sobre escalar o ndarray 0-d; el resultado es el valor marginal.
            val = 1.0 - prob

            # Lógica: Guarda el valor en el caché solo cuando el cubo tenía mecanismo asociado (clave válida).
            # Sintaxis: `if clave is not None` evita escribir entradas con llave None de la rama defensiva.
            if clave is not None:
                self._cache_marg[clave] = val

            # Lógica: Escribe el valor marginal del cubo i en la posición correspondiente de la distribución.
            # Sintaxis: Asignación indexada; numpy castea el escalar a float32 automáticamente.
            dist[i] = val

        # Lógica: Devuelve la distribución marginal completa de la k-partición.
        # Sintaxis: `return` entrega el NDArray al llamador (Fase 5 o búsqueda local).
        return dist

    def _particion_a_grupos(self, particion: list, alcances: NDArray) -> "list | None":
        """
        Reconstruye la asignación de grupos en índices LOCALES [0..n-1] a partir de una k-partición.

        Es la operación inversa parcial de `_grupos_a_particion`: mapea cada índice global de
        alcance a su posición local (su columna en el vector de costos) y agrupa esas posiciones
        según la parte a la que pertenecen. Sirve de punto de partida para la búsqueda local,
        que opera sobre grupos de índices locales y los reconvierte con `_grupos_a_particion`.

        Args:
            particion: Lista de k tuplas (alcance_i, mecanismo_i).
            alcances:  NDArray[int8] con los índices globales de las variables futuras (orden canónico).

        Returns:
            list[list[int]] | None: k listas de índices locales; None si la partición no cubre
            exactamente las n variables de `alcances` (estructura incompatible con el refinamiento).

        Complejidad temporal: O(n) — un pase por los alcances de todas las partes.
        """
        # Lógica: Mapa índice_global → posición_local (columna en el vector de costos / orden de alcances).
        # Sintaxis: Dict comprehension; `int(alcances[i])` normaliza la clave a int Python nativo.
        pos = {int(alcances[i]): i for i in range(len(alcances))}

        # Lógica: Por cada parte, traduce sus índices globales de alcance a posiciones locales.
        # Sintaxis: List comprehension interna con guardia `if int(v) in pos` para ignorar índices ajenos.
        grupos: list = []
        for alc_i, _ in particion:
            grupos.append([pos[int(v)] for v in alc_i if int(v) in pos])

        # Lógica: Verifica que la partición cubra exactamente las n variables; si no, el refinamiento
        #         no puede operar de forma consistente y se aborta de forma segura.
        # Sintaxis: `sum(len(g) for g in grupos)` cuenta el total de índices locales asignados.
        if sum(len(g) for g in grupos) != len(alcances):
            return None

        # Lógica: Retorna la lista de grupos en índices locales lista para la búsqueda local.
        # Sintaxis: `return` entrega la estructura al llamador (_refinar_local).
        return grupos

    def _refinar_local(
        self,
        particion: list,
        emd_actual: float,
        dist_actual: NDArray,
    ) -> tuple:
        """
        Búsqueda local de primera-mejora sobre la mejor k-partición encontrada (Optimización 7).

        Algoritmo (Local Search / Hill Climbing — ADA 24A, mejora de heurísticas voraces):
            Representa la solución como una asignación de las n variables a k grupos. En cada pase,
            intenta mover cada variable de su grupo a otro grupo; reconstruye la k-partición,
            la valida y evalúa su δ_k. Acepta el PRIMER movimiento que reduce estrictamente δ_k
            (estrategia first-improvement) y reinicia el pase desde la nueva solución. Termina
            cuando ningún movimiento mejora o se agota el presupuesto de evaluaciones.

        Garantía de no-regresión:
            La solución devuelta tiene δ_k ≤ δ_k de entrada SIEMPRE (mejora monótona), porque solo
            se aceptan movimientos con mejora estricta y, en el peor caso, se devuelve la entrada.

        Acotación de costo (clave para sistemas grandes):
            - Se desactiva si n > _REFINAMIENTO_N_MAX para NO añadir trabajo a sistemas grandes.
            - El número de evaluaciones EMD está acotado por _MAX_REFINAMIENTO_EVALS.
            - Cada evaluación reutiliza el caché de marginales (Opt 6), por lo que mover una sola
              variable solo recomputa los marginales de los grupos afectados, no de todo el sistema.

        Args:
            particion:   Mejor k-partición de la Fase 6 (list[tuple[NDArray, NDArray]]).
            emd_actual:  δ_k de esa partición.
            dist_actual: Distribución marginal de esa partición.

        Returns:
            tuple[list, float, NDArray]: (mejor_particion, mejor_emd, mejor_dist) tras el refinamiento.

        Complejidad temporal: O(_MAX_REFINAMIENTO_EVALS · n · 2^d) en el peor caso (acotada y << BFS).
        """
        # Lógica: Recupera índices de alcance y mecanismo del subsistema y el número de variables n.
        # Sintaxis: @property de System que retornan NDArray[int8]; `len` da el conteo de variables.
        sub = self.sia_subsistema
        alcances = sub.indices_ncubos
        mecanismos = sub.dims_ncubos
        n = len(alcances)
        k = self.k

        # Lógica: Compuerta de tamaño — para subsistemas grandes el refinamiento se desactiva para no
        #         encarecer el tiempo (prioridad en sistemas grandes: reducir tiempo, no añadir trabajo).
        # Sintaxis: Early return de la terna de entrada sin modificar; `len(self.estado_inicial)` = n_mec.
        if len(self.estado_inicial) > _REFINAMIENTO_N_MAX:
            return particion, emd_actual, dist_actual

        # Lógica: Reconstruye la asignación de grupos en índices locales; si la estructura no es
        #         compatible (no cubre las n variables), se aborta devolviendo la entrada intacta.
        # Sintaxis: `is None` comprueba el centinela de incompatibilidad retornado por _particion_a_grupos.
        grupos = self._particion_a_grupos(particion, alcances)
        if grupos is None:
            return particion, emd_actual, dist_actual

        # Lógica: Mejores valores conocidos hasta ahora; se actualizan al aceptar un movimiento.
        # Sintaxis: Asignación múltiple inicial — apuntan a la solución de entrada.
        mejor_part, mejor_emd, mejor_dist = particion, emd_actual, dist_actual

        # Lógica: Contador de evaluaciones EMD consumidas, acotado por _MAX_REFINAMIENTO_EVALS.
        # Sintaxis: Entero inicializado en 0; se incrementa tras cada evaluación de candidato.
        evals = 0

        # Lógica: Bandera que indica si el pase actual encontró una mejora; controla el reinicio.
        # Sintaxis: `True` para entrar al menos una vez al bucle while.
        mejoro = True

        # Lógica: Repite pases mientras el último haya mejorado y quede presupuesto de evaluaciones.
        # Sintaxis: `while cond_a and cond_b` — cortocircuita si alguna condición es falsa.
        while mejoro and evals < _MAX_REFINAMIENTO_EVALS:
            mejoro = False

            # Lógica: Recorre cada grupo de origen `gi` del cual se intentará extraer una variable.
            # Sintaxis: `range(k)` itera los k grupos por su índice.
            for gi in range(k):
                # Lógica: No se vacía un grupo: si tiene una sola variable, moverla dejaría el grupo
                #         sin alcance y la partición sería inválida.
                # Sintaxis: `<= 1` salta el grupo con `continue` sin intentar movimientos.
                if len(grupos[gi]) <= 1:
                    continue

                # Lógica: Itera una copia de los miembros del grupo origen (copia porque la lista se
                #         muta al mover variables, y no se debe modificar lo que se está iterando).
                # Sintaxis: `list(grupos[gi])` crea una copia superficial de los índices del grupo.
                for v in list(grupos[gi]):
                    # Lógica: Prueba mover la variable v a cada grupo destino gj distinto del origen.
                    # Sintaxis: `range(k)` itera destinos; el guardia salta gj == gi.
                    for gj in range(k):
                        if gj == gi:
                            continue
                        # Lógica: Respeta el presupuesto de evaluaciones; si se agota, corta el bucle interno.
                        # Sintaxis: `break` sale del for de destinos; los controles externos propagan la salida.
                        if evals >= _MAX_REFINAMIENTO_EVALS:
                            break

                        # Lógica: Aplica tentativamente el movimiento: quita v de gi y lo añade a gj.
                        # Sintaxis: `list.remove(v)` elimina la primera aparición; `list.append(v)` lo agrega al final.
                        grupos[gi].remove(v)
                        grupos[gj].append(v)

                        # Lógica: Reconstruye la k-partición candidata a partir de los grupos modificados.
                        # Sintaxis: `_grupos_a_particion` mapea índices locales → NDArray de alcances/mecanismos.
                        cand = self._grupos_a_particion(grupos, alcances, mecanismos, k)

                        # Lógica: Solo evalúa si la partición candidata es válida (k partes no vacías).
                        # Sintaxis: `_particion_valida` retorna bool; evita evaluaciones inútiles.
                        if self._particion_valida(cand):
                            # Lógica: Distribución y pérdida del candidato usando el evaluador cacheado (Opt 6).
                            # Sintaxis: Encadenamiento _dist_particion → emd_efecto; cuenta una evaluación.
                            dist = self._dist_particion(cand)
                            emd = emd_efecto(dist, self.sia_dists_marginales)
                            evals += 1

                            # Lógica: Acepta el movimiento solo si mejora estrictamente la pérdida (con un
                            #         epsilon para evitar oscilaciones por ruido de punto flotante).
                            # Sintaxis: `emd < mejor_emd - 1e-12` exige mejora estricta superior al epsilon.
                            if emd < mejor_emd - 1e-12:
                                mejor_emd, mejor_dist, mejor_part = emd, dist, cand
                                mejoro = True
                                # Lógica: First-improvement — se conserva el movimiento (no se revierte) y se
                                #         reinicia la exploración desde la nueva solución mejorada.
                                # Sintaxis: `break` sale del for de destinos manteniendo el estado de `grupos`.
                                break
                            else:
                                # Lógica: Movimiento sin mejora — se revierte para restaurar el estado previo.
                                # Sintaxis: Operaciones inversas remove/append devuelven v al grupo origen.
                                grupos[gj].remove(v)
                                grupos[gi].append(v)
                        else:
                            # Lógica: Candidato inválido — se revierte el movimiento sin evaluar EMD.
                            # Sintaxis: Mismas operaciones inversas que restauran `grupos`.
                            grupos[gj].remove(v)
                            grupos[gi].append(v)

                    # Lógica: Si hubo mejora en este punto, se interrumpe el recorrido de variables para
                    #         reiniciar el pase desde la solución mejorada (first-improvement).
                    # Sintaxis: `if mejoro: break` propaga la salida hacia el for de grupos.
                    if mejoro:
                        break

                # Lógica: Propaga la salida del pase hacia el while para reiniciar con `grupos` actualizado.
                # Sintaxis: `if mejoro: break` rompe el for de grupos de origen.
                if mejoro:
                    break

        # Lógica: Devuelve la mejor terna encontrada; idéntica a la entrada si nada mejoró.
        # Sintaxis: `return` entrega la tupla (partición, emd, dist) al llamador (aplicar_estrategia).
        return mejor_part, mejor_emd, mejor_dist
