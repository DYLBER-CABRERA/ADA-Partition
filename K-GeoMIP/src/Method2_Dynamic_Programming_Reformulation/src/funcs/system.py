from itertools import product, chain, combinations, islice
from typing import Generator, Tuple, Union
import numpy as np
from numpy.typing import NDArray


def generar_candidatos(n_vars: int):
    """
    Genera todas las combinaciones posibles para condicionamiento.
    Empieza desde conjuntos pequeños hasta el sistema completo.

    Args:
        n_vars: Número total de variables en el sistema

    Returns:
        Generador de conjuntos de variables a condicionar
    """
    # Lógica: Genera todos los subconjuntos propios de {0,...,n_vars-1} de tamaño r para r ∈ [0, n_vars-1],
    #         produciendo en total 2^n_vars - 1 combinaciones (se excluye r=n_vars porque el conjunto completo
    #         no puede condicionarse sobre sí mismo sin perder información del sistema candidato).
    # Sintaxis: Generator expression de doble bucle anidado; `combinations(range(n_vars), r)` genera C(n,r)
    #           subconjuntos de tamaño r — la expresión es perezosa y no materializa todos los combos en RAM.
    return (combo for r in range(n_vars) for combo in combinations(range(n_vars), r))


def generar_subsistemas(vars: tuple[int]):
    """
    Genera las combinaciones posibles para un sistema candidato de N variables.
    Son dos conjuntos de combinaciones que hacen un producto cartesiano.
    Las combinaciones van desde vacío hasta la N-1 combinación puesto generar la n-ésima combinación complicaría la posterior marginalización, esta recibe las dimensiones a descartar, pero, si no tiene dimensiones para marginalizar (conjunto vacío) no se realiza nada, por lo que retornar el n-ésimo elemento con la diferencia de dimensiones activas del sistema candidato haría se envíe una tupla vacua, es por ello iteramos cuantas variables tengamos y no N+1.

    Args:
        n_vars (int): Tamaño del sistema candidato, sus variables.

    Returns:
        Generador con combinaciones de subsistemas.
    """
    # Lógica: Construye la lista de todos los subconjuntos de `vars` (incluyendo ∅ y el conjunto completo)
    #         para el producto cartesiano. Se incluye r=len(vars) (completo) porque tanto alcance como
    #         mecanismo pueden necesitar seleccionar todas las variables del sistema candidato.
    # Sintaxis: list comprehension de doble bucle; `range(len(vars)+1)` incluye r=len(vars)
    #           gracias al +1 — range excluye el límite superior, por lo que sin él faltaría el completo.
    tiempos = [combo for r in range(len(vars) + 1) for combo in combinations(vars, r)]
    # Lógica: El producto cartesiano `tiempos × tiempos` produce todos los pares (alcance_i, mecanismo_j)
    #         posibles; ambos ejes son idénticos porque alcance y mecanismo pueden elegir libremente
    #         cualquier subconjunto de las mismas variables del sistema candidato.
    # Sintaxis: `product(a, b)` de itertools genera el producto cartesiano como generador perezoso O(1) en memoria.
    return product(tiempos, tiempos)


def generar_particiones_conjuntos():
    # Lógica: Función reservada para una futura extensión que genere particiones de conjuntos de forma
    #         directa sobre elementos arbitrarios. Actualmente no implementada; `pass` es el cuerpo vacío.
    # Sintaxis: `pass` es la sentencia vacía de Python — permite definir el cuerpo de una función sin código.
    pass


