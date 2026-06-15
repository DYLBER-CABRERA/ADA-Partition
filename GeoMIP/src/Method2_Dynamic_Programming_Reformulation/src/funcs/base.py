from itertools import product  # Importa la función 'product' para calcular el producto cartesiano de iterables
import logging  # Importa el módulo 'logging' para registrar mensajes (logs) del sistema
from datetime import datetime  # Importa la clase 'datetime' para trabajar con fechas y horas
from pathlib import Path  # Importa la clase 'Path' para manipular rutas del sistema de archivos de forma orientada a objetos

import numpy as np  # Importa la librería 'numpy' con el alias 'np' para computación numérica
from numpy.typing import NDArray  # Importa 'NDArray' para anotaciones de tipos de arreglos (arrays) en numpy
from pyemd import emd  # Importa la función 'emd' (Earth Mover's Distance) del paquete 'pyemd'

from src.models.enums.distance import MetricDistance  # Importa la enumeración 'MetricDistance' de nuestras carpetas de modelos
from src.models.enums.notation import Notation  # Importa la enumeración 'Notation' para representar los tipos de notación (Ej: Endianness)

from src.models.base.application import aplicacion  # Importa el objeto o clase 'aplicacion' con la configuración de la app
from src.constants.base import ABC_START, INT_ZERO  # Importa constantes globales como el inicio del abecedario y el cero entero


