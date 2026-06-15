from colorama import Fore
from numpy.typing import NDArray
from typing import Callable
import pandas as pd
import numpy as np
import time

from src.controllers.manager import Manager

from src.models.base.sia import SIA
from src.models.core.system import System
from src.models.core.solution import Solution

from src.middlewares.slogger import SafeLogger
from src.middlewares.profile import profile, profiler_manager

from src.funcs.base import seleccionar_metrica, literales
from src.funcs.format import fmt_biparticion
from src.funcs.system import (
    biparticiones,
    generar_candidatos,
    generar_particiones,
    generar_subsistemas,
)
from src.models.base.application import aplicacion
from src.constants.base import (
    EXCEL_EXTENSION,
    NET_LABEL,
    TYPE_TAG,
    EFECTO,
    ACTUAL,
)
from src.constants.models import (
    BRUTEFORCE_FULL_ANALYSIS_TAG,
    BRUTEFORCE_STRAREGY_TAG,
    BRUTEFORCE_ANALYSIS_TAG,
    BRUTEFORCE_LABEL,
    DUMMY_ARR,
    DUMMY_EMD,
    ERROR_PARTITION,
)


class BruteForce(SIA):
    """
    Generador de soluciones mediante fuerza bruta sobre una red específica.

    Para hacer uso del debug en diferentes zonas del proceso:

    >>>    self.logger.info("General status update")
    >>>    self.logger.debug("Detailed debugging info")
    >>>    self.logger.debuging("debuging message")
    >>>    self.logger.error("Error occurred")

    Así mismo este se almacenará en el archivo con el nombre que hayamos asociado en el `setup_logger(...)`.
    Este archivo de profilling de extensión HTML lo arrastras hasta tu navegador y se visualizará la depuración del aplicativo a lo largo del tiempo en dos vistas, temporal y cumulativa sobre el coste temporal en subrutinas.
    """

    def __init__(self, gestor: Manager):
        # Lógica: Inicializa la cadena de herencia SIA para preparar el gestor,
        #         logger base y atributos de subsistema antes de configurar BruteForce.
        # Sintaxis: `super().__init__(gestor)` llama al __init__ de SIA en la MRO;
        #           en herencia simple equivale a SIA.__init__(self, gestor).
        super().__init__(gestor)
        # Lógica: Abre una sesión de profiling nombrada por tamaño de red y página
        #         para que el reporte HTML agrupe todos los análisis de esta ejecución.
        # Sintaxis: f-string construye el nombre concatenando NET_LABEL, longitud del
        #           estado inicial (número de nodos) y la letra de página (A, B...).
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        # Lógica: Selecciona en tiempo de construcción la función de métrica (emd_efecto
        #         o emd_causal) según la configuración global, evitando el if en cada llamada.
        # Sintaxis: `seleccionar_metrica` retorna una Callable; `aplicacion.distancia_metrica`
        #           es el string del enum MetricDistance (ej: "emd_efecto").
        self.distancia_metrica: Callable = seleccionar_metrica(
            aplicacion.distancia_metrica
        )
        # Lógica: Crea el logger con el tag de estrategia BruteForce para distinguir
        #         sus mensajes de los de otras estrategias en los archivos de log.
        # Sintaxis: `SafeLogger(tag)` construye un logger con 3 handlers (archivo detallado,
        #           archivo last, consola colorizada); el tag aparece en cada línea de log.
        self.logger = SafeLogger(BRUTEFORCE_STRAREGY_TAG)

    @profile(
        context={TYPE_TAG: BRUTEFORCE_ANALYSIS_TAG}
    )  # Descomentame y revisa el directorio `review/profiling/`! #
    def aplicar_estrategia(self, condiciones: str, alcance: str, mecanismo: str):
        """
        Análisis por fuerza brutal sobre una red específica para un sistema candidato llevado a un subsistema determinado por el alcance y mecanismo indicado por el usuario.

        Args:
        ----
            conditions (str): Condiciones de fondo, dónde se va a condicionar el sistema original como candidato, sean las dimensiones en 0 las que se condicionen.
            alcance (str): Elementos futuros que serán marginalizados si el bit está en cero (0) para la posición de la variable asociada.
            mecanismo (str): Elementos presentes que serán marginalizados si su bit asociado en cero (0) para la posición de la variable.

        Returns:
        -------
            None: El análisis como se aprecia puede ser medido mediante el decorador de profiling, así como si se desea para algún otro método.
        """
        # Lógica: Construye el subsistema a partir de las cadenas de bits, condicionando
        #         y marginalizando el sistema completo hasta el subsistema mínimo analizable.
        # Sintaxis: `sia_preparar_subsistema` modifica `self.sia_subsistema` y
        #           `self.sia_dists_marginales` como efectos secundarios en la instancia.
        self.sia_preparar_subsistema(condiciones, alcance, mecanismo)

        # Lógica: Inicializa una solución centinela con valores DUMMY para garantizar
        #         que siempre haya una solución retornable incluso si no se halla partición.
        # Sintaxis: `Solution(...)` con DUMMY_EMD=-1, DUMMY_ARR=[-1] y ERROR_PARTITION
        #           señaliza "sin resultado válido" sin lanzar excepción.
        solucion_base = Solution(
            BRUTEFORCE_LABEL,
            DUMMY_EMD,
            self.sia_dists_marginales,
            DUMMY_ARR,
            ERROR_PARTITION,
        )

        # Lógica: `small_phi` guarda la menor EMD vista hasta ahora; se inicializa con
        #         +∞ para que cualquier valor real lo reemplace en la primera iteración.
        # Sintaxis: `np.infty` es el float infinito positivo de NumPy; equivale a float("inf").
        small_phi = np.infty
        # Lógica: Almacena la distribución marginal de la partición con menor EMD,
        #         lista para incluirse en la solución final.
        # Sintaxis: `DUMMY_ARR = [-1]` es el centinela inicial; se sobreescribe al hallar la MIP.
        mejor_dist_marg: np.ndarray = DUMMY_ARR

        # Lógica: Extrae los índices de futuros (alcance) y presentes (mecanismo) del
        #         subsistema para determinar el espacio de biparticiones: (2^m)*(2^n).
        # Sintaxis: `.indices_ncubos` retorna los índices de los n-cubos (futuro, t+1);
        #           `.dims_ncubos` retorna las dimensiones activas (presente, t).
        futuros = self.sia_subsistema.indices_ncubos
        presentes = self.sia_subsistema.dims_ncubos
        biparticion_prim: tuple[tuple[int, ...], tuple[int, ...]]
        biparticion_dual: tuple[tuple[int, ...], tuple[int, ...]]
        # Lógica: m y n son los tamaños de futuros y presentes; el número total de
        #         biparticiones a evaluar es (2^m)*(2^n).
        # Sintaxis: `.size` es el atributo NumPy que retorna el conteo de elementos;
        #           equivale a `len(arr)` para arrays 1D.
        m, n = futuros.size, presentes.size

        # Lógica: Itera todas las biparticiones factibles para encontrar la MIP
        #         (Minimum Information Partition) que minimiza la pérdida φ.
        # Sintaxis: `biparticiones(futuros, presentes, total)` es un generador que yield
        #           pares (subalcance, submecanismo), evitando alocar todas las combinaciones en RAM.
        for subalcance, submecanismo in biparticiones(
            futuros, presentes, (1 << m) * (1 << n)
        ):
            # Lógica: Referencia local al subsistema; no copia datos porque System es
            #         inmutable por diseño — cada operación crea un nuevo objeto.
            # Sintaxis: Asignación simple de referencia; el System original no se modifica.
            subsistema = self.sia_subsistema
            # Lógica: Convierte los subconjuntos de índices a arrays int8 para compatibilidad
            #         con los métodos del n-cubo que esperan NDArray[np.int8].
            # Sintaxis: `np.array(iter, dtype=np.int8)` crea 1 byte por elemento,
            #           suficiente para índices de nodos ≤127.
            arr_alcance = np.array(subalcance, dtype=np.int8)
            arr_mecanismo = np.array(submecanismo, dtype=np.int8)

            # Lógica: Genera la bipartición del subsistema: cada n-cubo se marginaliza
            #         según su pertenencia al alcance o mecanismo de esta bipartición.
            # Sintaxis: `bipartir(alcance, mecanismo)` retorna un nuevo System con n-cubos
            #           modificados; el System original no se altera.
            particion = subsistema.bipartir(arr_alcance, arr_mecanismo)

            # Lógica: Calcula la distribución marginal de la partición y mide la EMD
            #         respecto al subsistema original para cuantificar la pérdida φ.
            # Sintaxis: `self.distancia_metrica` es la Callable seleccionada en __init__;
            #           se llama como función ordinaria con los dos vectores de distribución.
            part_marg_dist = particion.distribucion_marginal()
            emd_value = self.distancia_metrica(
                part_marg_dist, self.sia_dists_marginales
            )
            # Lógica: Actualiza la solución mínima si esta partición tiene menor pérdida.
            #         Guarda la bipartición primaria y su complemento (dual) para el formateo final.
            # Sintaxis: `set(presentes.data) - set(submecanismo)` calcula la diferencia de
            #           conjuntos Python; `.data` expone el buffer interno del ndarray.
            if emd_value < small_phi:
                small_phi = emd_value
                mejor_dist_marg = part_marg_dist
                biparticion_prim = submecanismo, subalcance
                biparticion_dual = (
                    set(presentes.data) - set(submecanismo),
                    set(futuros.data) - set(subalcance),
                )

        # Lógica: Formatea la bipartición óptima como string legible para mostrar al usuario
        #         en qué dimensiones ocurre el corte que minimiza la pérdida.
        # Sintaxis: `fmt_biparticion` recibe [mecanismo, alcance] para cada lado y retorna
        #           un string con la notación de partición (ej. "AB|C // DE|F").
        biparticion_formateada = fmt_biparticion(
            [biparticion_prim[ACTUAL], biparticion_prim[EFECTO]],
            [biparticion_dual[ACTUAL], biparticion_dual[EFECTO]],
        )

        # Lógica: Actualiza la solución centinela con los resultados reales del análisis
        #         y activa el anuncio de voz para notificar al usuario que terminó.
        # Sintaxis: Asignaciones directas de atributo de instancia; `hablar=True` dispara
        #           el hilo de TTS en Solution al retornar.
        solucion_base.perdida = small_phi
        solucion_base.distribucion_particion = mejor_dist_marg
        solucion_base.particion = biparticion_formateada
        solucion_base.tiempo_ejecucion = time.time() - self.sia_tiempo_inicio
        solucion_base.hablar = True

        return solucion_base

    @profile(context={TYPE_TAG: BRUTEFORCE_FULL_ANALYSIS_TAG})
    def analizar_completamente_una_red(self) -> None:
        """
        Se prepara el directorio de salida donde almacenaremos el análisis completo de una red específica.
        Este análisis consiste de para una red de N elementos en dos tiempos `t_0` y `t_1` para un único estado inicial, se crean todos los `{2^N}-1` factibles sistemas candidatos, posteriormente a cada uno sus `2^{m+n}` posibles biparticiones, excluyendo escenarios con alcances vacíos y finalmente cada bipartición de las `2^{m+n-1}-1` factibles.
        """
        # Lógica: Crea el directorio de salida antes de escribir archivos Excel,
        #         garantizando que la ruta exista sin importar si ya fue creada antes.
        # Sintaxis: `.mkdir(parents=True, exist_ok=True)` crea directorios intermedios
        #           automáticamente y no falla si el directorio ya existe — equivale a `mkdir -p`.
        self.sia_gestor.output_dir.mkdir(parents=True, exist_ok=True)

        # Lógica: Carga la TPM desde CSV y convierte el estado inicial de string binario
        #         a array int8 para construir el sistema completo.
        # Sintaxis: List comprehension sobre string itera cada carácter; `np.array(..., dtype=np.int8)`
        #           convierte los chars '0'/'1' a enteros de 1 byte.
        tpm = self.sia_cargar_tpm()
        initial_state = np.array(
            [canal for canal in self.sia_gestor.estado_inicial],
            dtype=np.int8,
        )
        # system = System(tpm, initial_state, debug_observer)
        system = System(tpm, initial_state)
        # Lógica: Delega el análisis completo de todos los candidatos al método privado,
        #         que itera sobre todos los posibles condicionamientos del sistema.
        # Sintaxis: `self.__analizar_candidatos` — el doble guión provoca name mangling
        #           a `_BruteForce__analizar_candidatos`, limitando acceso externo.
        self.__analizar_candidatos(system)
        print(f"""
{Fore.RED}Generación finalizada!{Fore.BLUE}\nRevisa tu directorio `review/resolver/`.
{Fore.WHITE}Tamaño de la red: {initial_state.size} nodos.
Estado incial: {initial_state}.
""")

    def __analizar_candidatos(self, sistema: System) -> None:
        """
        Genera todos los sistemas candidatos factibles para dar análisis, de forma que se almacenen luego como un documento excel para mejor visualización.

        Args:
        ----
            sistema (System): Sisteam completo que será condicionado según la combinación de dimensiones para condicionar/eliminar, formando el sistema candidato.
        """
        # Lógica: Obtiene el número de nodos a partir de la longitud del estado inicial,
        #         que determina cuántos bits de condicionamiento son posibles.
        # Sintaxis: `len(string)` retorna el número de caracteres del string binario;
        #           un string de n bits representa un sistema de n nodos.
        cantidad = len(self.sia_gestor.estado_inicial)
        # Lógica: Genera todas las combinaciones de dimensiones candidatas (2^n - 1 conjuntos
        #         no vacíos) para iterar sobre todos los posibles condicionamientos del sistema.
        # Sintaxis: `generar_candidatos(n)` devuelve un iterable de tuplas de índices;
        #           cada tupla es un subconjunto de dimensiones a condicionar.
        dim_candidatas = generar_candidatos(cantidad)

        # Lógica: Itera cada combinación de dimensiones, convierte a array int8 y procesa
        #         el sistema candidato resultante del condicionamiento.
        # Sintaxis: `np.array(dimensiones, dtype=np.int8)` convierte la tupla de índices
        #           a NDArray compatible con System.condicionar.
        for dimensiones in dim_candidatas:
            self.__procesar_candidato(sistema, np.array(dimensiones, dtype=np.int8))

    def __procesar_candidato(
        self, completo: System, condiciones: NDArray[np.int8]
    ) -> None:
        """Aplicamos condiciones de fondo sobre el sistema completo y continuamos la cadena para su análisis por subsistemas.

        Args:
        ----
            completo (System): Sistema completo a condicionar.
            condiciones (NDArray[np.int8]): Condiciones de fondo aplicadas sobre el sistema completo.
        """
        # Lógica: Aplica las condiciones de fondo al sistema completo, fijando las
        #         dimensiones condicionadas al valor de su estado inicial.
        # Sintaxis: `completo.condicionar(condiciones)` retorna un nuevo System;
        #           el sistema completo original no se modifica (diseño inmutable).
        candidato = completo.condicionar(condiciones)
        # Lógica: Calcula el nombre literal del candidato como las dimensiones que sobreviven
        #         al condicionamiento, para usarlo como nombre de archivo de resultados.
        # Sintaxis: `np.setdiff1d(A, B)` retorna elementos de A no presentes en B;
        #           `literales(arr)` convierte índices [0,1,2] a letras "ABC".
        nombre = literales(np.setdiff1d(candidato.dims_ncubos, condiciones))
        self.__procesar_subsistema(candidato, nombre)

    def __procesar_subsistema(
        self, mecanismo_removido: System, nombre_candidato: str
    ) -> None:
        """
        Genera todos los subsistemas para un sistema candidato.

        Args:
        ----
            mecanismo_removido (System): Mecanismo obtenido de algún condicionamiento realizado con anterioridad.
            nombre_candidato (str): El noombre del sistema candidato de forma amigable, este determinará el nombre del fichero donde se guardará la solución de su análisis, esto en el directorio `review/`.
        """
        # Lógica: Construye la ruta del archivo Excel de resultados usando el nombre
        #         del candidato, para que cada sistema tenga su propio archivo de análisis.
        # Sintaxis: Operador `/` de pathlib concatena Path y string; f-string interpola
        #           el nombre y la extensión Excel.
        results_file = (
            self.sia_gestor.output_dir / f"{nombre_candidato}.{EXCEL_EXTENSION}"
        )

        # Lógica: Abre el ExcelWriter como gestor de contexto para agregar múltiples hojas
        #         (una por subsistema) sin reabrir el archivo en cada iteración.
        # Sintaxis: `pd.ExcelWriter(path)` es un context manager; al salir del bloque `with`
        #           guarda y cierra el archivo correctamente aunque ocurra una excepción.
        with pd.ExcelWriter(results_file) as writer:
            # Lógica: Itera sobre todos los posibles subconjuntos de alcance y mecanismo
            #         para generar cada subsistema del candidato actual.
            # Sintaxis: `generar_subsistemas(dims)` es un generador que yield pares
            #           (alcance_removido, sub_present) de dimensiones a marginalizar.
            for alcance_removido, sub_present in generar_subsistemas(
                mecanismo_removido.dims_ncubos
            ):
                # Lógica: Omite subsistemas sin futuro (alcance removido == todos los índices),
                #         ya que no hay información causal que analizar en ese caso.
                # Sintaxis: La guarda booleana evita llamadas innecesarias y escrituras Excel
                #           para casos triviales sin nodos futuros.
                if not self.__deberia_omitir_subsistema(
                    alcance_removido, mecanismo_removido
                ):
                    self.__analizar_subsistema(
                        mecanismo_removido,
                        np.array(alcance_removido, dtype=np.int8),
                        np.array(sub_present, dtype=np.int8),
                        writer,
                    )

    def __deberia_omitir_subsistema(
        self, alcance_removido: tuple[int, ...], candidate: System
    ) -> bool:
        """
        Revisa si el alcance o futuro que se va a condicionar genera un subsistema sin futuro y por ende, no útil en el análisis sistémico, no hay un non-trivial effect cual dar revisión.

        Args:
        ----
            alcance_removido (tuple[int, ...]): tupla con índices asociados a las dimensiones que serán removidas.
            candidate (System): Sistema cual se removeran los alcances.

        Returns:
        -------
            bool: Determina si tienen el mismo tamaño, de serlo su diferencia será 0 y por ende no habrá futuro.
        """
        # Lógica: Si el alcance removido cubre todos los índices del sistema, no quedaría
        #         ningún nodo futuro — el subsistema sería trivial y debe omitirse.
        # Sintaxis: `len(tuple)` es O(1); `.indices_ncubos.size` retorna el conteo de
        #           n-cubos (nodos futuros) del sistema candidato en O(1).
        return len(alcance_removido) == candidate.indices_ncubos.size

    def __analizar_subsistema(
        self,
        candidato: System,
        alcance_removido: NDArray[np.int8],
        mecanismo_removido: NDArray[np.int8],
        writer: pd.ExcelWriter,
    ) -> None:
        """Analiza un sistema candidato y genera un condicionamiento para analizar sus subsistemas restantes.

        Args:
        ----
            candidato (System): Subsistema candidato a ser substraído de sus elementos con el fin de obtener un subsistema.
            alcance_removido (NDArray[np.int8]): El alcance o elementos futuros que serán marginalizados.
            mecanismo_removido (NDArray[np.int8]): El mecanismo o elementos presentes que serán marginalizados.
            writer (pd.ExcelWriter): escritor en la hoja de cálculo para un documento excel ya asociado.

        Se almacena el resultado del análisis de este subsistema en una hoja de excel con la representación literal del mismo.
        """
        # Lógica: Genera el subsistema marginalizando las dimensiones especificadas en
        #         alcance (futuro) y mecanismo (presente) del candidato.
        # Sintaxis: `.substraer(alcance, mecanismo)` retorna un nuevo System sin las
        #           dimensiones removidas; no modifica el candidato original.
        subsistema = candidato.substraer(alcance_removido, mecanismo_removido)
        # Lógica: Calcula la distribución marginal del subsistema como referencia para
        #         medir la pérdida EMD de cada bipartición.
        # Sintaxis: `.distribucion_marginal()` itera los n-cubos y extrae P(OFF)
        #           para cada nodo según el estado inicial.
        dist_marginal = subsistema.distribucion_marginal()

        # Lógica: Obtiene el nombre literal del subsistema para usarlo como nombre de
        #         la hoja Excel — identifica de forma legible el alcance y mecanismo restantes.
        # Sintaxis: El método privado calcula diferencias de conjuntos y convierte índices
        #           a letras para generar nombres como "AB|BC".
        nombre_subsistema = self.__get_nombre_subsistema(
            candidato, alcance_removido, mecanismo_removido
        )
        # Lógica: Analiza todas las biparticiones del subsistema, genera el DataFrame con
        #         las EMDs de cada una y lo escribe como hoja en el archivo Excel.
        # Sintaxis: `.to_excel(writer, sheet_name=nombre)` escribe el DataFrame como una
        #           hoja nueva en el ExcelWriter abierto en el bloque `with` padre.
        resultado = self.__analizar_particiones(dist_marginal, subsistema)
        resultado.to_excel(writer, sheet_name=nombre_subsistema)

    def __analizar_particiones(
        self, distribucion: NDArray[np.float32], subsistema: System
    ) -> pd.DataFrame:
        """Para cada subsistema se realiza su análisis por cada partición. Como tenemos entendido la primera partición es tirivial de forma que es ignorada (esto es representado luego con i=1 para la selección de etiquetas).
        Primeramente se obtienen las dimensiones totales del subsistema, tanto para mecanismos/filas (n) como alcances/columnas (m), sabemos que la cantidad de particiones con `k=2` (biparticiones) `P_k(S_{n, m}) = 2^(m+n-1)-1 = [(2^m-1)*(2^{n})]-1`, con esto podemos generar una matriz de `2^m` filas por `2^(m-1)` columnas y sustraemos la partición trivial.
        Precomputamos las llaves y así mismo las posibles particiones, donde indexamos el resultado de la emd claramente en el iterando módulo m o n para asociar correctamente la clave e incrementamos ambos, pero sólo j cuando i haga una rotación.
        Como se aprecia en el fichero `resolver/<red específica>/<estado inicial>/` la partición que interseca las claves (0,0) siempre debe estar vacía puesto es la partición trivial (donde de hecho no es una partición pues toda variable pertenece al mismo lado).

        Args:
        ----
            distribucion (NDArray[np.float32]): Distribución marginal que se comparará con la distribución marginal de la partición
            subsistema (System): Subsistema que será particionado y su partición analizada con este mismo mediante la EMD Efecto

        Returns:
        -------
            pd.DataFrame: Matriz que asociará en las filas los elementos presente o mecanismos de la partición y en las columnas los elementos futuros o alcances de la partición, esto de forma que los elementos que pertenezcan al mismo bit (0|1), pertenecen a la misma partición.
        """
        # Lógica: Obtiene los tamaños de futuros (m) y presentes (n) para calcular el espacio
        #         de biparticiones y definir las dimensiones del DataFrame de resultados.
        # Sintaxis: `.indices_ncubos.size` retorna el conteo de n-cubos (futuros);
        #           `.dims_ncubos.size` retorna el conteo de dimensiones activas (presentes).
        m, n = subsistema.indices_ncubos.size, subsistema.dims_ncubos.size

        # Lógica: Genera etiquetas binarias para indexar filas (mecanismos, 2^n valores)
        #         y columnas (alcances, 2^m-1 valores excluyendo partición trivial).
        # Sintaxis: f-string `f"{number:0{n}b}"` formatea como binario con ancho fijo n;
        #           `range(1 << n)` es range(0, 2^n); `1 << m - 1` equivale a 2^(m-1).
        llave_presente = [f"{number:0{n}b}" for number in range(1 << n)]
        llave_futuro = [f"{number:0{m}b}" for number in range(1 << m - 1)]

        # Lógica: Crea el DataFrame vacío con etiquetas binarias como índice y columnas;
        #         cada celda recibirá el valor EMD de la bipartición correspondiente.
        # Sintaxis: `dtype=np.float32` usa 4 bytes por celda en lugar de 8 (float64),
        #           reduciendo consumo de memoria para matrices grandes.
        resultados = pd.DataFrame(
            columns=llave_futuro,
            index=llave_presente,
            dtype=np.float32,
        )

        # Lógica: i=1 porque la partición trivial (i=0) se excluye por convención;
        #         j es el contador de columna que avanza cuando i completa una rotación.
        # Sintaxis: `i, j = 1, 0` es asignación múltiple simultánea (tuple unpacking).
        i, j = 1, 0
        # Lógica: Itera sobre todas las biparticiones no triviales, calcula la EMD de cada
        #         una y la almacena en la celda correspondiente del DataFrame.
        # Sintaxis: `generar_particiones(m, n)` es un generador que yield pares de arrays
        #           booleanos (alcance_bits, mecanismo_bits) para cada bipartición.
        for alcance, mecanismo in generar_particiones(m, n):
            # Lógica: Convierte los arrays de bits a arrays de índices de posiciones activas
            #         para pasar a bipartir(), que espera índices de nodos, no máscaras de bits.
            # Sintaxis: List comprehension con `enumerate`; `if bit` filtra solo posiciones con 1.
            sub_alcance = np.array([i for i, bit in enumerate(alcance) if bit])
            sub_mecanismo = np.array([i for i, bit in enumerate(mecanismo) if bit])

            # Lógica: Genera la bipartición del subsistema con estos índices de alcance y
            #         mecanismo, luego obtiene su distribución marginal para la comparación.
            # Sintaxis: `np.array(..., dtype=np.int8)` asegura el tipo correcto esperado por bipartir().
            particion = subsistema.bipartir(
                np.array(sub_alcance, dtype=np.int8),
                np.array(sub_mecanismo, dtype=np.int8),
            )

            dist_parte_marginal = particion.distribucion_marginal()
            # Lógica: Calcula la EMD entre la distribución de la partición y la del subsistema
            #         original para cuantificar la pérdida φ de esta bipartición específica.
            # Sintaxis: `self.distancia_metrica` es la Callable seleccionada en __init__;
            #           se invoca directamente como función con dos arrays de distribución.
            emd_value = self.distancia_metrica(dist_parte_marginal, distribucion)

            # Lógica: Convierte los arrays de bits a strings binarios para usarlos como
            #         coordenadas fila-columna en el DataFrame.
            # Sintaxis: `"".join(map(str, arr.astype(int)))` convierte cada elemento a int,
            #           luego a str, y los une sin separador para formar la etiqueta binaria.
            etiqueta_mecanismo = "".join(map(str, mecanismo.astype(int)))
            etiqueta_alcance = "".join(map(str, alcance.astype(int)))

            # Asignar el valor al DataFrame
            # Lógica: Almacena el valor EMD en la celda identificada por las etiquetas binarias
            #         de mecanismo (fila) y alcance (columna) del DataFrame.
            # Sintaxis: `resultados.loc[fila, columna] = valor` es el indexador label-based
            #           de pandas; más legible que iloc (numérico) para este contexto.
            resultados.loc[etiqueta_mecanismo, etiqueta_alcance] = emd_value

        return resultados

    def __get_nombre_subsistema(
        self,
        candidato: System,
        sub_alcance: NDArray[np.int8],
        sub_mecanismo: NDArray[np.int8],
    ) -> str:
        """
        Muestra de forma amigable el subsistema analizado, utilizando literales asociados con la dimensión respectiva.

        Args:
            candidato (System): Sistema candidato del que se obtendrán las dimensiones a ser representadas de tanto el mecanismo presente, como el alcance futuro.
            sub_alcance (NDArray[np.int8]): Alcance que será eliminado en el proceso.
            sub_mecanismo (NDArray[np.int8]): Mecanismo que será eliminado en el proceso.

        Returns:
            str: Literal con la representación del subsistema
        """
        # Lógica: Calcula las dimensiones que SOBREVIVEN en futuro y presente después de
        #         remover los alcances y mecanismos especificados — muestra lo que queda.
        # Sintaxis: `np.setdiff1d(A, B)` retorna elementos de A no presentes en B;
        #           `literales(arr)` convierte índices [0,1,2] a letras concatenadas "ABC".
        futuro_removido = np.setdiff1d(candidato.dims_ncubos, sub_alcance)
        presente_removido = np.setdiff1d(candidato.dims_ncubos, sub_mecanismo)
        return f"{literales(futuro_removido)}|{literales(presente_removido)}"