def generar_particiones(
    m: int,
    n: int,
    *,
    as_matrix: bool = False,
    as_generator: bool = True,
) -> Union[Generator[Tuple[np.ndarray, np.ndarray], None, None], np.ndarray]:
    """
    Versión para generar particiones binarias.
    Eficiente para valores grandes de M y N.

    Args:
        m: Tamaño de la primera parte
        n: Tamaño de la segunda parte
        square: Si True, retorna matriz 2D. Si False, retorna tuplas
        as_generator: Si True, usa generador para memoria eficiente
    """
    # Lógica: m < 1 es una precondición inválida — si el alcance tiene 0 elementos no puede
    #         construirse ninguna bipartición no trivial. Se lanza ValueError en vez de retornar
    #         silenciosamente para hacer el error visible al llamador.
    # Sintaxis: `raise ValueError(f"...")` interrumpe la ejecución con mensaje descriptivo;
    #           `{m}` interpola el valor de m en el mensaje de error.
    if m < 1:
        raise ValueError(f"Alcance trivial: Future no debe tener {m} elementos")

    # Lógica: Se usa 2^(m-1) en lugar de 2^m para el alcance porque la bipartición (∅, M) se excluye
    #         por convención — el alcance primario nunca es el conjunto vacío en este contexto.
    # Sintaxis: `1 << (m-1)` es desplazamiento de bits equivalente a 2^(m-1); más rápido que `2**(m-1)`.
    m_combinations = 1 << (m - 1)  # 2^(M-1)
    # Lógica: El mecanismo sí genera todos los 2^n subconjuntos posibles incluyendo ∅.
    # Sintaxis: `1 << n` = 2^n via desplazamiento bit a bit.
    n_combinations = 1 << n  # 2^N

    # Lógica: `np.empty` asigna la memoria sin inicializarla, lo que es más rápido que `np.zeros`
    #         porque los valores se sobreescribirán completamente con el broadcasting posterior.
    # Sintaxis: `np.empty((filas, cols), dtype)` reserva el bloque de memoria sin llenarlo.
    m_bits = np.empty((m_combinations, m), dtype=np.uint8)
    n_bits = np.empty((n_combinations, n), dtype=np.uint8)

    # Lógica: Crea columnas de índices con forma (N,1) para habilitar el broadcasting con el vector
    #         de desplazamientos — esto vectoriza la generación de representaciones binarias en una sola operación.
    # Sintaxis: `np.arange(N, dtype=np.uint32)[:, np.newaxis]` crea un array columna 2D de shape (N,1).
    m_indices = np.arange(m_combinations, dtype=np.uint32)[:, np.newaxis]
    n_indices = np.arange(n_combinations, dtype=np.uint32)[:, np.newaxis]

    # Lógica: Vector de posiciones de bit de mayor a menor peso (big-endian), usado como exponente
    #         de desplazamiento para extraer cada bit de los índices.
    # Sintaxis: `np.arange(m-1, -1, -1)` genera [m-1, m-2, ..., 0] en orden descendente.
    m_shifts = np.arange(m - 1, -1, -1, dtype=np.uint8)
    n_shifts = np.arange(n - 1, -1, -1, dtype=np.uint8)

    # Lógica: Broadcasting NumPy: (N,1) >> (m,) produce (N,m) — para cada fila i y columna j
    #         extrae el bit j del número i. `& 1` enmascara todos los bits excepto el LSB,
    #         produciendo la representación binaria de todos los índices en una sola operación.
    # Sintaxis: `>>` es desplazamiento de bits a la derecha; `& 1` es AND bit a bit con 1.
    m_bits = (m_indices >> m_shifts) & 1
    n_bits = (n_indices >> n_shifts) & 1

    if as_generator:

        def partition_generator():
            # Lógica: Para i=0 (primera fila de m_bits), empieza desde j=1 para evitar el par trivial
            #         (0...0, 0...0) — la partición (∅,∅) no es una bipartición válida del sistema.
            # Sintaxis: `m_bits[0]` accede a la primera fila del array 2D como view de shape (m,).
            m_row = m_bits[0]
            for j in range(1, n_combinations):
                yield m_row, n_bits[j]

            # Lógica: Para el resto de filas de m_bits (i≥1), itera sobre todos los j incluyendo j=0,
            #         porque si i≠0 el par (m_bits[i], n_bits[0]) ya no es la partición trivial.
            # Sintaxis: `range(1, m_combinations)` excluye i=0 (ya procesado arriba).
            for i in range(1, m_combinations):
                m_row = m_bits[i]
                for j in range(n_combinations):
                    yield m_row, n_bits[j]

        return partition_generator()

    if as_matrix:
        # Lógica: Calcula el número total de filas de la matriz resultado = producto de todas las combinaciones.
        # Sintaxis: `m_combinations * n_combinations` es la multiplicación escalar de los dos enteros.
        total_rows = m_combinations * n_combinations
        result = np.empty((total_rows, m + n), dtype=np.uint8)

        # Lógica: Crea vistas 3D de la matriz resultado para asignar m_bits y n_bits con broadcasting
        #         sin bucles Python — la vista comparte la memoria con `result`.
        # Sintaxis: `.reshape(a, b, c)` reinterpreta la forma del array sin copiar datos;
        #           `result[:, :m]` es una vista de las primeras m columnas.
        result_view_m = result[:, :m].reshape(m_combinations, n_combinations, m)
        result_view_n = result[:, m:].reshape(m_combinations, n_combinations, n)

        # Lógica: Broadcasting vectorizado: asigna todas las filas de m_bits y n_bits a la vez,
        #         replicando cada fila m_combinations veces en la dimensión del producto cartesiano.
        # Sintaxis: `m_bits[:, np.newaxis, :]` convierte (m_comb, m) a (m_comb, 1, m) para broadcasting;
        #           la asignación in-place `[:] =` llena la vista sin crear copias temporales.
        result_view_m[:] = m_bits[:, np.newaxis, :]
        result_view_n[:] = n_bits

        return result if not as_generator else (row for row in result)

    # Lógica: Modo lista: construye una lista de tuplas (m_bits_i, n_bits_j) para todos los pares válidos.
    #         Menos eficiente en memoria que el generador pero permite acceso aleatorio por índice.
    # Sintaxis: List comprehension de doble bucle; `m_bits[i]` y `n_bits[j]` son views del array 2D.
    return [
        (m_bits[i], n_bits[j])
        for i in range(m_combinations)
        for j in range(n_combinations)
    ]