# @cache (comentado)
def get_labels(n: int) -> tuple[str, ...]:
    # Define la función 'get_labels' que recibe un entero 'n' y retorna una tupla de cadenas (strings).
    def get_excel_column(n: int) -> str:
        # Define una función anidada para convertir un número 'n' en una letra de columna estilo Excel (A, B, ..., Z, AA, AB...).
        if n <= 0:
            # Caso base de la recursión: si 'n' es 0 o negativo, retorna una cadena vacía.
            return ""
        # Llamada recursiva: calcula el cociente (n-1)//26 para las letras previas, y añade la letra actual con chr((n-1)%26 + ord('A'))
        return get_excel_column((n - 1) // 26) + chr((n - 1) % 26 + ord(ABC_START))

    # Crea un generador list comprehension que obtiene la etiqueta para cada 'i' desde 1 hasta 'n'
    # y lo convierte en una tupla usando tuple(). Retorna dicha tupla.
    return tuple([get_excel_column(i) for i in range(1, n + 1)])


# Llama a la función 'get_labels' para obtener las letras hasta el 40, guardándolas en 'ABECEDARY'
ABECEDARY = get_labels(40)
# Usa list comprehension para crear una lista en minúsculas de las etiquetas generadas en 'ABECEDARY'
LOWER_ABECEDARY = [letter.lower() for letter in ABECEDARY]


def literales(remaining_vars: NDArray[np.int8], lower: bool = False):
    # Define la función que recibe un arreglo de numpy de tipo int8 representando índices y un flag 'lower'.
    return (
        # Si 'remaining_vars' tiene elementos (evalúa a True), hace un "".join() iterando cada índice 'i' en remaining_vars.
        # Usa minúsculas si 'lower' es True, sino mayúsculas.
        "".join(ABECEDARY[i].lower() if lower else ABECEDARY[i] for i in remaining_vars)
        if remaining_vars.size
        # Si el arreglo está vacío, retorna el string "∅" (conjunto vacío).
        else "∅"
    )


def seleccionar_metrica(distancia_usada: str):
    # Define la función para seleccionar la métrica de distancia según un string 'distancia_usada'.
    distancias_metricas = {
        # Diccionario que mapea el valor de la enumeración EMD_EFECTO con la función 'emd_efecto'
        MetricDistance.EMD_EFECTO.value: emd_efecto,
        # Dict mapping de EMD_CAUSA con la función 'emd_causal'
        MetricDistance.EMD_CAUSA.value: emd_causal,
        # ...otras
    }
    # Retorna la función que corresponde a la 'distancia_usada' pasandolo como llave al diccionario
    return distancias_metricas[distancia_usada]


def emd_efecto(u: NDArray[np.float32], v: NDArray[np.float32]) -> float:
    # Define la función 'emd_efecto' que recibe dos arreglos numpy tipo float32 de distribuciones 'u' y 'v' y retorna float
    """
    Solución analítica de la Earth Mover's Distance basada en variables independientes condicionalmente.
    Sean X_1, X_2 dos variables aleatorias con su correspondiente espacio de estados. Si X_1 y X_2 son independientes y u_1, v_1 dos distribuciones de probabilidad en X_1 y u_2, v_2 dos distribuciones de probabilidad en X_2.

    Args:
        u (NDArray[np.float32]): Histograma/distribución/vector/serie donde cada indice asocia un valor de pobabilidad de tener el nodo en estado OFF.
        v (NDArray[np.float32]): Histograma/distribución/vector/serie donde cada indice asocia un valor de pobabilidad de tener el nodo en estado OFF.

    Returns:
        float: La EMD entre los repertorios efecto es igual a la suma entre las EMD de las distribuciones marginales de cada nodo, de forma que la EMD entre las distribuciones marginales para un nodo es la diferencia absoluta entre las probabilidades con el nodo OFF.
    """
    # Calcula la diferencia entre arrays (u - v), le aplica valor absoluto con np.abs, 
    # y suma todos los valores resultantes con np.sum, retornando el total (distancia analítica)
    return float(np.sum(np.abs(u - v))) # Sintaxis: np.sum devuelve tipo np.number, con float() parseamos a float built-in (opcional pero usual)


def emd_causal(u: NDArray[np.float64], v: NDArray[np.float64]) -> float:
    # Función 'emd_causal' que recibe 2 distribuciones en arrays tipo float64, y retorna un float.
    """
    Calculate the Earth Mover's Distance (EMD) between two probability distributions u and v.
    The Hamming distance was used as the ground metric.
    """
    # Verifica que ambos parametros u y v sean instancias de arreglos de numpy 'np.ndarray' usando all() sobre una list-comprehension
    if not all(isinstance(arr, np.ndarray) for arr in [u, v]):
        # Lanza TypeError si alguno no lo es
        raise TypeError("u and v must be numpy arrays.")

    n: int = u.size  # Obtiene el tamaño (cantidad de elementos) del array 'u', declarando el tipo int
    costs: NDArray[np.float64] = np.empty((n, n))  # Crea una matriz vacía NumPy de tamaño n x n tipo float64

    # Itera sobre el rango [0, n - 1]
    for i in range(n):
        # Utiliza comprensión de listas para calcular los costos:
        # Asigna la distancia de hamming entre 'i' y cada 'j' anterior a 'i'. Se usa slicing costs[i, :i] para asignar la fila hasta i.
        costs[i, :i] = [hamming_distance(i, j) for j in range(i)]
        # Debido a que la distancia Hamming es simétrica, aplica la reflexión copiando de la fila a la columna iterada: costs[:i, i]
        costs[:i, i] = costs[i, :i]  # Reflejar los valores

    # Llena la diagonal de la matriz con INT_ZERO (0) usando la función implícita de numpy np.fill_diagonal
    np.fill_diagonal(costs, INT_ZERO)

    # Convierte la matriz modificada nuevamente en un arreglo forzando su tipo fuertemente con np.array y dtype
    cost_mat: NDArray[np.float64] = np.array(costs, dtype=np.float64)
    # Retorna la EMD calculada mediante la librería externa pasándole los dos arrays y la matriz de pesos/distancias
    return emd(u, v, cost_mat)


def hamming_distance(a: int, b: int) -> int:
    # Devuelve la distancia de hamming (cantidad de bits diferentes): 
    # 'a ^ b' aplica el operador matemático XOR bit a bit, luego '.bit_count()' cuenta cuantos bits son '1' en su notación en memoria.
    return (a ^ b).bit_count()


def reindexar(N: int):
    # Función que recibe N entero para recuperar un esquema de repetición o notación
    notaciones = {
        # Evalúa BIG_ENDIAN y le asigna el rango normal built-in de python (Range object generado por range(N))
        Notation.BIG_ENDIAN.value: range(N),
        # Evalúa LIL_ENDIAN y le asgina la función lil_endian enviando N, que retorna el array invertido
        Notation.LIL_ENDIAN.value: lil_endian(N),
        # ...otras
    }
    # Retorna de base en la propiedad 'aplicacion.notacion' guardada a nivel de sistema que hace match con las keys del Dict
    return notaciones[aplicacion.notacion]


def seleccionar_subestado(subestado):
    # Función que se encarga de reordenar o mantener el arreglo de subestado
    # posible in-deducción por acceso inverso
    notaciones = {
        # BIG_ENDIAN: Mantiene el array original sin modificaciones
        Notation.BIG_ENDIAN.value: subestado,
        # LIL_ENDIAN: Revierte el string / vector / list original con sintaxis de slicing str[::-1] indicando step -1
        Notation.LIL_ENDIAN.value: subestado[::-1],
        # ...otras
    }
    return notaciones[aplicacion.notacion]  # Devuelve de nuevo segun la notación que está en aplicación


def lil_endian(n: int) -> np.ndarray:
    # Función optimizada para retornar un Numpy Array (anotación np.ndarray) conteniendo notación little endian 
    """
    Implementación final optimizada para generación de little endian.
    Combina las mejores prácticas encontradas en nuestras pruebas.
    """
    if n <= 0:
        # Caso base/borde. Retorna un array con el valor '0' tipo entero sin signo de 32 bits (uint32)
        return np.array([0], dtype=np.uint32)  # Caso especial para n=0

    # Desplazamiento bit a bit: 1 << n es equivalente a 2 elevado a la potencia n (ej 1 << 3 = 8)
    size = 1 << n
    # Crea un arreglo numpy de ceros con tamaño igual a 2^n usando tipo uint32
    result = np.zeros(size, dtype=np.uint32)

    # Optimización de parámetros basada en n: 
    # min() y max() acotan el valor de '28 - logaritmo 2 de (n)' a un máximo 16 o mínimo 12
    block_bits = max(12, min(16, 28 - int(np.log2(n))))
    # block_size es el resultante pow de 2 basado en el shift
    block_size = 1 << block_bits

    # Precomputar shifts de una vez (arreglo con posiciones invertidas int)
    shifts = np.array([n - i - 1 for i in range(n)], dtype=np.uint32)

    # Pre-alocar buffer para procesamientos individuales temporales por bloque (array de ceros)
    block_result = np.zeros(block_size, dtype=np.uint32)

    # Determinar tamaño óptimo de grupo de bits. Si n>24 -> 6, caso contrario -> 4
    bit_group_size = 6 if n > 24 else 4  # Ajuste basado en pruebas empíricas

    # Itera de forma separada por bloques 'block_size' usando sintaxis range(start, stop, step)
    for start in range(0, size, block_size):
        # Determina final del loop acotándolo contra el tamañó total 'size' si pasamos del borde
        end = min(start + block_size, size)
        # Calcula longitud real con final - inicio
        current_size = end - start

        # Limpieza (reset) eficiente del buffer mediante inserción [slice]
        block_result[:current_size] = 0
        # Obtiene un vector secuencial desde 'start' hasta 'end' conteniendo los indices correspondientes, para procesamiento paralelo
        block_indices = np.arange(start, end, dtype=np.uint32)

        # Procesar bits en grupos optimizados, loop usando step 'bit_group_size'
        for base_bit in range(0, n, bit_group_size):
            # Obtiene cuantos bits faltan (minimo entre el tamaño del grupo o 'n' quitandole 'base_bit')
            bits_remaining = min(bit_group_size, n - base_bit)
            if bits_remaining <= 0:
                break # Rompe el ciclo con break si no quedan bits por procesar, impidiendo loops inútiles

            # Optimización: procesamiento de múltiples bits de una vez
            # Se aplica bit shift y resta 1 para obtener una máscara bits a bits ((1 << x) - 1). Ej: <<2 -> 4-1 = 3 (11b)
            group_mask = np.uint32((1 << bits_remaining) - 1)
            # Aplicamos right shift (>>) para poner los bits de interés a la izq, y evitamos el resto aplicando AND ('&') a la mask
            group_values = (block_indices >> base_bit) & group_mask

            # iteramos procesando cada bit extraído en el subset actual
            for j in range(bits_remaining):
                # Extraemos nuestro shift precalculado para no tener que deducirlo aquí arriba
                shift = shifts[base_bit + j]
                # Tomamos bit desplazando posición 'j' y enmascarado con '& 1' para aislar unicamente su posición actual
                bit_value = (group_values >> j) & np.uint32(1)
                # Acumula por bloque aplicando el operador OR '|=', mandándolo hacia la indexación Left Shift '<< shift'
                block_result[:current_size] |= bit_value << shift

        # Pasa los resultados de cada bloque armado nuevamente al array general final 'result' sobre el slice equivalente[start:end]
        result[start:end] = block_result[:current_size]

    return result # Retorna el arr armado iterativamente en orden Little-Endian de los bits


def get_restricted_combinations(binary_str: str) -> tuple[list[str], list[str]]:
    # Retorna tupla de manera estructurada de dos arrays con strings de sus combinaciones validas
    """
    Genera las combinaciones para B y C basadas en la cadena binaria A.
    B solo puede tener 1s donde A tiene 1s.
    """
    # Función nativa str.count("X") cuenta cuantas ocurrencias de "1" hay dentro del scope 'A'.
    ones_count = binary_str.count("1")
    # Función reservada len() toma la magnitud (longitud/caracteres) de arreglo en este caso str.
    width = len(binary_str)

    # List comprehension encadenado a destructuring if (enumerate): recorre y almacena índice si bit es '1'
    one_positions = [i for i, bit in enumerate(binary_str) if bit == "1"]

    # Función interna. Sintaxis de nested function normal def `nom`: con acceso a scope del padre
    def generate_valid_combinations():
        # itertools product toma la lista con '0' y '1'. Con keyword argument repeat=ones_count se obtiene permutaciones
        base_combinations = list(product(["0", "1"], repeat=ones_count))
        # Inicialización de lista base vacía en python array []
        valid_combinations = []

        # itera los iterables string tuples de product resultantes "base_combinations"
        for comb in base_combinations:
            # Crea un array clonando ["0"] la cantidad de veces 'width' via operador sintáctico * para listas
            result = ["0"] * width
            # Colocamos los bits de la combinación en las posiciones donde A tiene 1s. 
            #  Sintaxis zip(lstA, lstB) itera entre elementos simultaneos (A_0 contra B_0, luego A_1 contra B_1 e izq...)
            for pos, bit in zip(one_positions, comb):
                # asignación local
                result[pos] = bit
            # list.append inserta al final. str.join une el arreglo intermedio 'result' de forma contigua para guardarlo concatenado
            valid_combinations.append("".join(result))

        # expone store de combinaciones final
        return valid_combinations

    # B tiene restricciones de 1s con la ejecución normal. Invocamos call func anidada
    B = generate_valid_combinations()
    # Genera una copia superficial (shallow copy) usando keyword '.copy()'. Array nativo func en Python
    C = (
        B.copy()
    )  # En este caso C es igual a B, pero podría ser diferente si se necesita más tarde

    # Retorna tupla de listas separada por "," devuelta en auto unboxing de Python '( , )'
    return B, C


def generate_combinations(A: str) -> list[tuple[str, str, str]]:
    # Def recibe str y retorna una lista indicando con TypeHints que sus elementos son un listado de Tuplas en grupos de(str, str, str).
    """
    Genera el producto cartesiano final de A con las combinaciones válidas de B y C.
    """
    # Extrae y desempaqueta auto array elements/values tuplado desde return call anterior
    B, C = get_restricted_combinations(A)
    # Convertimos A, B y C en formato "XX XX XX"
    # Anidación de list comprehension + str.join con generador step 'range'.
    # Range empieza en 0, detiene en len(target), saltando pasos de a 2. slice toma target[i : i+2].
    formatted_B = ["".join(b[i : i + 2] for i in range(0, len(b), 2)) for b in B]
    formatted_C = ["".join(c[i : i + 2] for i in range(0, len(c), 2)) for c in C]
    # Sincroniza A usando la misma sintaxis inline con base en scope A
    formatted_A = "".join(A[i : i + 2] for i in range(0, len(A), 2))

    # Generamos el producto cartesiano usando producto itertools y removiendo la posición 0 del resultado:
    # Syntax arr[1:] es un slicing sin fin para retornar todo el string/list exceptuando solo el ind 0
    return list(product([formatted_A], formatted_B, formatted_C))[1:]


def dec2bin(decimal: int, width: int) -> str:
    # Usa constructor built-in 'format(num, formater)` de python para formatear ints con template string local 
    #   '0{width}b' -> '0 (llenar espacios), {v=W} ancho, b (binario str)'
    return format(decimal, f"0{width}b")


def estados_binarios(n: int):
    # Genera usando bitwise left-shift `1 << n` que para numeros enteros a veces se usa como manera rápida de multiplicar '2^n'. 
    # itera el list comprehension y llama dec2bin para todos quitando el cero default con [1:]
    return [dec2bin(i, n) for i in range(1 << n)][1:]


# Ejemplos / Notas antiguas
# def estados_binarios(n: int, veces=3):
#     # Números de 0 a 2^N #
#     rango = [dec2bin(i, n) for i in range(2**n)]
#     return product(rango, repeat=veces)

