from src.funcs.base import ABECEDARY, LOWER_ABECEDARY
from src.constants.base import VOID_STR, SMALL_PHI_STR


def letras_a_bits(letras: str, n: int) -> str:
    """Convierte notación de letras del Excel de pruebas a cadena de bits de longitud n.

    Cada letra (case-insensitive) mapea a su posición en ABECEDARY (A→0, B→1, ...).
    Las letras presentes en `letras` dan bit=1; las ausentes dan bit=0.

    Ejemplos:
        letras_a_bits("ABCDEFGHIJ", 10) → "1111111111"
        letras_a_bits("ACEGI",      10) → "1010101010"
        letras_a_bits("BCDEFGHIJ",  10) → "0111111111"
    """
    # Lógica: Extrae las primeras n etiquetas del abecedario como tupla de referencia.
    #         ABECEDARY[:n] produce exactamente las n etiquetas del sistema
    #         (ej. ('A','B',...,'J') para n=10), que mapean 1-a-1 con los índices de nodos.
    # Sintaxis: El slicing `[:n]` sobre una tupla retorna una subtupla sin copia de datos internos.
    abc = ABECEDARY[:n]

    # Lógica: Normaliza la entrada a mayúsculas para comparación case-insensitive,
    #         de modo que "acegi" y "ACEGI" produzcan el mismo resultado.
    # Sintaxis: `str.upper()` retorna una nueva cadena sin modificar la original (inmutabilidad de str).
    letras_upper = letras.upper()

    # Lógica: Construye la cadena de bits posición a posición: bit=1 si la etiqueta del nodo i
    #         aparece en el conjunto de letras del usuario, bit=0 si está ausente.
    #         Esto traduce directamente la notación "ACEGI" del Excel de pruebas a "1010101010".
    # Sintaxis: `"".join(generador)` materializa la cadena sin lista intermedia en memoria.
    #           `abc[i] in letras_upper` ejecuta búsqueda O(|letras_upper|) sobre str — válido para n≤40.
    return "".join("1" if abc[i] in letras_upper else "0" for i in range(n))


def fmt_biparticion(
    parte_uno: list[tuple[int, ...], tuple[int, ...]],
    parte_dos: list[tuple[int, ...], tuple[int, ...]],
) -> str:
    # Lógica: Extrae el mecanismo (variables presentes) y el purview (variables futuras) de cada parte
    #         mediante desempaquetado de la lista; el orden convencional es [mecanismo, purview].
    # Sintaxis: `mech_p, pur_p = parte_uno` es desempaquetado de secuencia — asigna simultáneamente
    #           los dos primeros elementos de la lista a las variables locales.
    mech_p, pur_p = parte_uno
    mech_d, purv_d = parte_dos

    # Lógica: Convierte la lista de índices de purview a letras mayúsculas (ABECEDARY) separadas por coma,
    #         o usa VOID_STR ("∅") si la lista está vacía — representa el conjunto vacío de forma legible.
    # Sintaxis: `",".join(gen) if lista else VOID_STR` — la expresión ternaria cortocircuita:
    #           una lista vacía es falsy, así que VOID_STR se usa sin ejecutar el join.
    purv_prim = ",".join(ABECEDARY[j] for j in pur_p) if pur_p else VOID_STR
    # Lógica: Convierte los índices de mecanismo a letras minúsculas (LOWER_ABECEDARY); las minúsculas
    #         distinguen visualmente las variables presentes (mecanismo) de las futuras (purview).
    # Sintaxis: Idéntico al caso de purview pero usando LOWER_ABECEDARY y mech_p.
    mech_prim = ",".join(LOWER_ABECEDARY[i] for i in mech_p) if mech_p else VOID_STR

    purv_dual = ",".join(ABECEDARY[i] for i in purv_d) if purv_d else VOID_STR
    mech_dual = ",".join(LOWER_ABECEDARY[j] for j in mech_d) if mech_d else VOID_STR

    # Lógica: Calcula el ancho de cada columna como el máximo entre la longitud del purview y el mecanismo
    #         más 2 caracteres de margen lateral, para que purview y mecanismo queden alineados.
    # Sintaxis: `max(len(a), len(b)) + 2` retorna el mayor de los dos enteros con 2 de padding visual.
    width_prim = max(len(purv_prim), len(mech_prim)) + 2
    width_dual = max(len(purv_dual), len(mech_dual)) + 2

    # Lógica: Construye la representación visual en 2 filas × 2 columnas: fila superior = purviews,
    #         fila inferior = mecanismos; cada celda centrada en su ancho calculado.
    # Sintaxis: f-string con `{texto:^{ancho}}` centra el texto en un campo de `ancho` caracteres;
    #           `||` separa las dos columnas de la bipartición visualmente.
    return (
        f"|{purv_prim:^{width_prim}}||{purv_dual:^{width_dual}}|\n"
        f"|{mech_prim:^{width_prim}}||{mech_dual:^{width_dual}}|\n"
    )