def biparticiones(
    alcances: np.ndarray,
    mecanismos: np.ndarray,
    total=None,
):
    # Lógica: Calcula el número total de pares (subconj_alcance, subconj_mecanismo) posibles
    #         si no se provee explícitamente. Incluye los casos triviales (∅,∅) y (A,M) que luego se excluyen.
    # Sintaxis: `1 << arr.size` es 2^n via desplazamiento bit a bit; `.size` da el número de elementos.
    if total is None:
        total = (1 << alcances.size) * (1 << mecanismos.size)
    # Lógica: Genera el producto cartesiano de todos los subconjuntos de alcances y mecanismos,
    #         pero omite el primer elemento (∅,∅) y el último (A completo, M completo) — particiones triviales.
    # Sintaxis: `islice(it, 1, total-1)` de itertools retorna un slice perezoso del iterador:
    #           empieza en el índice 1 (salta (∅,∅)) y termina antes de total-1 (excluye (A,M) completo).
    return islice(
        product(subconjuntos(alcances), subconjuntos(mecanismos)), 1, total - 1
    )


def subconjuntos(arr: np.ndarray):
    # Lógica: Genera todos los subconjuntos de `arr` (incluyendo ∅ con r=0 y el conjunto completo con r=n)
    #         en orden de tamaño creciente; produce en total 2^n subconjuntos, donde n = len(arr).
    # Sintaxis: `chain.from_iterable(gen)` aplana el generador de generadores en un único iterable perezoso;
    #           `combinations(arr, r) for r in range(len(arr)+1)` genera C(n,r) combinaciones para cada r,
    #           incluyendo r=0 (tupla vacía ()) y r=len(arr) (la tupla completa con todos los elementos).
    return chain.from_iterable(combinations(arr, r) for r in range(len(arr) + 1))


# ─────────────────────────────────────────────────────────────────────────────
# K-PARTICIONES — Extensión para k ∈ {2, 3, 4, 5}
# ─────────────────────────────────────────────────────────────────────────────

