from itertools import product
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from pyemd import emd

from src.models.enums.distance import MetricDistance
from src.models.enums.notation import Notation

from src.models.base.application import aplicacion
from src.constants.base import ABC_START, INT_ZERO


# @cache (comentado)
def get_labels(n: int) -> tuple[str, ...]:
    # Lógica: Genera etiquetas de nodo estilo Excel (A, B, ..., Z, AA, AB...) para cualquier
    #         n, permitiendo identificar más de 26 nodos sin repetir letras.
    # Sintaxis: Función anidada — tiene acceso al scope de get_labels; se define dentro
    #           para encapsular la recursión sin exponerla al módulo.
    def get_excel_column(n: int) -> str:
        # Lógica: Caso base de la recursión — n=0 retorna string vacío, terminando la cadena.
        # Sintaxis: `if n <= 0: return ""` es la condición de parada de la recursión;
        #           sin esto la función recursaría infinitamente.
        if n <= 0:
            return ""
        # Lógica: Calcula la letra actual del nivel más a la derecha usando módulo 26,
        #         y la concatena recursivamente con los niveles superiores.
        # Sintaxis: `(n-1) // 26` calcula el cociente para los niveles anteriores;
        #           `(n-1) % 26 + ord('A')` da el valor ASCII de la letra actual;
        #           `chr(...)` convierte el código ASCII al carácter correspondiente.
        return get_excel_column((n - 1) // 26) + chr((n - 1) % 26 + ord(ABC_START))

    # Lógica: Genera la tupla de etiquetas para los índices 1..n aplicando get_excel_column
    #         a cada posición; índice 1→'A', 26→'Z', 27→'AA', etc.
    # Sintaxis: List comprehension `[get_excel_column(i) for i in range(1, n + 1)]`
    #           itera 1..n; `tuple(...)` convierte la lista a tupla inmutable.
    return tuple([get_excel_column(i) for i in range(1, n + 1)])


# Lógica: Genera el abecedario extendido hasta 40 letras para soportar redes de hasta 40 nodos;
#         40 > 26 por eso se usa la notación estilo Excel (AA, AB...) a partir del nodo 27.
# Sintaxis: `get_labels(40)` retorna una tupla de 40 strings; se asigna como constante de módulo
#           para que todos los módulos que importen ABECEDARY usen el mismo objeto.
ABECEDARY = get_labels(40)
# Lógica: Versión en minúsculas del abecedario para identificar nodos en tiempo presente (t)
#         en contraste con las mayúsculas que identifican nodos en tiempo futuro (t+1).
# Sintaxis: List comprehension `[letter.lower() for letter in ABECEDARY]` convierte cada
#           elemento; `str.lower()` es O(n) en la longitud del string.
LOWER_ABECEDARY = [letter.lower() for letter in ABECEDARY]


def literales(remaining_vars: NDArray[np.int8], lower: bool = False):
    # Lógica: Convierte un array de índices de nodos a su representación literal concatenada
    #         (ej: [0,1,2] → "ABC") para mostrar particiones en logs y resultados.
    # Sintaxis: Operador ternario: si el array no está vacío (`remaining_vars.size` > 0),
    #           hace join de las etiquetas; si está vacío retorna el símbolo ∅.
    return (
        # Lógica: Mapea cada índice al abecedario en minúsculas o mayúsculas según `lower`,
        #         y une sin separador para formar la representación literal.
        # Sintaxis: Generator expression sobre `remaining_vars`; `ABECEDARY[i].lower()`
        #           convierte a minúscula; `"".join(...)` concatena sin separador.
        "".join(ABECEDARY[i].lower() if lower else ABECEDARY[i] for i in remaining_vars)
        if remaining_vars.size
        # Lógica: Array vacío indica conjunto vacío — se representa con el símbolo matemático ∅.
        # Sintaxis: `else "∅"` es la rama falsy del operador ternario.
        else "∅"
    )


def seleccionar_metrica(distancia_usada: str):
    # Lógica: Selecciona la función de cálculo de EMD apropiada según la métrica configurada,
    #         retornando una Callable reutilizable para evitar el dispatch en cada iteración.
    # Sintaxis: Dict que mapea el `.value` de cada enum MetricDistance a su función;
    #           `distancias_metricas[key]` retorna la función sin llamarla.
    distancias_metricas = {
        # Lógica: EMD_EFECTO usa la solución analítica Σ|u-v| — más rápida que la EMD general.
        # Sintaxis: `.value` extrae el string del enum para usarlo como clave del dict.
        MetricDistance.EMD_EFECTO.value: emd_efecto,
        # Lógica: EMD_CAUSA usa la EMD con distancia Hamming como ground metric — más costosa.
        # Sintaxis: Mismo patrón de clave-valor; `emd_causal` es la función del módulo.
        MetricDistance.EMD_CAUSA.value: emd_causal,
        # ...otras
    }
    # Lógica: Retorna la función de métrica que corresponde al string de distancia configurado
    #         en la aplicación, para que el llamador la use directamente como Callable.
    # Sintaxis: `distancias_metricas[distancia_usada]` indexa el dict; lanza KeyError si
    #           la distancia no está en el mapa.
    return distancias_metricas[distancia_usada]


def emd_efecto(u: NDArray[np.float32], v: NDArray[np.float32]) -> float:
    """
    Solución analítica de la Earth Mover's Distance basada en variables independientes condicionalmente.
    Sean X_1, X_2 dos variables aleatorias con su correspondiente espacio de estados. Si X_1 y X_2 son independientes y u_1, v_1 dos distribuciones de probabilidad en X_1 y u_2, v_2 dos distribuciones de probabilidad en X_2.

    Args:
        u (NDArray[np.float32]): Histograma/distribución/vector/serie donde cada indice asocia un valor de pobabilidad de tener el nodo en estado OFF.
        v (NDArray[np.float32]): Histograma/distribución/vector/serie donde cada indice asocia un valor de pobabilidad de tener el nodo en estado OFF.

    Returns:
        float: La EMD entre los repertorios efecto es igual a la suma entre las EMD de las distribuciones marginales de cada nodo, de forma que la EMD entre las distribuciones marginales para un nodo es la diferencia absoluta entre las probabilidades con el nodo OFF.
    """
    # Lógica: Calcula la EMD entre dos distribuciones marginales como la suma de diferencias
    #         absolutas elemento a elemento — solución exacta cuando las variables son independientes.
    # Sintaxis: `np.abs(u - v)` calcula |u_i - v_i| para cada par; `np.sum(...)` suma todos
    #           los valores; `float(...)` convierte np.float32 a float nativo de Python.
    return float(np.sum(np.abs(u - v)))


def emd_causal(u: NDArray[np.float64], v: NDArray[np.float64]) -> float:
    """
    Calculate the Earth Mover's Distance (EMD) between two probability distributions u and v.
    The Hamming distance was used as the ground metric.
    """
    # Lógica: Valida que ambas entradas sean arrays NumPy; la función `emd` de pyemd
    #         requiere arrays y lanza TypeError con tipos incompatibles.
    # Sintaxis: `all(isinstance(arr, np.ndarray) for arr in [u, v])` aplica isinstance
    #           a cada elemento de la lista; `all(...)` retorna True solo si todos son True.
    if not all(isinstance(arr, np.ndarray) for arr in [u, v]):
        raise TypeError("u and v must be numpy arrays.")

    # Lógica: El tamaño de la distribución determina la dimensión de la matriz de costos;
    #         para la EMD se necesita una matriz n×n de distancias entre estados.
    # Sintaxis: `u.size` retorna el número total de elementos del array en O(1).
    n: int = u.size
    # Lógica: Crea una matriz de costos n×n vacía (sin inicializar) para mayor velocidad;
    #         se llenará con distancias de Hamming entre cada par de estados.
    # Sintaxis: `np.empty((n, n))` reserva memoria sin inicializar — más rápido que `np.zeros`
    #           cuando se va a rellenar completamente después.
    costs: NDArray[np.float64] = np.empty((n, n))

    for i in range(n):
        # Lógica: Calcula las distancias de Hamming entre el estado i y todos los estados j < i,
        #         aprovechando la simetría para llenar solo la mitad inferior de la matriz.
        # Sintaxis: List comprehension `[hamming_distance(i, j) for j in range(i)]` calcula
        #           la distancia para los j anteriores; `costs[i, :i]` asigna la fila parcial.
        costs[i, :i] = [hamming_distance(i, j) for j in range(i)]
        # Lógica: Copia la fila i en la columna i usando la simetría d(i,j) = d(j,i),
        #         evitando calcular la distancia dos veces.
        # Sintaxis: `costs[:i, i] = costs[i, :i]` es una asignación de slice transpuesta;
        #           refleja los valores de la fila en la columna.
        costs[:i, i] = costs[i, :i]  # Reflejar los valores

    # Lógica: Llena la diagonal con ceros ya que la distancia de un estado a sí mismo es 0;
    #         `np.empty` no garantiza ceros en la diagonal.
    # Sintaxis: `np.fill_diagonal(arr, val)` modifica in-place la diagonal principal
    #           del array 2D con el valor dado.
    np.fill_diagonal(costs, INT_ZERO)

    # Lógica: Convierte la matriz de costos a float64 explícitamente ya que pyemd requiere
    #         ese tipo para el cálculo de la EMD general con ground metric.
    # Sintaxis: `np.array(costs, dtype=np.float64)` crea una copia con el dtype forzado;
    #           necesario porque `np.empty` puede usar float64 pero se garantiza explícitamente.
    cost_mat: NDArray[np.float64] = np.array(costs, dtype=np.float64)
    # Lógica: Calcula la EMD usando la librería pyemd con la matriz de distancias Hamming
    #         como ground metric — más costoso que emd_efecto pero exacto para EMD causal.
    # Sintaxis: `emd(u, v, cost_mat)` de pyemd implementa el algoritmo de transporte óptimo;
    #           retorna el costo mínimo de "mover" la distribución u hacia v.
    return emd(u, v, cost_mat)


def hamming_distance(a: int, b: int) -> int:
    # Lógica: Calcula la distancia de Hamming entre dos enteros como el número de bits
    #         que difieren en su representación binaria.
    # Sintaxis: `a ^ b` aplica XOR bit a bit — los bits 1 del resultado son los que difieren;
    #           `.bit_count()` cuenta cuántos bits son 1 (Python 3.10+, equivalente a bin(x).count('1')).
    return (a ^ b).bit_count()


def reindexar(N: int):
    # Lógica: Retorna el esquema de indexación (orden de estados) según la notación del
    #         sistema — big-endian mantiene el orden natural, little-endian lo invierte.
    # Sintaxis: Dict que mapea el `.value` de cada enum Notation al índice correspondiente;
    #           `notaciones[aplicacion.notacion]` selecciona el índice activo en la app.
    notaciones = {
        # Lógica: BIG_ENDIAN mantiene el orden original de los estados (0, 1, 2...).
        # Sintaxis: `range(N)` genera un Range object con los índices en orden natural.
        Notation.BIG_ENDIAN.value: range(N),
        # Lógica: LIL_ENDIAN invierte el orden de los bits en cada estado para cambiar
        #         la notación de indexación de la TPM.
        # Sintaxis: `lil_endian(N)` retorna un ndarray con los índices en orden little-endian.
        Notation.LIL_ENDIAN.value: lil_endian(N),
        # ...otras
    }
    # Lógica: Retorna el esquema de indexación seleccionado por la configuración global
    #         de la aplicación para reordenar la TPM según la notación del sistema.
    # Sintaxis: `notaciones[aplicacion.notacion]` indexa el dict con el string de notación
    #           activa; lanza KeyError si la notación no está registrada.
    return notaciones[aplicacion.notacion]


def seleccionar_subestado(subestado):
    # Lógica: Reordena o mantiene el subestado según la notación del sistema; en little-endian
    #         los bits menos significativos van primero, por lo que se invierte el vector.
    # Sintaxis: Dict que mapea cada notación a su transformación; las llaves son los `.value`
    #           del enum Notation.
    notaciones = {
        # Lógica: BIG_ENDIAN mantiene el subestado en su orden original sin transformación.
        # Sintaxis: `subestado` sin modificar — la clave apunta al objeto original.
        Notation.BIG_ENDIAN.value: subestado,
        # Lógica: LIL_ENDIAN invierte el subestado porque en little-endian el bit menos
        #         significativo está primero y hay que revertirlo para indexar el n-cubo.
        # Sintaxis: `subestado[::-1]` es slicing con paso -1 — invierte cualquier secuencia
        #           (string, list, tuple, ndarray) sin crear una copia profunda.
        Notation.LIL_ENDIAN.value: subestado[::-1],
        # ...otras
    }
    # Lógica: Retorna el subestado transformado según la notación activa de la aplicación.
    # Sintaxis: `notaciones[aplicacion.notacion]` indexa el dict con el string de notación.
    return notaciones[aplicacion.notacion]


def lil_endian(n: int) -> np.ndarray:
    """
    Implementación final optimizada para generación de little endian.
    Combina las mejores prácticas encontradas en nuestras pruebas.
    """
    # Lógica: Caso borde para n=0 — retorna array con un solo elemento 0 en lugar de
    #         un array vacío, para que el resultado sea siempre indexable.
    # Sintaxis: `return np.array([0], dtype=np.uint32)` crea array de un elemento de 32 bits sin signo.
    if n <= 0:
        return np.array([0], dtype=np.uint32)

    # Lógica: Calcula el número total de estados (2^n) como desplazamiento de bits,
    #         luego reserva el array de resultados en uint32 para soportar hasta 2^32 estados.
    # Sintaxis: `1 << n` es equivalente a 2^n pero más eficiente; `np.zeros(size, dtype=np.uint32)`
    #           inicializa en ceros de 4 bytes por elemento.
    size = 1 << n
    result = np.zeros(size, dtype=np.uint32)

    # Lógica: Elige el tamaño de bloque óptimo basado en n para equilibrar uso de caché L1/L2
    #         vs overhead de bucles; bloques más grandes para n pequeños, más pequeños para n grandes.
    # Sintaxis: `max(12, min(16, 28 - int(np.log2(n))))` acota el valor entre 12 y 16;
    #           `1 << block_bits` convierte bits a tamaño de bloque.
    block_bits = max(12, min(16, 28 - int(np.log2(n))))
    block_size = 1 << block_bits

    # Lógica: Precomputa los desplazamientos para invertir el orden de bits — el bit i
    #         del estado original pasa a la posición (n-i-1) en la representación little-endian.
    # Sintaxis: List comprehension `[n - i - 1 for i in range(n)]` genera los shifts;
    #           `np.array(..., dtype=np.uint32)` los convierte a array para operaciones vectorizadas.
    shifts = np.array([n - i - 1 for i in range(n)], dtype=np.uint32)

    # Lógica: Pre-aloca el buffer de bloque para evitar crear arrays nuevos en cada iteración,
    #         reutilizando memoria y reduciendo la presión sobre el garbage collector.
    # Sintaxis: `np.zeros(block_size, dtype=np.uint32)` crea el buffer reutilizable;
    #           se limpia explícitamente al inicio de cada iteración de bloque.
    block_result = np.zeros(block_size, dtype=np.uint32)

    # Lógica: Determina el tamaño de grupo de bits a procesar simultáneamente; grupos de 6
    #         para n>24 (redes grandes) y de 4 para n≤24, basado en pruebas empíricas de rendimiento.
    # Sintaxis: Operador ternario `A if cond else B`; `bit_group_size` es un entero.
    bit_group_size = 6 if n > 24 else 4

    # Lógica: Itera sobre el array de resultados en bloques para aprovechar la localidad
    #         de caché y reducir accesos a memoria no contiguos.
    # Sintaxis: `range(0, size, block_size)` genera los índices de inicio de cada bloque
    #           (0, block_size, 2*block_size...); el paso es el tamaño del bloque.
    for start in range(0, size, block_size):
        # Lógica: Calcula el fin del bloque actual, acotado al tamaño total para el último bloque
        #         que puede ser más pequeño que block_size.
        # Sintaxis: `min(start + block_size, size)` garantiza que no se acceda fuera del array.
        end = min(start + block_size, size)
        current_size = end - start

        # Lógica: Limpia el buffer reutilizable en el slice del tamaño del bloque actual
        #         para no contaminar el bloque con valores de la iteración anterior.
        # Sintaxis: `block_result[:current_size] = 0` asigna 0 a los primeros `current_size`
        #           elementos del buffer sin crear un nuevo array.
        block_result[:current_size] = 0
        # Lógica: Genera los índices del bloque actual como array para procesamiento
        #         vectorizado — evita el bucle Python explícito sobre cada estado.
        # Sintaxis: `np.arange(start, end, dtype=np.uint32)` crea el rango como array de uint32.
        block_indices = np.arange(start, end, dtype=np.uint32)

        # Lógica: Procesa los bits en grupos para reducir el número de iteraciones del bucle
        #         interno, aplicando operaciones vectorizadas sobre grupos de bits a la vez.
        # Sintaxis: `range(0, n, bit_group_size)` genera índices 0, group_size, 2*group_size...
        for base_bit in range(0, n, bit_group_size):
            # Lógica: Calcula cuántos bits quedan en este grupo — el último grupo puede ser
            #         más pequeño que bit_group_size.
            # Sintaxis: `min(bit_group_size, n - base_bit)` acota al tamaño disponible.
            bits_remaining = min(bit_group_size, n - base_bit)
            if bits_remaining <= 0:
                break

            # Lógica: Crea una máscara de bits para aislar el grupo actual de bits de cada
            #         estado — `(1 << bits_remaining) - 1` genera una secuencia de 1s del ancho dado.
            # Sintaxis: `np.uint32(...)` fuerza el tipo para operaciones bit a bit vectorizadas;
            #           `(1 << k) - 1` genera k bits en 1 (ej: k=3 → 0b111 = 7).
            group_mask = np.uint32((1 << bits_remaining) - 1)
            # Lógica: Extrae el grupo de bits de cada estado desplazando a la derecha (>>) para
            #         posicionar los bits de interés en las posiciones más bajas, luego aplica la máscara.
            # Sintaxis: `(block_indices >> base_bit)` desplaza todos los índices a la derecha;
            #           `& group_mask` aplica AND bit a bit para aislar solo los bits del grupo.
            group_values = (block_indices >> base_bit) & group_mask

            for j in range(bits_remaining):
                # Lógica: Usa el shift precomputado para colocar el bit j del grupo original
                #         en su posición invertida en la representación little-endian.
                # Sintaxis: `shifts[base_bit + j]` indexa el array de shifts precomputados;
                #           es O(1) en NumPy.
                shift = shifts[base_bit + j]
                # Lógica: Extrae el bit j del grupo de valores y lo coloca en la posición
                #         `shift` del resultado acumulando con OR.
                # Sintaxis: `(group_values >> j) & np.uint32(1)` aisla el bit j;
                #           `|= bit_value << shift` acumula en el buffer con OR bit a bit.
                bit_value = (group_values >> j) & np.uint32(1)
                block_result[:current_size] |= bit_value << shift

        # Lógica: Copia el resultado del bloque actual al array general en la posición correcta
        #         para construir el resultado final completo.
        # Sintaxis: `result[start:end] = block_result[:current_size]` es asignación de slice;
        #           copia los `current_size` elementos del buffer al rango [start, end) del resultado.
        result[start:end] = block_result[:current_size]

    # Lógica: Retorna el array completo con la permutación de índices en orden little-endian
    #         para reordenar los estados de la TPM.
    # Sintaxis: `return result` retorna el ndarray de uint32 construido iterativamente.
    return result


def get_restricted_combinations(binary_str: str) -> tuple[list[str], list[str]]:
    """
    Genera las combinaciones para B y C basadas en la cadena binaria A.
    B solo puede tener 1s donde A tiene 1s.
    """
    # Lógica: Cuenta los bits activos en la cadena para determinar cuántas posiciones
    #         libres tiene B para variar (solo puede poner 1s donde A tiene 1s).
    # Sintaxis: `str.count("1")` cuenta las ocurrencias del carácter "1" en el string.
    ones_count = binary_str.count("1")
    # Lógica: La longitud de la cadena determina el ancho de cada combinación generada,
    #         para que todas las combinaciones tengan el mismo número de bits.
    # Sintaxis: `len(string)` retorna el número de caracteres del string.
    width = len(binary_str)

    # Lógica: Precomputa las posiciones de los 1s en A para saber dónde pueden ir los 1s de B
    #         sin iterar sobre toda la cadena en cada combinación.
    # Sintaxis: List comprehension con `enumerate` — `i` es el índice, `bit` es el carácter;
    #           `if bit == "1"` filtra solo las posiciones con valor activo.
    one_positions = [i for i, bit in enumerate(binary_str) if bit == "1"]

    def generate_valid_combinations():
        # Lógica: Genera el producto cartesiano de {0,1} tomado `ones_count` veces para
        #         obtener todas las asignaciones posibles de bits en las posiciones activas de A.
        # Sintaxis: `product(["0", "1"], repeat=k)` es itertools.product; genera todas las
        #           k-tuplas de {0,1}; `list(...)` materializa el generador.
        base_combinations = list(product(["0", "1"], repeat=ones_count))
        valid_combinations = []

        for comb in base_combinations:
            # Lógica: Inicia cada combinación con todos ceros y luego coloca los bits de
            #         `comb` en las posiciones donde A tiene 1s.
            # Sintaxis: `["0"] * width` crea una lista de `width` strings "0";
            #           el operador `*` sobre listas repite el elemento.
            result = ["0"] * width
            # Lógica: Asigna cada bit de la combinación a su posición correspondiente en
            #         la cadena resultado, usando las posiciones precomputadas de los 1s de A.
            # Sintaxis: `zip(one_positions, comb)` itera pares (posición, bit) en paralelo;
            #           `result[pos] = bit` asigna el carácter en la posición correcta.
            for pos, bit in zip(one_positions, comb):
                result[pos] = bit
            # Lógica: Une la lista de caracteres en un string y la añade a las combinaciones
            #         válidas para retornar al llamador.
            # Sintaxis: `"".join(result)` concatena sin separador; `list.append` añade al final.
            valid_combinations.append("".join(result))

        return valid_combinations

    # Lógica: B y C son las mismas combinaciones válidas — ambas tienen la misma restricción
    #         de solo poner 1s donde A tiene 1s.
    # Sintaxis: `generate_valid_combinations()` invoca la función anidada; `B.copy()` crea
    #           una copia superficial (shallow copy) de la lista para que B y C sean independientes.
    B = generate_valid_combinations()
    C = (
        B.copy()
    )  # En este caso C es igual a B, pero podría ser diferente si se necesita más tarde

    # Lógica: Retorna la tupla (B, C) para que el llamador la desempaquete con `B, C = ...`.
    # Sintaxis: `return B, C` retorna una tupla de dos listas sin paréntesis explícitos —
    #           Python empaqueta automáticamente los valores separados por coma.
    return B, C


def generate_combinations(A: str) -> list[tuple[str, str, str]]:
    """
    Genera el producto cartesiano final de A con las combinaciones válidas de B y C.
    """
    # Lógica: Obtiene las combinaciones válidas de B y C basadas en las posiciones activas
    #         de A para generar el producto cartesiano completo A×B×C.
    # Sintaxis: Desempaquetado de tupla retornada por get_restricted_combinations.
    B, C = get_restricted_combinations(A)
    # Lógica: Formatea cada combinación de B, C y A en grupos de 2 bits separados por
    #         espacio para la representación visual de estados del sistema.
    # Sintaxis: Outer list comprehension itera sobre `b` en B; inner `"".join(...)` con
    #           generator sobre `range(0, len(b), 2)` agrupa de a 2 con `b[i:i+2]`.
    formatted_B = ["".join(b[i : i + 2] for i in range(0, len(b), 2)) for b in B]
    formatted_C = ["".join(c[i : i + 2] for i in range(0, len(c), 2)) for c in C]
    # Lógica: Formatea A con el mismo esquema de grupos de 2 bits para consistencia
    #         en la representación junto a las combinaciones de B y C.
    # Sintaxis: `"".join(A[i:i+2] for i in range(0, len(A), 2))` agrupa A de a 2 bits.
    formatted_A = "".join(A[i : i + 2] for i in range(0, len(A), 2))

    # Lógica: Genera el producto cartesiano {A}×B×C, excluyendo el primer elemento que
    #         corresponde a la combinación trivial (B=todos 0, C=todos 0).
    # Sintaxis: `product([A], formatted_B, formatted_C)` genera todas las tripletas;
    #           `list(...)[1:]` materializa y descarta el primer elemento (índice 0).
    return list(product([formatted_A], formatted_B, formatted_C))[1:]


def dec2bin(decimal: int, width: int) -> str:
    # Lógica: Convierte un entero decimal a su representación binaria con ancho fijo,
    #         rellenando con ceros a la izquierda si es necesario.
    # Sintaxis: `format(decimal, f"0{width}b")` aplica el format spec `0{width}b`:
    #           `0` = rellenar con ceros, `{width}` = ancho mínimo, `b` = binario.
    return format(decimal, f"0{width}b")


def estados_binarios(n: int):
    # Lógica: Genera todas las representaciones binarias de los estados no nulos (1..2^n-1)
    #         para un sistema de n bits, omitiendo el estado 0 (todos apagados).
    # Sintaxis: List comprehension sobre `range(1 << n)` (= range(0, 2^n));
    #           `[1:]` descarta el primer elemento (dec2bin(0, n) = "000...0").
    return [dec2bin(i, n) for i in range(1 << n)][1:]


# Ejemplos / Notas antiguas
# def estados_binarios(n: int, veces=3):
#     # Números de 0 a 2^N #
#     rango = [dec2bin(i, n) for i in range(2**n)]
#     return product(rango, repeat=veces)