def fmt_biparte_q(
    prim: list[tuple[int, int]],
    dual: list[tuple[int, int]],
    to_sort: bool = True,
) -> str:
    # Lógica: Formatea cada mitad de la bipartición delegando a fmt_parte_q para obtener
    #         las cadenas de purview (top) y mecanismo (bottom) de cada parte.
    # Sintaxis: `top_prim, bottom_prim = fmt_parte_q(...)` desempaqueta la tupla de 2 strings
    #           retornada por fmt_parte_q; `to_sort` se reenvía para controlar el orden interno.
    top_prim, bottom_prim = fmt_parte_q(prim, to_sort)
    top_dual, bottom_dual = fmt_parte_q(dual, to_sort)

    # Lógica: Une las cadenas de ambas partes en 2 líneas: fila superior (purviews) y fila inferior
    #         (mecanismos), con las columnas de ambas partes adyacentes sin separador adicional.
    # Sintaxis: f-string con `\n` como separador de líneas; las cadenas ya incluyen sus `|`
    #           laterales, por lo que la concatenación directa produce la tabla visual completa.
    return f"{top_prim}{top_dual}\n{bottom_prim}{bottom_dual}"


def fmt_parte_q(parte: list[tuple[int, int]], to_sort: bool = True) -> tuple[str, str]:
    # Lógica: Ordena los pares (tiempo, índice) por índice de nodo para que la representación
    #         visual muestre siempre los nodos en orden A, B, C, ... independientemente del orden
    #         en que el algoritmo los agrupó.
    # Sintaxis: `parte.sort(key=lambda x: x[1])` ordena la lista in-place; `x[1]` extrae el índice
    #           (segundo elemento del par) como clave de comparación; `to_sort` permite deshabilitar.
    if to_sort:
        parte.sort(key=lambda x: x[1])

    # Lógica: Clasifica cada par (tiempo, índice) en purview (tiempo=EFECTO=1 → mayúsculas) o mecanismo
    #         (tiempo=ACTUAL=0 → minúsculas) usando la convención de tiempo del sistema.
    # Sintaxis: `for time, idx in parte` desempaqueta cada tupla; la expresión ternaria
    #           `.append(X) if time else Y.append(Z)` selecciona la lista destino según el valor de tiempo.
    purv, mech = [], []
    for time, idx in parte:
        purv.append(ABECEDARY[idx]) if time else mech.append(LOWER_ABECEDARY[idx])

    # Lógica: Convierte las listas de etiquetas a strings separados por coma, o VOID_STR si están vacías.
    # Sintaxis: `",".join(lista) if lista else VOID_STR` — lista vacía es falsy; VOID_STR = "∅".
    str_purv = ",".join(purv) if purv else VOID_STR
    str_mech = ",".join(mech) if mech else VOID_STR
    # Lógica: Calcula el ancho de la columna tomando el máximo entre purview y mecanismo más 2 de margen,
    #         para que ambas filas queden alineadas en la misma anchura de columna.
    # Sintaxis: `max(len(a), len(b)) + 2` retorna el mayor de los dos enteros sumado a 2 (padding visual).
    width = max(len(str_purv), len(str_mech)) + 2

    # Lógica: Retorna las dos cadenas formateadas (purview y mecanismo) como tupla para que el llamador
    #         (fmt_biparte_q o fmt_k_particion) las posicione en la fila superior e inferior.
    # Sintaxis: `f"|{texto:^{width}}|"` centra el texto en un campo de `width` chars flanqueado por `|`;
    #           la coma en el return crea la tupla de 2 cadenas sin paréntesis explícitos.
    return f"|{str_purv:^{width}}|", f"|{str_mech:^{width}}|"