def stirling(n: int, k: int) -> int:
    """
    Calcula el número de Stirling del segundo tipo S(n, k).

    S(n, k) cuenta el número de formas de particionar un conjunto de n elementos
    en exactamente k subconjuntos no vacíos (particiones no ordenadas de conjuntos).

    Recurrencia:
        S(n, k) = k · S(n-1, k) + S(n-1, k-1)

    Casos base:
        S(n, 1) = 1        (una sola parte = el conjunto completo)
        S(n, n) = 1        (n partes = n singletons)
        S(n, 0) = 0        para n > 0
        S(0, k) = 0        para k > 0

    Valores de referencia:
        S(4,2)=7,  S(5,3)=25,  S(8,3)=966,  S(10,3)=9330,  S(15,3)≈2.37M

    Args:
        n: Tamaño del conjunto a particionar (n ≥ 0).
        k: Número de partes requeridas (k ≥ 0).

    Returns:
        int: S(n, k).

    Complejidad temporal:  Θ(n · k) — programación dinámica 2D con dos filas.
    Complejidad espacial:  O(k)     — solo se conserva la fila anterior.
    """
    # Lógica: Casos degenerados — si k=0 o k>n no existen k-particiones posibles; S(n,0)=0 y S(n,k)=0 para k>n.
    # Sintaxis: `or` evalúa en cortocircuito: si la primera condición es True, la segunda no se evalúa.
    if k == 0 or k > n:
        return 0

    # Lógica: Casos base de la recurrencia — S(n,1)=1 (todo en una parte) y S(n,n)=1 (cada elemento solo).
    # Sintaxis: `or` encadena dos comparaciones de igualdad; cualquiera que sea True activa el return 1.
    if k == 1 or k == n:
        return 1

    # Lógica: Inicializa la fila "anterior" de la tabla DP con ceros; el índice j representa el número de partes j.
    #         Solo se conservan dos filas (prev y curr) en lugar de la tabla completa para ahorrar O(n·k) → O(k) en espacio.
    # Sintaxis: `[0] * (k + 1)` crea una lista de k+1 ceros — la multiplicación de lista repite el elemento k+1 veces.
    prev = [0] * (k + 1)

    # Lógica: Caso base S(1,1)=1 — un conjunto de un elemento tiene exactamente una forma de particionarse en una parte.
    # Sintaxis: `prev[1] = 1` indexa la lista en la posición 1 (j=1) y le asigna el valor 1.
    prev[1] = 1  # S(1, 1) = 1

    # Lógica: Recorre cada tamaño de conjunto desde i=2 hasta n, extendiendo la tabla DP fila a fila.
    # Sintaxis: `range(2, n + 1)` genera los enteros [2, 3, ..., n]; el +1 incluye n en el rango (range excluye el límite superior).
    for i in range(2, n + 1):
        # Lógica: Crea la fila actual de la tabla (para el conjunto de tamaño i) inicializada en ceros.
        # Sintaxis: `[0] * (k + 1)` construye una lista nueva independiente de prev para no sobreescribir datos aún necesarios.
        curr = [0] * (k + 1)

        # Lógica: Recorre cada número de partes j ∈ {1,...,min(i,k)} — no puede haber más partes que elementos (j≤i) ni más que k.
        # Sintaxis: `min(i, k) + 1` ajusta el límite superior del range; sin +1, min(i,k) quedaría excluido del rango.
        for j in range(1, min(i, k) + 1):
            # Lógica: Aplica la recurrencia S(i,j) = j·S(i-1,j) + S(i-1,j-1).
            #   - j·prev[j]: insertar el i-ésimo elemento en cualquiera de las j partes ya formadas (j opciones).
            #   - prev[j-1]: crear una parte nueva que contenga solo el i-ésimo elemento (partimos de j-1 partes previas).
            # Sintaxis: `j * prev[j] + prev[j - 1]` — multiplicación e indexación de lista; `prev` contiene la fila i-1.
            curr[j] = j * prev[j] + prev[j - 1]

        # Lógica: Descarta la fila anterior y la reemplaza por la actual para continuar con el siguiente i.
        # Sintaxis: Reasignación de variable local — Python marca la lista anterior como elegible para el recolector de basura.
        prev = curr

    # Lógica: Retorna S(n, k): el valor en la posición k de la última fila calculada, que corresponde al tamaño total n.
    # Sintaxis: `prev[k]` indexa la lista resultante en la posición k; en este punto prev almacena la fila i=n de la tabla.
    return prev[k]


