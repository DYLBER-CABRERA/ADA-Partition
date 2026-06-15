import heapq
from src.constants.error import ERROR_INCOMPATIBLE_SIZES
from src.models.core.system import System
from src.constants.base import NET_LABEL, STR_ZERO
from src.funcs.base import ABECEDARY
from src.middlewares.slogger import SafeLogger
from src.funcs.base import emd_efecto
from src.models.base.sia import SIA
from src.constants.base import (
    ACTUAL,
    EFECTO,
    TYPE_TAG,
)
from src.constants.models import (
    GEOMETRIC_ANALYSIS_TAG,
    GEOMETRIC_LABEL,
    GEOMETRIC_STRAREGY_TAG,
)
from src.controllers.manager import Manager
from src.funcs.format import fmt_biparte_q
from src.middlewares.profile import profiler_manager, profile
from src.models.core.solution import Solution
import numpy as np
import time
from typing import List, Dict, Tuple

from concurrent.futures import ThreadPoolExecutor
import itertools

class GeometricSIA(SIA):
    def __init__(self, gestor: Manager):
        # Lógica: Inicializa la cadena de herencia — SIA.__init__ configura el gestor, el estado inicial
        #         y los atributos base que aplicar_estrategia necesita (sia_subsistema, sia_tiempo_inicio, etc.).
        # Sintaxis: `super().__init__(gestor)` invoca el __init__ de la clase padre SIA en la MRO de Python.
        super().__init__(gestor)
        # Lógica: Inicia la sesión del gestor de profiling con un nombre derivado de la red actual
        #         (ej. "NET10A") para agrupar los reportes HTML de esta ejecución en un mismo directorio.
        # Sintaxis: f-string combina NET_LABEL ("NET"), la longitud del estado inicial y la página del gestor.
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        # Lógica: Par de etiquetas [minúsculas, mayúsculas] para formatear nodos presentes y futuros;
        #         índice 0 (minúsculas) → mecanismo (presentes); índice 1 (mayúsculas) → alcance (futuros).
        # Sintaxis: `tuple(s.lower() for s in ABECEDARY)` convierte la tupla de mayúsculas a minúsculas perezosamente.
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        # Lógica: Logger seguro con el nombre de la estrategia para trazar los hitos del análisis geométrico.
        # Sintaxis: `SafeLogger(tag)` construye el logger con el tag como nombre del archivo .log.
        self.logger = SafeLogger(GEOMETRIC_STRAREGY_TAG)
        # Lógica: Almacén legado de costos de transición como dict de tuplas. Reemplazado por
        #         `_trans_matrix` (NDArray float32) para acceso O(1) por índice entero en vez de hash.
        # Sintaxis: `dict ={}` es inicialización a dict vacío; se mantiene por compatibilidad.
        self.tabla_transiciones: dict ={}
        # Lógica: Conjunto de todos los nodos (presentes + futuros) del subsistema; se usa para calcular
        #         el complemento de una partición en `nodes_complement`. Se asigna en `aplicar_estrategia`.
        # Sintaxis: Declaración de tipo PEP 526 sin `=` — reserva el nombre del atributo sin asignar valor.
        self.vertices :set[tuple]
        # Lógica: Tabla auxiliar de adyacencia para el grafo BFS; mapea estado → vecinos.
        #         Actualmente no se usa activamente — la lógica BFS opera sobre `self.caminos`.
        # Sintaxis: `dict[int, list[tuple[int,int]]] = {}` anota el tipo y asigna dict vacío.
        self.tabla :dict[int, list[tuple[int, int]]] = {}
        # Lógica: Caché de particiones evaluadas; mapea el conjunto de nodos de una partición (como tupla)
        #         al par (emd, distribucion) calculado en `find_mip`. Es la fuente de verdad del MIP.
        # Sintaxis: `dict[tuple, tuple[float, float]]` anota el tipo del dict — solo informativo en runtime.
        self.memoria_particiones: dict[tuple[int, int], tuple[float, float]] = {}
        # Lógica: Reemplazan a tabla_transiciones (dict Python) como almacén principal de costos.
        #         _trans_matrix[estado_idx] = vector de n_fut costos para ese estado.
        #         _trans_valid[estado_idx] = True si ese estado ya fue computado (memoización).
        # Sintaxis: Se inicializan en None y se asignan en find_mip / aplicar_estrategia
        #           una vez conocidas las dimensiones n_mec y n_fut del subsistema.
        self._trans_matrix: np.ndarray | None = None
        self._trans_valid: np.ndarray | None = None

    @staticmethod
    def _estado_a_idx(estado) -> int:
        # Lógica: Convierte un estado binario (lista o NDArray de 0s/1s) al entero que lo representa
        #         en convenio little-endian: la posición 0 es el bit menos significativo (LSB).
        #         Permite indexar las filas de _trans_matrix en O(1) sin hash de tuplas Python.
        # Sintaxis: `reversed(list(estado))` invierte el orden de los bits; `map(str, ...)` los
        #           convierte a caracteres; `"".join(...)` forma la cadena binaria; `int(..., 2)`
        #           la interpreta en base 2. Para estado=[1,0,0] → "001" → int=1.
        return int("".join(map(str, reversed(list(estado)))), 2)

    @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray #! COMENTAR PARA UN SOLO ESTADO INICIAL
    ):
        """ vamos a hacer que vaya desde el estado inicial hasta el final, bit a bit diferente, llenando la tabla primero para distancias hamming 1 hasta n, con n la cantidad de bits que cambian del estado inicial al final. para esto podemos usar una tabla de transiciones, donde cada fila es un estado y cada columna es un bit. la tabla de transiciones se llena con los estados que se pueden alcanzar desde el estado inicial, y luego se va llenando la tabla de distancias hamming. para esto vamos a usar una lista de listas, donde cada lista es una fila de la tabla de transiciones. la primera fila es el estado inicial, y las siguientes filas son los estados alcanzables desde el estado inicial. la última fila es el estado final.
        paso a paso
        1. cargar la matriz, pasar a ncubos
        2. condicionar
        3. obtener los bits que cambian entre el estado inicial y el final
        4. obener vecinos del estado final que van hacia el estado inicial y calcular el costo de la transicion.
        5. para cada vecino, obtener los vecinos que van hacia el estado inicial y calcular el costo de la transicion.
        6. repetir hasta llegar al estado inicial.


        nota: intentar llenar la tabla desde el estado final hacia atras, pues al contrario habra dependencia de los valores de la tabla de los estados que van en camino hacia el estado final
        """
        # Lógica: Prepara el subsistema condicionando la TPM al estado inicial y restringiendo
        #         a los nodos de alcance y mecanismo — resultado almacenado en `self.sia_subsistema`.
        # Sintaxis: Llamada al método heredado de SIA; la TPM se pasa como argumento porque se cargó
        #           externamente para evitar releerla en cada llamada (modo multi-estado inicial).
        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm) #! COMENTAR PARA UN SOLO ESTADO INICIAL
        # self.sia_preparar_subsistema(condicion, alcance, mecanismo) #! DESCOMENTAR PARA UN SOLO ESTADO INICIAL

        # Lógica: Construye los identificadores de las variables futuras (EFECTO) del subsistema
        #         como pares (EFECTO, índice). Estos pares se usan en `nodes_complement` para distinguir
        #         variables futuras de presentes al calcular el complemento de una partición.
        # Sintaxis: `tuple(gen)` fuerza la evaluación del generador `((EFECTO, e) for e in ...)` en memoria;
        #           `indices_ncubos` son los índices de los nodos futuros del subsistema activo.
        futuro = tuple(
            (EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos
        )

        # Lógica: Construye los identificadores de las variables presentes (ACTUAL) del subsistema
        #         como pares (ACTUAL, índice) — simétrico al caso futuro.
        # Sintaxis: `dims_ncubos` son las dimensiones activas del mecanismo (variables presentes).
        presente = tuple(
            (ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos
        )

        # Lógica: Lista de vectores de probabilidad aplanados por nodo futuro, precalculados
        #         para que `calcular_costo` pueda acceder a P(estado) en O(1) por índice entero.
        # Sintaxis: `[]` inicializa la lista vacía; se llena con `.append()` en el bucle siguiente.
        self._flat_data = []

        # Lógica: Aplana la matriz de distribución de cada N-cubo a un vector 1D para indexación
        #         directa por entero, evitando overhead de hash en `calcular_costo`.
        # Sintaxis: `enumerate(iterable)` genera pares (idx, ncubo); `.ravel()` aplana el ndarray
        #           a 1D sin copiar datos si es posible (retorna view si el array es contiguo).
        for idx, ncubo in enumerate(self.sia_subsistema.ncubos):
            self._flat_data.append(ncubo.data.ravel())

        # Lógica: Crea el conjunto de todos los nodos (presentes + futuros) del subsistema; se usa
        #         en `nodes_complement` para calcular la diferencia de conjuntos sin bucles explícitos.
        # Sintaxis: `set(presente + futuro)` concatena las tuplas con `+` y construye un conjunto hash O(n).
        self.vertices = set(presente + futuro)

        # Lógica: Extrae los índices de las dimensiones activas (mecanismo) para proyectar el estado
        #         inicial global al subespacio del subsistema analizado.
        # Sintaxis: `dims_ncubos` es un ndarray de índices enteros — se usa para fancy indexing.
        dims = self.sia_subsistema.dims_ncubos

        # Lógica: Proyecta el estado inicial global al subespacio del mecanismo usando fancy indexing;
        #         solo los bits de las dimensiones activas del mecanismo son relevantes para el BFS.
        # Sintaxis: `array[ndarray_de_ints]` es fancy indexing de NumPy — extrae simultáneamente
        #           todas las posiciones en `dims` del array `estado_inicial` en una sola operación.
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]

        # Lógica: El estado final del BFS es el complemento bit a bit del estado inicial —
        #         el algoritmo busca la ruta de mínimo costo desde estado_inicial hasta su inverso.
        # Sintaxis: `1 - array` es broadcasting de NumPy: el escalar 1 se resta element-wise
        #           al ndarray, produciendo la inversión de bits sin bucle Python.
        self.estado_final = 1 - self.estado_inicial

        # Lógica: Ejecuta el algoritmo BFS geométrico sobre el hipercubo para encontrar la
        #         Minimum Information Partition (MIP) — la bipartición que minimiza el EMD.
        # Sintaxis: `self.find_mip()` es una llamada al método de la misma instancia; retorna
        #           la tupla de nodos de la partición óptima como clave de `memoria_particiones`.
        mip = self.find_mip()

        # Lógica: Formatea la partición MIP y su complemento en la representación visual de 2 columnas
        #         con purview (mayúsculas) y mecanismo (minúsculas) para la salida en Solution.
        # Sintaxis: `list(mip)` convierte la tupla a lista (requerido por fmt_biparte_q);
        #           `nodes_complement(mip)` retorna la lista de nodos no incluidos en la partición.
        fmt_mip = fmt_biparte_q(list(mip), self.nodes_complement(mip))

        # Construye la respuesta empaquetándola en la clase Solution
        # Sintaxis: Uso de 'return' para finalizar la función. Instanciación del constructor usando puros Argumentos de Palabra Clave (Keyword arguments - 'algo=valor') mejorando legibilidad.
        return Solution(
            estrategia= GEOMETRIC_LABEL,
            
            # Obtiene la pérdida del diccionario mediante el MIP devuelto
            # Sintaxis: Indexación en Diccionario por tupla 'dict[key]'. Como eso devuelve una tupla de respuesta '(pérdida, distribución)', se saca su elemento '0' (pérdida) con el '[0]'.
            perdida=self.memoria_particiones[mip][0], 
            
            distribucion_subsistema=self.sia_dists_marginales,
            
            # Recupera la distribución producto cruzada
            # Sintaxis: Idéntico al caso de arriba, pero extrae el segundo elemento de esa tupla usando indexación base cero '[1]'.
            distribucion_particion=self.memoria_particiones[mip][1],
            
            # Mide la duración total del cálculo topológico
            # Sintaxis: Resta aritmética entre dos valores numéricos flotantes, producto de las llamadas encadenadas al módulo base 'time'.
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            
            particion=fmt_mip,
        )
    
    def nodes_complement(self, nodes: list[tuple[int, int]]):
        # Lógica: Obtiene el complemento lógico, devolviendo los nodos del ecosistema que NO están en 'nodes'.
        # Sintaxis: 'set(A) - set(B)' usa la sobrecarga del operador aritmético '-' evaluando la diferencia entre 2 Conjuntos (Hashtable). 'list()' fuerza el resultado a una lista.
        return list(set(self.vertices) - set(nodes))
    
    def find_mip(self):
        """
        Implementa el algoritmo para encontrar la bipartición óptima
        utilizando el enfoque geométrico-topológico.
        """
        # Lógica: Registra en el logger el inicio del algoritmo BFS para trazar el progreso
        #         del análisis geométrico en el archivo .log de la sesión activa.
        # Sintaxis: `.critic(msg)` usa nivel CRITICAL del logger — el nivel más visible en consola.
        self.sia_logger.critic("empieza.")

        # Lógica: Alias locales para evitar la dereferencia `self.` repetida dentro del bucle BFS,
        #         lo que ahorra microsegundos en iteraciones intensivas.
        # Sintaxis: Asignación simple — Python no copia los arrays, solo crea referencias locales.
        estado_inicial = self.estado_inicial
        estado_final = self.estado_final
        
        # Lógica: Genera una lista [0, 1, ..., n] de las variables futuras involucradas.
        # Sintaxis: 'len(coleccion)' da el tamaño entero, 'range(X)' genera los números entre 0 e (X-1), y 'list(iter)' compacta los números iterados en una lista.
        self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))
        
        # Lógica: Plantea y ubica como el Nivel [0] inicial del Grafo al estado primigenio.
        # Sintaxis: Diccionario '{llave: valor}' donde se le aplica TypeHint con Two-Dimensional List (List[List[int]]). '.tolist()' transforma el output NumPy a una lista nativa.
        self.caminos: Dict[int, List[List[int]]] = {0: [estado_inicial.tolist()]}
        
        # Lógica: Inicializa el costo del nodo pivote hacia sí mismo con Puntuaciones Nulas 0.0
        # Sintaxis: Crea u obtiene la entrada de Diccionario cuya llave es una Tupla acoplada multi-nodo. Expresión Comprehensible para popular N cantidad de '0.0' en una lista vacía.
        # Lógica: Inicializa la matriz numpy de transiciones que reemplaza al dict tabla_transiciones.
        #         Tiene 2^n_mec filas (una por cada posible estado del mecanismo) y n_fut columnas
        #         (una por cada nodo futuro). Los valores son float32 para reducir uso de memoria
        #         a la mitad respecto a float64 sin perder precisión significativa.
        # Sintaxis: `1 << n_mec` = 2^n_mec usando desplazamiento bit a bit — más rápido que `2**n_mec`.
        #           `np.zeros(shape, dtype)` inicializa a cero — el estado ini→ini tiene costo 0.
        n_mec = len(self.estado_inicial)
        n_fut = len(self.sia_subsistema.indices_ncubos)
        self._trans_matrix = np.zeros((1 << n_mec, n_fut), dtype=np.float32)
        # Lógica: Array booleano de memoización: _trans_valid[i]=True significa que la fila i
        #         de _trans_matrix ya fue computada y puede usarse directamente.
        # Sintaxis: `np.zeros(..., dtype=bool)` crea array de False; bool ocupa 1 byte/elemento.
        self._trans_valid = np.zeros(1 << n_mec, dtype=bool)
        # Lógica: Marca el estado inicial (ini→ini, costo=0) como válido desde el inicio.
        #         Equivale a la línea original: tabla_transiciones[(ini,ini)] = [0.0]*n_fut.
        # Sintaxis: `_estado_a_idx` convierte la lista del estado inicial a su índice entero.
        ini_idx = self._estado_a_idx(self.caminos[0][0])
        self._trans_valid[ini_idx] = True
        
        # Lógica: Expande el BFS nivel a nivel desde el estado inicial hasta el estado final,
        #         calculando los costos de transición de cada estado en cada nivel del hipercubo.
        #         El número de niveles es igual al número de bits del estado (distancia Hamming máxima).
        # Sintaxis: `range(1, len(estado_inicial)+1)` itera niveles 1, 2, ..., n; el +1 incluye el último.
        for nivel in range(1, len(estado_inicial)+1):
            self.calcular_costos_nivel(estado_final,nivel)

        # Lógica: Barrer los niveles BFS para identificar los candidatos de partición más prometedores
        #         antes de evaluar el EMD real — reduce el número de bipartir() + emd_efecto() necesarios.
        # Sintaxis: Llamada al método de la misma instancia; retorna lista de [presentes, futuros].
        candidatos = self.identificar_particiones_optimas()
        
        # Lógica: Valida el listado pre-evaluado y escudriña su EMD real final.
        # Sintaxis: Iteración Desempaquetada en la cual 'enumerate(coleccion)' expone la tupla indexada al for en '(idx, (presente, futuros))'.
        for idx, (presentes, futuros) in enumerate(candidatos):
            # Recupera IDs reales basandose en las selecciones numéricas
            presentes = self.sia_subsistema.dims_ncubos[presentes]
            futuros = self.sia_subsistema.indices_ncubos[futuros]
            
            # Lógica: Obtiene el tensor marginal/probabilidad del hipercubo roto tras cortar tales enlaces.
            # Sintaxis: Encadenamiento de métodos; llamar una función e invocar la siguiente justo en lo que devuelva la anterior '(')'.
            dist =self.sia_subsistema.bipartir(futuros,presentes).distribucion_marginal()
            
            # Lógica: Evalúa el Earth Mover's Distance comprobando qué tanto falló el vector versus su contraparte Inacta
            emd = emd_efecto(dist, self.sia_dists_marginales)
            
            # Lógica: Vincula la estructura formateada de tuplas '(0:ausa, N)' y '(1:efecto, N)' en un arreglo combinado.
            # Sintaxis: 'array = [comprensión...]' y luego array.extend() agregan otra lista in-situ a la cola.
            key = [(0,nodo) for nodo in presentes]
            key.extend([(1,nodo) for nodo in futuros])
            # print(fmt_biparte_q(list(key), self.nodes_complement(key)))
            
            # Guarda en cache dict evaluativo asociando el Costo y Configuración del corte analizado
            self.memoria_particiones[tuple(key)] = (emd, dist)
            
        # Lógica: Elige y retorna el Corte/Partición Óptima que minimiza la métrica
        # Sintaxis: 'min(Diccionario, key=lambda llave: evaluacion)' evalúa un bucle transparente. Por cada llave extrae en el lambda su posición de tupla almacenada '(memoria[llave][0])'. Retorna la llave numérica con el mínimo 'emd'.
        return min(
            self.memoria_particiones, key=lambda k: self.memoria_particiones[k][0]
        )
    
    def calcular_costos_nivel(self,estado_final: np.ndarray, nivel):
        # Lógica: Número de bits del estado — determina el rango de índices a iterar en el flip de bits.
        # Sintaxis: `len(ndarray)` retorna la longitud del primer eje del array NumPy en O(1).
        n = len(estado_final)

        # Lógica: Conjunto de estados ya visitados en este nivel para evitar procesar el mismo estado
        #         dos veces cuando distintos caminos BFS convergen al mismo nodo.
        # Sintaxis: `set[tuple]` es la anotación de tipo; `set()` crea un conjunto vacío (hash table O(1) para `in`).
        visitados:set[tuple] = set()
        # Lógica: Inicializa la lista de estados del nivel actual; se llenará con los estados generados
        #         por flip de bits desde los estados del nivel anterior.
        # Sintaxis: `self.caminos[nivel] = []` crea una nueva entrada en el dict de caminos BFS.
        self.caminos[nivel] = []

        # Lógica: Lee la frontera del nivel anterior (distancia Hamming = nivel-1 desde el inicial)
        #         y genera todos los nuevos estados a distancia Hamming = nivel flipeando un bit más.
        # Sintaxis: `self.caminos[nivel-1]` es la lista de estados del nivel anterior del BFS.
        for estado_anterior in self.caminos[nivel - 1]:
            # Lógica: Convierte la lista Python a ndarray para usar operaciones NumPy de forma eficiente.
            # Sintaxis: `np.array(lista)` construye un ndarray a partir de una lista de enteros Python.
            estado_actual = np.array(estado_anterior)

            for i in range(n):
                # Lógica: Solo se hace flip al bit i si diffiere del estado final en esa posición —
                #         avanzar hacia el objetivo flipeando únicamente bits "incorrectos".
                # Sintaxis: `!=` comparación escalar entre elementos de ndarray indexados con `[i]`.
                if estado_actual[i] != estado_final[i]:

                    # Lógica: Copia el estado actual antes de modificarlo para evitar alterar
                    #         el estado del nivel anterior que se sigue usando en este bucle.
                    # Sintaxis: `.copy()` crea una copia independiente del ndarray — sin esto el flip
                    #           modificaría `estado_actual` y rompería las iteraciones posteriores.
                    nuevo_estado = estado_actual.copy()

                    # Lógica: Flip del bit i al valor objetivo (avance hacia estado_final).
                    # Sintaxis: Indexación y asignación directa en ndarray — O(1).
                    nuevo_estado[i] = estado_final[i]
                    nuevo_estado_tuple = tuple(nuevo_estado)

                    # Lógica: Verifica en O(1) si este estado ya fue generado en este nivel
                    #         para evitar calcular y guardar el mismo costo múltiples veces.
                    # Sintaxis: `not in set` usa el hash del elemento para la comprobación O(1).
                    if nuevo_estado_tuple not in visitados:
                        # Lógica: Registra el nuevo estado en la frontera del nivel actual como lista Python
                        #         para que el nivel siguiente pueda usarlo como punto de partida.
                        # Sintaxis: `.tolist()` convierte ndarray a lista nativa — necesario porque
                        #           las listas son hashables elemento a elemento en estructuras Python.
                        self.caminos[nivel].append(nuevo_estado.tolist())

                        # Lógica: Calcula y almacena en `_trans_matrix` el vector de costos
                        #         de transición desde el estado inicial hasta este nuevo estado.
                        # Sintaxis: `.tolist()` garantiza que las listas pasadas a `calcular_costo`
                        #           sean tipos Python nativos para comparación consistente con `==`.
                        self.calcular_costo(self.caminos[0][0],nuevo_estado.tolist(),self.idx_ncubos)

                        # Lógica: Marca el estado como visitado para no procesarlo de nuevo si otro
                        #         camino del nivel anterior converge a él.
                        # Sintaxis: `.add(elem)` inserta en el conjunto en O(1) amortizado.
                        visitados.add(nuevo_estado_tuple)

    def calcular_costo(self, estado_inicial: tuple, estado_final: tuple, ncubos: list[int]):
        """
        Calcula el costo de transición del estado inicial al estado final para todos
        los nodos futuros usando la función tx(i,j) = (1/2^dh) * (|X[i]-X[j]| + Σ tx(k,j))
        donde dh = distancia Hamming y la suma acumula costos de estados intermedios BFS.

        Optimización: usa _trans_matrix (NumPy 2D) en vez de tabla_transiciones (dict).
        Acceso O(1) por índice entero en vez de O(1) amortizado con hash de tupla Python.
        La fila fin_idx se escribe in-place con operaciones NumPy vectorizadas sin bucles Python.
        """
        # Lógica: Convierte el estado final a índice entero para acceder a su fila en _trans_matrix.
        #         Usa convenio little-endian: posición 0 es LSB → estado=[1,0,0] → índice 1.
        # Sintaxis: `_estado_a_idx` invierte la lista, convierte a str, une y parsea base-2.
        fin_idx = self._estado_a_idx(estado_final)

        # Lógica: Memoización O(1): si la fila ya fue calculada en una llamada anterior, retorna.
        #         Evita recalcular el mismo estado cuando múltiples ramas BFS lo visitan.
        # Sintaxis: `_trans_valid[fin_idx]` es elemento bool de array NumPy — evaluación O(1).
        if self._trans_valid[fin_idx]:
            return

        # Lógica: Número de bits distintos entre ini y fin — determina el nivel BFS y el factor.
        # Sintaxis: `self.hamming(a, b)` compara elemento a elemento con zip y cuenta diferencias.
        distancia_hamming = self.hamming(estado_inicial, estado_final)

        # Lógica: Factor topológico: penaliza estados más lejanos; cada bit extra divide a la mitad.
        #         1/2^1=0.5 (vecino directo), 1/2^2=0.25 (a dos pasos), etc.
        # Sintaxis: `1 << distancia_hamming` = 2^dh con desplazamiento bit a bit — más rápido que **
        factor = 1.0 / (1 << distancia_hamming)

        # Lógica: Índices enteros para indexar los vectores aplanados de probabilidades.
        #         `_flat_data[j][idx]` = P(estado idx → siguiente) para el nodo futuro j.
        #         La inversión del orden de bits alinea con el convenio little-endian de _flat_data.
        # Sintaxis: slicing `[::-1]` invierte una lista Python; map+join+int parsean en base 2.
        estado_ini_int = int("".join(map(str, estado_inicial[::-1])), 2)
        # estado_fin_int = int("".join(map(str, estado_final[::-1])), 2)  # REDUNDANTE: produce
        #   el mismo resultado que fin_idx (ya calculado con _estado_a_idx arriba), porque
        #   [::-1] y reversed(list(...)) invierten el orden de bits de la misma forma.
        estado_fin_int = fin_idx

        # Lógica: Vectorización NumPy: calcula |X[ini] - X[fin]| para TODOS los nodos futuros
        #         en una sola operación SIMD. Elimina el bucle Python original sobre ncubos.
        #         Resultado: vector float64 de longitud n_fut con las diferencias absolutas.
        # Sintaxis: `np.array([flat[idx] for flat in self._flat_data])` construye el vector de
        #           probabilidades por comprensión; la resta y np.abs operan element-wise.
        diffs = np.abs(
            np.array([flat[estado_ini_int] for flat in self._flat_data])
            - np.array([flat[estado_fin_int] for flat in self._flat_data])
        )

        # Lógica: Escribe los diffs base en la fila fin_idx de la matriz de transiciones.
        #         Operación in-place sobre la vista de la fila — sin copias intermedias en memoria.
        # Sintaxis: `_trans_matrix[fin_idx, :]` selecciona toda la fila; `=` asigna in-place.
        self._trans_matrix[fin_idx, :] = diffs

        # Lógica: Acumulación BFS: cuando hamming>1, los estados intermedios (nivel anterior)
        #         ya fueron calculados por el orden de expansión de calcular_costos_nivel.
        #         Para cada bit i que cambió, el estado con ese bit revertido ya tiene su fila
        #         válida y se suma vectorialmente a la fila actual — sin bucle sobre ncubos.
        # Sintaxis: `range(len(estado_inicial))` itera sobre los índices de bits posibles.
        if distancia_hamming > 1:
            for i in range(len(estado_inicial)):
                # Lógica: Solo los bits que difieren crean un estado intermedio válido.
                #         Si estado_inicial[i]==estado_final[i] ese bit no contribuye a la distancia.
                # Sintaxis: `!=` comparación escalar entre elementos de lista Python.
                if estado_inicial[i] != estado_final[i]:
                    # Lógica: Estado intermedio = estado_final con el bit i revertido a estado_inicial[i].
                    #         Tiene distancia Hamming = dh-1 respecto al estado inicial → ya calculado.
                    # Sintaxis: `list(estado_final)` copia la lista para evitar aliasing; `[i]=` muta la copia.
                    nuevo_estado = list(estado_final)
                    nuevo_estado[i] = estado_inicial[i]

                    # Lógica: Índice entero del estado intermedio para acceder a su fila en _trans_matrix.
                    # Sintaxis: `_estado_a_idx` con lista de ints → entero little-endian O(1).
                    tmp_idx = self._estado_a_idx(nuevo_estado)

                    # Lógica: Suma vectorial in-place: acumula el costo del camino intermedio.
                    #         Reemplaza el bucle Python `for n in ncubos: tabla[key][n] += tabla[tmp_key][n]`.
                    #         NumPy opera sobre el array completo en una instrucción CPU (SIMD).
                    # Sintaxis: `+=` in-place sobre fila de numpy; ambos operandos son arrays de shape (n_fut,).
                    self._trans_matrix[fin_idx] += self._trans_matrix[tmp_idx]

        # Lógica: Aplica el factor topológico a toda la fila en una sola multiplicación escalar.
        #         Reemplaza el bucle Python `for i,n in enumerate(...): tmp.append(factor*n)`.
        #         Broadcasting NumPy: escalar × array → nuevo array sin bucle Python.
        # Sintaxis: `*=` in-place: modifica _trans_matrix[fin_idx] directamente sin crear copia.
        self._trans_matrix[fin_idx] *= factor

        # Lógica: Marca la fila como válida para que futuras llamadas con el mismo estado la salteen.
        #         Finaliza el protocolo de memoización iniciado con la comprobación al inicio.
        # Sintaxis: Asignación de `True` (bool Python) a elemento de array numpy dtype=bool.
        self._trans_valid[fin_idx] = True

    def identificar_particiones_optimas(self):
        """
        Identifica las particiones óptimas barriendo los niveles BFS del hipercubo.

        Optimización: reemplaza accesos a tabla_transiciones (dict con hash de tuplas)
        por lecturas directas a _trans_matrix[idx] (array NumPy O(1) por índice entero).
        Los bucles Python sobre ncubos se reemplazan con np.where() y np.minimum()
        que operan sobre el vector completo de n_fut columnas en una sola instrucción.
        """
        # Lógica: Índice del estado final en _trans_matrix; su fila contiene los costos ini→fin.
        #         Reemplaza `key=(ini,fin)` y `tabla_transiciones[key]` con acceso O(1) a array.
        # Sintaxis: `_estado_a_idx` convierte la lista a entero little-endian para indexar filas.
        fin_idx = self._estado_a_idx(list(self.estado_final))

        # Lógica: Vector de costos ini→fin de longitud n_fut (uno por nodo futuro).
        #         Vista (no copia) de la fila de la matriz — lectura O(1) sin hash.
        # Sintaxis: `_trans_matrix[fin_idx]` es una view numpy; dtype float32.
        costos = self._trans_matrix[fin_idx]

        # Lógica: Lista acumuladora de candidatos [presentes, futuros] a evaluar con EMD.
        # Sintaxis: `[]` lista vacía Python; se llenará con .append() en los bucles siguientes.
        candidatos = []

        # Lógica: n_vars = número de nodos futuros = columnas de _trans_matrix.
        #         Más eficiente que len(costos) porque evita materializar la lista.
        # Sintaxis: `.shape[1]` accede a la dimensión columnas del array 2D en O(1).
        n_vars = self._trans_matrix.shape[1]

        # Lógica: Nivel 0 — genera n_vars candidatos base: cada uno fija todos los nodos
        #         como presentes y deja fuera un único nodo futuro (bipartición elemental).
        #         Explora todas las formas de separar exactamente 1 nodo futuro del resto.
        # Sintaxis: `range(n_vars)` itera índices 0..n_vars-1.
        for idx in range(n_vars):
            # Lógica: Presentes = todos los nodos del estado actual (ninguno excluido en nivel 0).
            # Sintaxis: `list(range(...))` genera [0, 1, ..., len(estado_final)-1].
            presentes = list(range(len(self.estado_final)))

            # Lógica: Futuros = todos los nodos futuros excepto el que se está aislando como corte.
            # Sintaxis: list comprehension con filtro `if i != idx` — O(n_vars).
            futuros = [i for i in range(n_vars) if i != idx]

            # Lógica: Agrega el par [presentes, futuros] como candidato de nivel 0.
            # Sintaxis: `.append([a, b])` añade una sublista al final de candidatos en O(1) amortizado.
            candidatos.append([presentes, futuros])

        # Lógica: Determina el nivel "mitad" del BFS para limitar la exploración.
        #         Niveles más allá de la mitad son redundantes por simetría del hipercubo.
        # Sintaxis: `%` es módulo para detectar paridad; `//` es floor division.
        es_par = len(self.caminos) % 2 == 0
        mitad = len(self.caminos) // 2 if es_par else (len(self.caminos) // 2) + 1

        # Lógica: Itera niveles BFS 1..mitad-1 buscando el mejor candidato en cada uno.
        #         Los estados de cada nivel tienen distancia Hamming = nivel respecto al inicial.
        # Sintaxis: `range(1, mitad)` excluye el nivel 0 (ya procesado) y el nivel mitad.
        for nivel in range(1, mitad):
            # Lógica: Costo centinela muy alto para que el primer estado real lo supere siempre.
            # Sintaxis: `1e5` = 100000.0 en notación científica float Python.
            costo_candidato_nivel = 1e5
            presentes_nivel: list = []
            futuros_nivel: list = []

            # Lógica: Examina todos los estados BFS del nivel actual para encontrar el óptimo.
            #         Cada estado es una lista de bits obtenida por flip progresivo desde estado_ini.
            # Sintaxis: `self.caminos[nivel]` es la lista de estados del nivel BFS actual.
            for estado in self.caminos[nivel]:
                # Lógica: Vectorización NumPy: calcula en cuáles posiciones el estado no cambió
                #         respecto al estado inicial → esos índices son los "presentes" de esta partición.
                #         Reemplaza el bucle Python `for idx,i in enumerate(estado): if i==ini[idx]: presentes.append(idx)`.
                # Sintaxis: `np.array(estado)` convierte lista; `== ini_arr` comparación element-wise;
                #           `np.where(...)[0]` devuelve array de índices donde la condición es True;
                #           `.tolist()` convierte a lista Python para compatibilidad con find_mip.
                estado_arr = np.array(estado)
                ini_arr    = np.array(self.caminos[0][0])
                presentes  = np.where(estado_arr == ini_arr)[0].tolist()

                # Lógica: Índice entero del estado actual para leer su fila en _trans_matrix.
                #         Reemplaza `tabla_transiciones.get((ini, estado), None)`.
                # Sintaxis: `_estado_a_idx` lista→int little-endian O(1).
                act_idx = self._estado_a_idx(estado)

                # Lógica: Estado complementario = flip de todos los bits del estado actual.
                #         Se usa para evaluar el "lado opuesto" de la partición greedy.
                # Sintaxis: `1 - estado_arr` es resta NumPy broadcasting escalar → array 0/1 invertido;
                #           `.tolist()` convierte a lista para _estado_a_idx.
                comp_idx = self._estado_a_idx((1 - estado_arr).tolist())

                # Lógica: Lee las filas de costos de la matriz para estado actual y complementario.
                #         Son vistas (views) directas — sin copia ni hash. O(1) cada una.
                # Sintaxis: `_trans_matrix[idx]` devuelve view de la fila; dtype float32.
                actual        = self._trans_matrix[act_idx]
                complementario = self._trans_matrix[comp_idx]

                # Lógica: Greedy vectorizado: elige el mínimo entre actual y complementario
                #         para cada nodo futuro en una sola operación NumPy.
                #         Reemplaza el bucle Python `for idx,_ in enumerate(idx_ncubos): if actual[idx]<=comp[idx]: ...`.
                # Sintaxis: `np.minimum(a, b)` opera element-wise sobre dos arrays de igual forma;
                #           retorna nuevo array con el mínimo en cada posición.
                costos_min = np.minimum(actual, complementario)

                # Lógica: Futuros = índices donde actual[i] <= complementario[i] (ruta más barata).
                #         `np.where` vectoriza la condición sobre todo el array sin bucle Python.
                # Sintaxis: `(actual <= complementario)` → array bool; `np.where(...)[0]` → array de índices;
                #           `.tolist()` convierte a lista Python.
                futuros = np.where(actual <= complementario)[0].tolist()

                # Lógica: Costo total del candidato = suma de los costos mínimos sobre todos los futuros.
                #         Reemplaza la acumulación `costo_candidato += actual[idx]` dentro del bucle.
                # Sintaxis: `.sum()` es método NumPy que reduce el array a escalar en O(n_fut);
                #           `float(...)` convierte escalar numpy a float Python para la comparación.
                costo_candidato = float(costos_min.sum())

                # Lógica: Actualiza el mejor candidato del nivel si este tiene menor costo total.
                # Sintaxis: `<` comparación de floats Python; bloque if asigna tres variables.
                if costo_candidato < costo_candidato_nivel:
                    costo_candidato_nivel = costo_candidato
                    presentes_nivel = presentes
                    futuros_nivel   = futuros

            # Lógica: Agrega el candidato ganador del nivel actual a la lista de candidatos.
            #         Será evaluado con EMD real en find_mip junto con los demás candidatos.
            # Sintaxis: `.append([a, b])` añade sublista; O(1) amortizado.
            candidatos.append([presentes_nivel, futuros_nivel])

        # Lógica: Retorna todos los candidatos encontrados (nivel 0 + niveles 1..mitad-1).
        #         find_mip los evaluará con bipartir().distribucion_marginal() + emd_efecto().
        # Sintaxis: `return` termina la función devolviendo la lista al llamador.
        return candidatos

    def hamming(self,a: List[int], b: List[int]) -> int:
        # Lógica: Ejecuta y valora en medición posicional cuánta "Distancia en error/distanciamiento o mutabilidad lógica" se suscita cruzada paralelamente entre 2 cadenas evaluando estamento por estamento y comparando cuántos componentes son diametralmente disonantes ante el otro vector pareado en la confrontativa.
        # Sintaxis: Agrupa colecciones dimensionales en tándem mediante el iterador constructor apareador nativo 'zip(a,b)'. Envuelve el chequeo 'x != y' (que por debajo evalúa Truthy a = 1 / Falsey a = 0) bajo un Comprensivo Generador Genérico dentro de las pinzas funcionales sumativas escalares inmediatas 'sum()' reduciendo el bloque for-loop de 4 líneas a 1 sola, retornando finalmente su resultado validado por enmarcamiento de Type-Hint devolutivo final declarado estrictamente con clausula final '-> int'.
        return sum(x != y for x, y in zip(a, b))