def fmt_k_particion(
    partes: "list[list[tuple[int, int]]]",
    etiquetas: "list[str] | None" = None,
) -> str:
    """
    Formatea una k-partición para visualización en consola.

    Cada parte en 'partes' es una lista de pares (tiempo, idx) donde:
        tiempo = 0 (ACTUAL)  → variable presente / mecanismo (minúsculas)
        tiempo = 1 (EFECTO)  → variable futura  / alcance    (mayúsculas)

    Ejemplo para k=3, partes=[[(1,0),(0,0)], [(1,1),(0,1)], [(1,2),(0,2)]]:
        | A  || B  || C  |
        | a  || b  || c  |
        S₁     S₂     S₃

    Args:
        partes:    Lista de k partes. Cada parte es lista de (tiempo, idx).
        etiquetas: Etiquetas opcionales para cada parte (ej. ["S₁","S₂","S₃"]).
                   Si es None se omiten.

    Returns:
        str: Representación visual multi-columna de la k-partición.

    Complejidad temporal:  Θ(Σᵢ |partesᵢ|) — un pase lineal por cada elemento.
    Complejidad espacial:  O(k · max_width) para los buffers de cadenas.
    """
    # Lógica: Inicializa las listas acumuladoras que almacenarán la fila superior (alcances/futuro) e inferior (mecanismos/presente).
    # Sintaxis: `list[str] = []` es anotación de tipo PEP 526 más inicialización a lista vacía; la anotación no afecta la ejecución.
    tops: list[str] = []
    bottoms: list[str] = []

    # Lógica: Itera sobre cada una de las k partes para generar su par de cadenas de texto formateadas.
    # Sintaxis: `for parte in partes` recorre la lista de partes; cada parte es una lista de pares (tiempo, idx).
    for parte in partes:
        # Lógica: Delega el formateo de una parte a fmt_parte_q, que separa alcances (mayúsculas) y mecanismos (minúsculas).
        # Sintaxis: `top, bottom = func(...)` es desempaquetado de tupla — asigna simultáneamente los dos valores retornados.
        #           `list(parte)` asegura que parte sea una lista mutable (requerido por to_sort para ordenar in-place).
        top, bottom = fmt_parte_q(list(parte), to_sort=True)

        # Lógica: Acumula la cadena de la fila de alcances de esta parte para unirla luego con las demás partes.
        # Sintaxis: `.append(valor)` añade el elemento al final de la lista in-place en tiempo amortizado O(1).
        tops.append(top)

        # Lógica: Acumula la cadena de la fila de mecanismos de esta parte para unirla luego con las demás partes.
        # Sintaxis: Idéntico a tops.append — mismo patrón para la fila inferior.
        bottoms.append(bottom)

    # Lógica: Une todas las cadenas de alcances en una sola línea; las columnas de las k partes quedan adyacentes sin separador.
    # Sintaxis: `"".join(lista)` concatena todos los strings de la lista usando la cadena vacía como separador.
    linea_top = "".join(tops)

    # Lógica: Une todas las cadenas de mecanismos en una sola línea, paralela a linea_top.
    # Sintaxis: `"".join(lista)` — misma operación que linea_top; produce la fila inferior de la tabla visual.
    linea_bottom = "".join(bottoms)

    # Lógica: Verifica si se deben agregar etiquetas (S₁, S₂, ...) debajo de cada columna.
    #         La condición doble garantiza que la cantidad de etiquetas coincida exactamente con el número de partes.
    # Sintaxis: `if etiquetas and len(etiquetas) == len(partes)` usa cortocircuito: si etiquetas es None o lista vacía, no evalúa len().
    if etiquetas and len(etiquetas) == len(partes):
        # Lógica: Extrae el ancho real de cada columna (longitud de la cadena top, que incluye los caracteres '|').
        # Sintaxis: `[len(t) for t in tops]` es list comprehension que aplica len() a cada string de la lista tops.
        anchos = [len(t) for t in tops]

        # Lógica: Construye la línea de etiquetas alineando cada una bajo su columna; se descuentan 2 caracteres de '|' laterales.
        # Sintaxis: f-string con `{etiquetas[i]:^{anchos[i]-2}}` — el operador `^` centra el texto en un campo de ancho `anchos[i]-2`.
        #           `"".join(gen_expr)` une los resultados de la generator expression sin separador.
        linea_etiq = "".join(
            f" {etiquetas[i]:^{anchos[i] - 2}} " for i in range(len(partes))
        )

        # Lógica: Retorna las tres líneas (alcances, mecanismos, etiquetas) separadas por saltos de línea.
        # Sintaxis: f-string con `\n` como separador entre líneas; retorna la cadena completa al llamador.
        return f"{linea_top}\n{linea_bottom}\n{linea_etiq}"

    # Lógica: Retorna solo las dos líneas de la tabla (alcances y mecanismos) cuando no se proporcionan etiquetas.
    # Sintaxis: `return f"..."` termina la función con la cadena formateada de dos líneas unidas por `\n`.
    return f"{linea_top}\n{linea_bottom}"