def particionar_conjunto(
    elementos: NDArray,
    k: int,
) -> Generator:
    """
    Genera todas las k-particiones de 'elementos' en exactamente k subconjuntos no vacíos.

    Usa el algoritmo de Cadenas de Crecimiento Restringido (RGS — Restricted Growth Strings).

    Definición:
        Una cadena RGS a[0..n-1] satisface:
            a[0] = 0
            a[i] ≤ max(a[0], ..., a[i-1]) + 1   para i > 0

        Cada RGS con max(a) = k-1 corresponde biunívocamente a una k-partición de
        {elementos[0], ..., elementos[n-1]} mediante:
            Parte_j = { elementos[i] : a[i] = j }  para j ∈ {0, ..., k-1}

    Total de particiones generadas: S(n, k)  (número de Stirling del segundo tipo).

    Pseudocódigo RGS:
        _rgs(pos, max_usado):
            si pos == n:
                si max_usado == k-1: emitir partición actual
                retornar
            para v en {0, ..., min(max_usado+1, k-1)}:
                a[pos] ← v
                _rgs(pos+1, max(max_usado, v))

        iniciar con a[0]=0, llamar _rgs(1, 0)

    Args:
        elementos: Array de elementos a particionar.
        k:         Número de partes (k ≥ 1, k ≤ len(elementos)).

    Yields:
        tuple[tuple, ...]: Tupla de k sub-tuplas con los elementos de cada parte.
                           El orden de las partes sigue el primer elemento asignado
                           (el elemento elementos[0] siempre está en la parte 0).

    Complejidad temporal:  Θ(n · S(n, k)) — n trabajo por cada una de S(n,k) particiones.
    Complejidad espacial:  O(n) para el array de asignaciones + O(k) por partición.
    """
    # Lógica: Calcula el número de elementos del array a particionar; n se usará como límite de la recursión RGS.
    # Sintaxis: `len(ndarray)` devuelve la cantidad de elementos en el primer eje del array NumPy.
    n = len(elementos)

    # Lógica: Valida que k esté en el rango [1,n] — si k<1 no hay partición, si k>n no alcanzarían los elementos.
    # Sintaxis: `return` sin valor en una función generadora termina la iteración limpiamente (señal StopIteration al llamador).
    if k < 1 or k > n:
        return

    # Lógica: Caso especial S(n,n)=1 — la única partición es que cada elemento forme su propio singleton, sin necesidad de RGS.
    # Sintaxis: `if k == n:` guarda el caso degenerado antes de construir el array de asignaciones y la clausura recursiva.
    if k == n:
        # Lógica: Emite la única partición posible: k singletons ordenados, uno por cada elemento del array.
        # Sintaxis: `yield tuple(...)` suspende y entrega el valor; `(int(e),)` es tupla de 1 elemento (la coma final es obligatoria).
        yield tuple((int(e),) for e in elementos)
        return

    # Lógica: Array mutable compartido entre todos los niveles de recursión que codifica la asignación actual (RGS).
    #         Usar un array en lugar de lista de Python mejora el acceso por índice y la coherencia de tipos.
    # Sintaxis: `np.zeros(n, dtype=np.int32)` crea un array de n ceros con tipo entero de 32 bits, suficiente para índices de partes.
    asignaciones = np.zeros(n, dtype=np.int32)

    def _rgs(pos: int, max_usado: int) -> Generator:
        # Lógica: Caso base — todos los n elementos ya tienen asignación; verificar si se usaron exactamente k partes.
        # Sintaxis: `if pos == n:` compara el puntero de posición con el límite n (la longitud del array de elementos).
        if pos == n:
            # Lógica: Filtra las asignaciones que no cubren todas las k partes (alguna parte quedaría vacía si max_usado < k-1).
            # Sintaxis: `max_usado == k - 1` verifica que el índice máximo asignado sea exactamente k-1 (partes 0,1,...,k-1).
            if max_usado == k - 1:
                # Lógica: Construye la estructura de salida: k listas vacías que se llenarán con los elementos de cada parte.
                # Sintaxis: `[[] for _ in range(k)]` es list comprehension; `_` es convención para variable de iteración no usada.
                partes: list[list] = [[] for _ in range(k)]

                # Lógica: Distribuye cada elemento del array original a su parte según el número de parte asignado en `asignaciones`.
                # Sintaxis: `enumerate(asignaciones)` produce pares (índice_i, valor_v); i es posición, v es el número de parte.
                for i, v in enumerate(asignaciones):
                    partes[v].append(elementos[i])

                # Lógica: Emite la partición actual como estructura inmutable para garantizar que el llamador no pueda modificarla.
                # Sintaxis: `yield` suspende la función generadora y entrega el valor; `tuple(tuple(p) for p in partes)` convierte listas a tuplas.
                yield tuple(tuple(p) for p in partes)
            return

        # Lógica: Calcula el límite de valores permitidos para la posición actual.
        #   - v ≤ max_usado+1: no se puede crear la parte j+2 sin haber creado la parte j+1 antes (no crear huecos vacíos).
        #   - min con k: no superar el índice de la última parte permitida k-1.
        # Sintaxis: `min(max_usado + 2, k)` — el +2 porque range(limite) excluye el extremo superior, entonces +1 para incluir max_usado+1, +1 más para el range.
        limite = min(max_usado + 2, k)

        # Lógica: Prueba cada valor de asignación posible para la posición actual, explorando el árbol RGS en profundidad.
        # Sintaxis: `range(limite)` genera enteros [0, 1, ..., limite-1]; el límite es exclusivo.
        for v in range(limite):
            # Lógica: Asigna el valor v a la posición pos en el array compartido — modifica el estado global de la clausura in-place.
            # Sintaxis: `asignaciones[pos] = v` es indexación NumPy estándar; modifica el array sin crear uno nuevo.
            asignaciones[pos] = v

            # Lógica: Recurre al siguiente nivel pasando el nuevo máximo; si se encontraron particiones válidas, las emite hacia arriba.
            # Sintaxis: `yield from generador` delega la iteración al sub-generador sin crear un nivel extra de yield en la pila.
            #           `max(max_usado, v)` devuelve el mayor de los dos enteros — actualiza el máximo usado si v es mayor.
            yield from _rgs(pos + 1, max(max_usado, v))

    # Lógica: Inicia la recursión RGS desde pos=1 con asignaciones[0]=0 fijo, lo que rompe la simetría de permutaciones de partes
    #         y garantiza que no se generen duplicados por reordenamiento de las etiquetas de parte.
    # Sintaxis: `yield from` delega al generador recursivo _rgs; al arrancar desde pos=1, asignaciones[0]=0 ya está implícito (np.zeros).
    yield from _rgs(1, 0)


def k_particiones(
    alcances: NDArray[np.int8],
    mecanismos: NDArray[np.int8],
    k: int,
) -> Generator:
    """
    Genera todas las k-particiones del subsistema como listas de k pares (alcance_i, mecanismo_i).

    Recorre el producto cartesiano de:
        Π₁ = todas las k-particiones de 'alcances'   → S(|A|, k) particiones
        Π₂ = todas las k-particiones de 'mecanismos' → S(|M|, k) particiones

    Total de combinaciones generadas: S(|A|, k) × S(|M|, k)

    Correspondencia con biparticiones() para k=2:
        biparticiones() genera todos los pares (A₁⊆A, M₁⊆M) no triviales.
        k_particiones() con k=2 genera exactamente las particiones exactas donde
        A₂ = A ∖ A₁  y  M₂ = M ∖ M₁  (ninguna parte puede ser vacía).

    Nota sobre escalabilidad:
        Para n=10, k=3:  S(10,3)² ≈ 87 millones  → usar estrategia heurística.
        Para n≤5, k≤5:  S(5,5)² = 1, S(5,4)² = 100  → exhaustivo viable.
        Ver KGeometricSIA para la estrategia heurística geométrica.

    Args:
        alcances:   Índices de variables futuras del subsistema (indices_ncubos).
        mecanismos: Índices de variables presentes del subsistema (dims_ncubos).
        k:          Número de partes k ∈ {2, 3, 4, 5}.

    Yields:
        list[tuple[NDArray[np.int8], NDArray[np.int8]]]: Lista de k tuplas
            (alcance_i, mecanismo_i), cada una como ndarray de int8.

    Complejidad temporal:  Θ(S(|A|,k) · S(|M|,k) · (|A|+|M|))
                           donde |A|=|alcances|, |M|=|mecanismos|.
    Complejidad espacial:  O(|A| + |M|) por iteración (generador perezoso).
    """
    # Lógica: Valida que k esté en el rango soportado {2,3,4,5} — valores fuera de este rango son rechazados explícitamente
    #         antes de intentar cualquier cálculo, evitando generaciones vacías o resultados incorrectos silenciosos.
    # Sintaxis: `raise ValueError(f"...")` lanza una excepción con mensaje descriptivo; `{{` y `}}` son llaves literales en f-strings.
    if k < 2 or k > 5:
        raise ValueError(f"k debe estar en {{2,3,4,5}}, se recibió k={k}")

    # Lógica: Itera perezosamente sobre todas las S(|A|,k) k-particiones posibles del array de alcances (variables futuras).
    #         Al ser un generador, cada part_alc solo existe en memoria mientras se itera, sin materializar todo S(|A|,k).
    # Sintaxis: `for part_alc in particionar_conjunto(...)` consume el generador lazy; part_alc es una tupla de k sub-tuplas.
    for part_alc in particionar_conjunto(alcances, k):
        # Lógica: Para cada partición de alcances, itera sobre las S(|M|,k) k-particiones del array de mecanismos (variables presentes).
        #         El doble bucle forma el producto cartesiano Π₁ × Π₂, produciendo S(|A|,k)·S(|M|,k) combinaciones en total.
        # Sintaxis: Bucle anidado — cada iteración del externo desencadena una iteración completa del interno.
        for part_mec in particionar_conjunto(mecanismos, k):
            # Lógica: Emite una k-partición del subsistema como lista de k pares (alcance_i, mecanismo_i) convertidos a ndarray.
            #         Usar `yield` mantiene la generación lazy — la lista solo se construye cuando el llamador la solicita.
            # Sintaxis: `yield [list_comprehension]` emite la lista construida por comprensión directamente desde el generador.
            yield [
                # Lógica: Construye el par i-ésimo convirtiendo las sub-tuplas Python a ndarrays int8 compactos.
                #         int8 (1 byte) es suficiente para índices de nodos (máx. 127) y ahorra memoria frente a int64.
                # Sintaxis: `np.array(tupla, dtype=np.int8)` convierte una tupla Python a ndarray NumPy tipado.
                (
                    np.array(part_alc[i], dtype=np.int8),   # alcance_i: variables futuras de la parte i
                    np.array(part_mec[i], dtype=np.int8),   # mecanismo_i: variables presentes de la parte i
                )
                # Lógica: Genera los k pares de (alcance_i, mecanismo_i) indexando ambas particiones por el mismo i.
                # Sintaxis: `for i in range(k)` itera los índices 0,1,...,k-1 — uno por cada parte de la k-partición.
                for i in range(k)
            ]
