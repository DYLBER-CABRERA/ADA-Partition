# from src.controllers.manager import Manager

# from src.controllers.strategies.force import BruteForce
# from src.controllers.strategies.q_nodes import QNodes
# from src.controllers.strategies.geometric import GeometricSIA


# def iniciar():
#     """Punto de entrada principal"""
#                     # ABCD #
#     # estado_inicial = "100"
#     # condiciones =    "111"
#     # alcance =        "111"
#     # mecanismo =      "111"
#     # estado_inicial = "0000"
#     # condiciones =    "1111"
#     # alcance =        "1111"
#     # mecanismo =      "1111"
#     # estado_inicial = "1000"
#     # condiciones =    "1111"
#     # alcance =        "0111"
#     # mecanismo =      "1111"
#     # estado_inicial = "100000"
#     # condiciones =    "111111"
#     # alcance =        "101011"
#     # mecanismo =      "111111"
#     # estado_inicial = "100000"
#     # condiciones =    "111111"
#     # alcance =        "111111"
#     # mecanismo =      "111111"
#     # estado_inicial = "100000"
#     # condiciones =    "111111"
#     # alcance =        "111111"
#     # mecanismo =      "011111"
#     # estado_inicial = "1000000000"
#     # condiciones =    "1111111111"
#     # alcance =        "1111111111"
#     # mecanismo =      "1111111111"
#     estado_inicial = "1000000000"
#     condiciones =    "1111111111"
#     alcance =        "0101010101"
#     mecanismo =      "1111111111"
#     # estado_inicial = "1000000000"
#     # condiciones =    "1111111111"
#     # alcance =        "1111111110"
#     # mecanismo =      "1111111111"
#     # estado_inicial = "10000000000000000000"
#     # condiciones =    "11111111111111111111"
#     # alcance =        "11111111111111111111"
#     # mecanismo =      "11111111111111111111"
#     # estado_inicial = "10000000000000000000"
#     # condiciones =    "11111111111111111111"
#     # alcance =        "11011011011011011011"
#     # mecanismo =      "10101010101010101010"

#     gestor_sistema = Manager(estado_inicial)

#     ### Ejemplo de solución mediante módulo de fuerza bruta ###
#     analizador_fb = GeometricSIA(gestor_sistema)
#     # analizador_fb = BruteForce(gestor_sistema)
#     sia_uno = analizador_fb.aplicar_estrategia(
#         condiciones,
#         alcance,
#         mecanismo,
#     )
#     print(sia_uno)
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.q_nodes import QNodes
# Optional import: this project often runs only geometric strategy.
try:
    from src.controllers.strategies.phi import Phi
except Exception:
    Phi = None
from src.controllers.strategies.k_geometric import KGeometricSIA
from src.constants.models import K_MIN, K_MAX
from src.funcs.base import ABECEDARY
from src.funcs.format import letras_a_bits
import multiprocessing
import numpy as np
import pandas as pd
import os
import re
from pathlib import Path
import sys

METHOD2_ROOT = Path(__file__).resolve().parents[1]
GEOMIP_ROOT = Path(__file__).resolve().parents[3]

def convertir_a_binario(texto: str, n_bits: int = 20) -> str:
    """
        Lógica: Delegación completa a letras_a_bits para eliminar la duplicación de la lógica
            de conversión. El comportamiento es idéntico al anterior pero reutiliza
            ABECEDARY en lugar del string hardcodeado "ABCDEFGHIJKLMNOPQRST".
        Sintaxis: Wrapper de una línea — permite mantener el nombre original sin romper
              las llamadas existentes en ejecutar_desde_excel y ejecutar_k_geometric_desde_excel.
    """
    return letras_a_bits(texto, n_bits)

def ejecutar_con_tiempo(config_sistema, condiciones, alcance, mecanismo, resultado_queue, tpm):
    """ Lógica: Función ejecutada en un proceso hijo aislado para invocar GeometricSIA sin bloquear el padre.
             El aislamiento en proceso separado evita que errores o timeouts de un subsistema
             detengan el procesamiento del lote completo en `ejecutar_desde_excel`.
     Sintaxis: Función de nivel de módulo — obligatorio para multiprocessing en Windows (pickle requiere importabilidad). 
    """
    try:
        # Lógica: Instancia GeometricSIA con el Manager serializado desde el proceso padre por pickle.
        # Sintaxis: Constructor estándar; `config_sistema` ya fue deserializado por multiprocessing.
        analizador_fi = GeometricSIA(config_sistema)
        # Lógica: Ejecuta la estrategia de bi-partición con los parámetros del subsistema actual.
        # Sintaxis: La firma no incluye kwarg `k` — GeometricSIA siempre aplica bi-partición (k=2).
        sia_dos = analizador_fi.aplicar_estrategia(condiciones, alcance, mecanismo, tpm)
        # Lógica: Envía el resultado al padre vía cola FIFO compartida; el punto decimal se reemplaza
        #         por coma para compatibilidad con Excel en locales españolas (separador decimal = coma).
        # Sintaxis: `.put(dict)` inserta el diccionario en la cola de forma segura entre procesos.
        resultado_queue.put({
            "particion": sia_dos.particion,
            "perdida": str(sia_dos.perdida).replace('.', ','),
            "tiempo": str(sia_dos.tiempo_ejecucion).replace('.', ','),
        })

    except Exception as e:
        # Lógica: Captura cualquier excepción del hijo y envía un dict de Nones para evitar deadlock.
        #         Sin esta captura, un error silencioso dejaría la cola vacía y el padre esperaría
        #         indefinidamente hasta el timeout de 3600 s.
        # Sintaxis: `except Exception as e` captura todas las subclases de Exception (no SystemExit).
        resultado_queue.put({
            "particion": None,
            "perdida": None,
            "tiempo": None,
        })

def ejecutar_k_geometric_con_tiempo(
    config_sistema,
    condiciones,
    alcance,
    mecanismo,
    resultado_queue,
    tpm,
    k,
):
    # Lógica: Función ejecutada en un proceso hijo aislado para invocar KGeometricSIA.
    #         El aislamiento evita que errores de memoria o excepciones no capturadas bloqueen el proceso padre.
    # Sintaxis: Función de nivel de módulo — obligatorio para multiprocessing en Windows (pickle requiere importabilidad).
    try:
        # Lógica: Instancia KGeometricSIA con el gestor del sistema recibido del proceso padre.
        # Sintaxis: Constructor estándar; `config_sistema` es un Manager ya inicializado y serializado por pickle.
        analizador = KGeometricSIA(config_sistema)

        # Lógica: Ejecuta la estrategia K-GeoMIP con el valor k especificado; retorna un objeto Solution.
        # Sintaxis: Keyword argument `k=k` coincide con la firma `aplicar_estrategia(..., k=K_MIN)`.
        sia = analizador.aplicar_estrategia(condiciones, alcance, mecanismo, tpm, k=k)

        # Lógica: Envía el resultado estructurado al proceso padre vía la cola multiproceso compartida.
        #         Se reemplaza '.' por ',' en los números para compatibilidad con Excel en locales españoles.
        # Sintaxis: `.put(dict)` inserta el diccionario en la cola FIFO de forma segura entre procesos.
        resultado_queue.put({
            "particion": sia.particion,
            "perdida": str(sia.perdida).replace(".", ","),
            "tiempo": str(sia.tiempo_ejecucion).replace(".", ","),
        })
    except Exception:
        # Lógica: Captura cualquier excepción del proceso hijo y envía dict vacío para evitar deadlock en el padre.
        #         Sin esta captura, un error silencioso dejaría la cola vacía y el padre esperaría indefinidamente.
        # Sintaxis: `except Exception` captura todas las subclases de Exception (no SystemExit/KeyboardInterrupt).
        resultado_queue.put({
            "particion": None,
            "perdida": None,
            "tiempo": None,
        })


def resolver_tpm_path(estado_inicio: str, variante: str = "A") -> Path:
    """Find TPM file in common project locations based on state size."""
    # Lógica: Construye el nombre del CSV de la TPM usando el número de nodos y la variante indicada.
    #         La convención es "NxY.csv" donde x=número de nodos e Y=letra variante (A, B, C...).
    #         Por defecto variante="A" mantiene el comportamiento anterior sin romper ninguna llamada existente.
    # Sintaxis: f-string `f"N{len(str)}{variante}.csv"` interpola tanto el tamaño como la letra de variante.
    sample_name = f"N{len(estado_inicio)}{variante}.csv"
    # Lógica: Define las rutas candidatas en orden de prioridad: rutas locales (.samples/) tienen prioridad
    #         sobre data/samples/ para facilitar pruebas sin mover archivos al directorio global.
    # Sintaxis: Tupla de objetos Path; el operador `/` de pathlib concatena segmentos de ruta.
    candidates = (
        METHOD2_ROOT / "src" / ".samples" / sample_name,
        METHOD2_ROOT / ".samples" / sample_name,
        GEOMIP_ROOT / "data" / "samples" / sample_name,
    )
    for candidate in candidates:
        if candidate.exists():
            print(f"[TPM] Usando: {candidate}")
            return candidate
    # Lógica: Si ninguna ruta existe, lanza FileNotFoundError con la lista de rutas intentadas
    #         para que el usuario pueda ubicar el archivo faltante sin debugging adicional.
    # Sintaxis: `', '.join(str(c) for c in candidates)` genera la lista de rutas como string legible.
    raise FileNotFoundError(
        f"No se encontró la TPM '{sample_name}'. Busqué en: {', '.join(str(c) for c in candidates)}"
    )


def inferir_estado_inicial(n: int | None = None) -> str:
    """Infer an initial state from available datasets.

    If n is given, uses the dataset for exactly n nodes (e.g. n=10 → N10A.csv).
    If n is None, falls back to the largest available dataset.
    """
    # Lógica: Define las 3 rutas candidatas donde pueden residir los archivos de muestras TPM,
    #         en orden de prioridad: local al método 2 → raíz del proyecto → carpeta data/.
    # Sintaxis: Tupla de Path — inmutable y más eficiente que lista para iteración de solo lectura.
    sample_dirs = (
        METHOD2_ROOT / "src" / ".samples",
        METHOD2_ROOT / ".samples",
        GEOMIP_ROOT / "data" / "samples",
    )
    # Lógica: Patrón regex para extraer el número de nodos del nombre de archivo (e.g. "N10A.csv" → 10).
    #         El grupo de captura `(\d+)` aísla el entero; `[A-Z]` acepta cualquier variante de letra (A, B, ...).
    # Sintaxis: `re.compile` precompila el patrón para reutilizarlo eficientemente en el bucle siguiente.
    pattern = re.compile(r"N(\d+)[A-Z]\.csv$")
    # Lógica: Acumula los tamaños de sistema encontrados en disco para determinar cuál usar.
    # Sintaxis: Lista vacía — se rellena con `.append()` dentro del bucle de búsqueda.
    available_sizes = []

    # Lógica: Busca archivos TPM en cada directorio candidato; ignora los que no existen en disco.
    #         El glob "N*.csv" filtra solo archivos del patrón esperado sin listar todo el directorio.
    # Sintaxis: `sample_dir.exists()` retorna False si la ruta no existe en el sistema de archivos.
    for sample_dir in sample_dirs:
        if not sample_dir.exists():
            continue
        # Lógica: Aplica regex a cada archivo encontrado para extraer el entero n del nombre.
        #         `match.group(1)` extrae el primer grupo de captura `(\d+)` y se convierte a int.
        # Sintaxis: `sample_dir.glob("N*.csv")` es un generador — no carga todos los paths en RAM a la vez.
        for sample_file in sample_dir.glob("N*.csv"):
            match = pattern.match(sample_file.name)
            if match:
                available_sizes.append(int(match.group(1)))

    # Lógica: Si no se encontró ningún archivo TPM en ninguna ruta candidata, el sistema no puede operar.
    #         Lanzar FileNotFoundError aquí da un mensaje claro antes de fallar silenciosamente más adelante.
    # Sintaxis: `not available_sizes` es equivalente a `len(available_sizes) == 0` pero más idiomático en Python.
    if not available_sizes:
        raise FileNotFoundError("No hay archivos de muestras TPM disponibles en data/samples ni .samples.")

    # Lógica: Si n fue especificado, valida que exista un dataset para ese tamaño exacto antes de continuar.
    #         Si n es None, selecciona el sistema más grande disponible como default conservador.
    # Sintaxis: `n not in available_sizes` usa búsqueda lineal O(|available_sizes|) — lista pequeña, aceptable.
    if n is not None:
        if n not in available_sizes:
            raise FileNotFoundError(
                f"No hay archivo de muestra para N={n}. "
                f"Disponibles: {sorted(set(available_sizes))}"
            )
        n_bits = n
    else:
        # Lógica: `max()` selecciona el sistema más grande encontrado cuando el usuario no especifica n.
        # Sintaxis: `max(iterable)` recorre la lista una vez en O(|available_sizes|).
        n_bits = max(available_sizes)

    # Lógica: El estado inicial canónico del proyecto activa solo el primer nodo (bit 0 = 1) y
    #         apaga todos los demás. Este estado es el punto de partida estándar de todos los benchmarks.
    # Sintaxis: `"1" + ("0" * (n_bits - 1))` concatena strings en O(n_bits) produciendo un str inmutable.
    return "1" + ("0" * (n_bits - 1))


def ejecutar_desde_excel(
    ruta_excel: Path,
    ruta_salida: Path,
    inicio=0,
    cantidad=50,
    estado_inicio: str | None = None,
    condiciones: str | None = None,
    n: int | None = None,
):
    # Lógica: Lee la hoja 8 (índice base 0) del Excel de pruebas, columna B desde la fila 4,
    #         con encabezado renombrado a "Subsistema" para acceso uniforme en el código.
    # Sintaxis: `sheet_name=8` selecciona por índice; `skiprows=3` omite las 3 filas de cabecera del formato Excel.
    df = pd.read_excel(ruta_excel, sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"]) #! here
    # Lógica: Elimina celdas vacías (NaN) y convierte la columna a lista Python para indexado directo.
    # Sintaxis: `.dropna()` filtra NaN del Series; `.tolist()` materializa el resultado en lista estándar.
    filas = df["Subsistema"].dropna().tolist()
    # Lógica: Selecciona el rango de filas a procesar en este lote; permite reanudar desde un punto arbitrario
    #         sin releer el archivo completo ni perder la posición anterior del lote.
    # Sintaxis: `filas[inicio:inicio + cantidad]` usa slicing — O(cantidad), no copia el resto de la lista.
    filas = filas[inicio:inicio + cantidad]
    # Lógica: Lista vacía que acumulará un dict de resultado por cada subsistema procesado en el lote.
    # Sintaxis: Lista de Python — se rellena con `.append()` en O(1) amortizado dentro del bucle principal.
    resultados = []

    # Lógica: Si el llamador no provee estado inicial, se infiere automáticamente del dataset disponible en disco.
    #         `condiciones` None se interpreta como "todo el sistema activo": cadena de unos de longitud n.
    # Sintaxis: Operador `or` de Python — evalúa el lado derecho solo si el izquierdo es falsy (None o "").
    estado_inicio = estado_inicio or inferir_estado_inicial(n)
    condiciones = condiciones or ("1" * len(estado_inicio))
    # Lógica: Carga la TPM una sola vez antes del bucle para evitar releerla en cada iteración del lote.
    # Sintaxis: `np.genfromtxt(path, delimiter=",")` lee el CSV como ndarray float64 sin encabezado.
    tpm_path = resolver_tpm_path(estado_inicio)
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    # Lógica: Itera cada subsistema del rango seleccionado; el índice `i` refleja la posición real en el Excel.
    # Sintaxis: `enumerate(iterable, start=N)` produce pares (N, item), (N+1, item), ...
    for i, fila in enumerate(filas, start=inicio + 1):
        # Lógica: Divide la fila por '|' para separar la notación de alcance (izquierda) y mecanismo (derecha).
        # Sintaxis: `str.split("|")` retorna lista; longitud != 2 indica fila malformada → se omite.
        partes = fila.split("|")
        if len(partes) != 2:
            continue

        # Lógica: Convierte la representación de letras del alcance y mecanismo a cadena binaria de n bits.
        #         Se recortan los últimos 3 chars del alcance (sufijo de formato) y el último del mecanismo.
        # Sintaxis: `partes[0][:len-3]` usa slicing; `convertir_a_binario` delega a `letras_a_bits`.
        alcance = convertir_a_binario(partes[0][:len(partes[0]) - 3], n_bits=len(estado_inicio))
        mecanismo = convertir_a_binario(partes[1][:len(partes[1]) - 1], n_bits=len(estado_inicio))
        print(f"Iteración {i} - Alcance: {alcance}, Mecanismo: {mecanismo}")

        # Lógica: Crea un Manager nuevo por iteración para garantizar independencia entre subsistemas.
        # Sintaxis: `Manager(estado_inicial=...)` — keyword argument explícito para legibilidad.
        config_sistema = Manager(estado_inicial=estado_inicio)

        # Lógica: Cola FIFO compartida entre padre e hijo para transferir el resultado de GeometricSIA.
        # Sintaxis: `multiprocessing.Queue()` implementa una cola segura entre procesos del SO.
        resultado_queue = multiprocessing.Queue()
        # Lógica: Lanza el proceso hijo aislado que ejecuta GeometricSIA con el subsistema actual.
        # Sintaxis: `multiprocessing.Process(target=func, args=tuple)` — args debe ser serializable por pickle.
        proceso = multiprocessing.Process(target=ejecutar_con_tiempo, args=(config_sistema, condiciones, alcance, mecanismo, resultado_queue, tpm))

        # Lógica: Inicia el proceso hijo; `.start()` no bloquea al padre.
        # Sintaxis: `.start()` lanza el proceso en el SO y retorna inmediatamente.
        proceso.start()
        # Lógica: Bloquea el padre hasta que el hijo termine o se agoten los 3600 s de timeout.
        # Sintaxis: `.join(timeout=N)` retorna None tanto si el hijo terminó como si expiró el tiempo.
        proceso.join(timeout=3600)

        # Lógica: Si el proceso sigue activo tras el timeout, superó el límite; se termina y marca nulo.
        # Sintaxis: `.is_alive()` retorna True si el proceso aún se ejecuta al momento de la llamada.
        if proceso.is_alive():
            print(f"Iteración {i} - Tiempo límite alcanzado, terminando proceso...")
            # Lógica: Envía SIGTERM al proceso hijo y espera su terminación antes de continuar.
            # Sintaxis: `.terminate()` es no-bloqueante; `.join()` sin timeout espera hasta que termine.
            proceso.terminate()
            proceso.join()
            resultado = {"perdida": None, "tiempo": None, "particion": None}
        else:
            # Lógica: Extrae el resultado de la cola si el proceso terminó normalmente.
            #         Si la cola está vacía (excepción no capturada en el hijo), devuelve dict nulo.
            # Sintaxis: Ternario `A if cond else B`; `.empty()` comprueba si la cola no tiene elementos.
            resultado = (
                resultado_queue.get()
                if not resultado_queue.empty()
                else {"perdida": None, "tiempo": None, "particion": None}
            )

        # Lógica: Acumula el resultado del subsistema en la lista para exportarlo al Excel al final.
        # Sintaxis: `.append(dict)` añade el diccionario al final de la lista en O(1) amortizado.
        resultados.append({
            "Iteración": i,
            "Alcance": alcance,
            "Mecanismo": mecanismo,
            "Partición": resultado["particion"],
            "Pérdida": resultado["perdida"],
            "Tiempo de ejecución (s)": resultado["tiempo"],
        })
    # Lógica: Convierte la lista de dicts a DataFrame y lo exporta al Excel de salida.
    #         `mkdir(parents=True, exist_ok=True)` crea el directorio de salida si no existe.
    # Sintaxis: `pd.DataFrame(lista_dicts)` infiere las columnas desde las claves del primer dict;
    #           `.to_excel(ruta, index=False)` escribe sin la columna de índice numérico de pandas.
    df_resultados = pd.DataFrame(resultados)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_resultados.to_excel(ruta_salida, index=False)
    print(f"Resultados guardados en {ruta_salida}")


def ejecutar_k_geometric_desde_excel(
    ruta_excel: Path,
    ruta_salida: Path,
    k: int = K_MIN,
    inicio: int = 0,
    cantidad: int = 50,
    estado_inicio: str | None = None,
    condiciones: str | None = None,
    n: int | None = None,
):
    # Lógica: Carga la hoja de subsistemas del Excel de entrada (hoja índice 8, columna B, sin las 3 primeras filas de encabezado).
    #         El formato es idéntico al de ejecutar_desde_excel para mantener compatibilidad con el mismo archivo de pruebas.
    # Sintaxis: `pd.read_excel(sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"])` —
    #           `sheet_name=8` selecciona la hoja por índice (base 0); `skiprows=3` omite encabezados.
    df = pd.read_excel(ruta_excel, sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"])

    # Lógica: Extrae la lista de subsistemas no nulos y recorta al rango [inicio, inicio+cantidad).
    # Sintaxis: `.dropna()` elimina NaN de la Serie; `.tolist()` convierte a lista Python; slicing `[inicio:fin]`.
    filas = df["Subsistema"].dropna().tolist()
    filas = filas[inicio : inicio + cantidad]

    # Lógica: Lista que acumulará un diccionario de resultados por cada subsistema procesado.
    # Sintaxis: Lista vacía inicializada; cada iteración agrega un dict con `.append(dict)`.
    resultados = []

    estado_inicio = estado_inicio or inferir_estado_inicial(n)
    condiciones = condiciones or ("1" * len(estado_inicio))
    tpm_path = resolver_tpm_path(estado_inicio)
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    # Lógica: Itera cada subsistema en el rango seleccionado; el índice `i` refleja la posición real en el Excel.
    # Sintaxis: `enumerate(iterable, start=N)` produce pares (N, item), (N+1, item), ...
    for i, fila in enumerate(filas, start=inicio + 1):
        # Lógica: Divide la fila por '|' para separar la notación de alcance (izquierda) y mecanismo (derecha).
        # Sintaxis: `str.split("|")` retorna lista; longitud != 2 indica fila malformada.
        partes = fila.split("|")

        # Lógica: Omite filas que no tienen exactamente el separador '|' (filas de encabezado o vacías).
        # Sintaxis: `if cond: continue` salta al siguiente ciclo del for sin ejecutar el resto del cuerpo.
        if len(partes) != 2:
            continue

        # Lógica: Convierte la representación de letras del alcance a cadena binaria de n bits.
        #         Se recortan los últimos 3 caracteres del alcance (espacio + separador de formato).
        # Sintaxis: `partes[0][:len(partes[0]) - 3]` usa slicing negativo implícito para quitar el sufijo.
        alcance = convertir_a_binario(
            partes[0][: len(partes[0]) - 3], n_bits=len(estado_inicio)
        )

        # Lógica: Convierte la representación de letras del mecanismo a cadena binaria de n bits.
        #         Se recorta el último carácter del mecanismo (cierre de paréntesis o espacio de formato).
        # Sintaxis: `partes[1][:len(partes[1]) - 1]` quita el último carácter con slicing.
        mecanismo = convertir_a_binario(
            partes[1][: len(partes[1]) - 1], n_bits=len(estado_inicio)
        )

        # Lógica: Imprime el progreso incluyendo el valor de k para distinguir las ejecuciones en la consola.
        # Sintaxis: f-string con `[k={k}]` intercala el valor de k en la línea de progreso.
        print(f"Iteración {i} [k={k}] - Alcance: {alcance}, Mecanismo: {mecanismo}")

        # Lógica: Crea un nuevo Manager por cada subsistema para garantizar independencia entre iteraciones.
        # Sintaxis: `Manager(estado_inicial=...)` — kwarg explícito para legibilidad.
        config_sistema = Manager(estado_inicial=estado_inicio)

        # Lógica: Cola FIFO compartida entre el proceso padre y el hijo para transferir el resultado.
        # Sintaxis: `multiprocessing.Queue()` implementa una cola segura entre procesos del SO.
        resultado_queue = multiprocessing.Queue()

        # Lógica: Lanza un proceso hijo que ejecuta KGeometricSIA de forma aislada con el k configurado.
        #         El aislamiento en proceso hijo evita que fallas de un subsistema detengan todo el lote.
        # Sintaxis: `multiprocessing.Process(target=func, args=tuple)` — args debe ser serializable por pickle.
        proceso = multiprocessing.Process(
            target=ejecutar_k_geometric_con_tiempo,
            args=(config_sistema, condiciones, alcance, mecanismo, resultado_queue, tpm, k),
        )

        # Lógica: Inicia la ejecución del proceso hijo en el sistema operativo.
        # Sintaxis: `.start()` no bloquea el padre; el hijo ejecuta `target(*args)` en paralelo.
        proceso.start()

        # Lógica: Bloquea el padre hasta que el hijo termine o transcurra el timeout de 3600 s (1 hora).
        # Sintaxis: `.join(timeout=N)` retorna None tanto si el proceso terminó como si se agotó el tiempo.
        proceso.join(timeout=3600)

        # Lógica: Si el proceso sigue vivo tras el timeout, se considera que superó el límite de tiempo.
        # Sintaxis: `.is_alive()` retorna True si el proceso está en ejecución al momento de la llamada.
        if proceso.is_alive():
            print(f"Iteración {i} [k={k}] - Tiempo límite alcanzado, terminando proceso...")
            # Lógica: Termina el proceso hijo enviándole SIGTERM; `.join()` espera que efectivamente termine.
            # Sintaxis: `.terminate()` es no-bloqueante; `.join()` sin timeout bloquea hasta la terminación.
            proceso.terminate()
            proceso.join()
            resultado = {"perdida": None, "tiempo": None, "particion": None}
        else:
            # Lógica: Extrae el resultado de la cola si el proceso terminó normalmente con un `put`.
            #         Si la cola está vacía (excepción no capturada en el hijo), devuelve dict nulo.
            # Sintaxis: Operador ternario `A if cond else B`; `.empty()` es O(1) para la comprobación rápida.
            resultado = (
                resultado_queue.get()
                if not resultado_queue.empty()
                else {"perdida": None, "tiempo": None, "particion": None}
            )

        # Lógica: Agrega el resultado del subsistema actual incluyendo la columna "k" para análisis comparativo.
        #         La columna "k" permite comparar resultados de bi-partición vs k-partición en el mismo archivo.
        # Sintaxis: `.append(dict)` agrega el diccionario al final de la lista en O(1) amortizado.
        resultados.append(
            {
                "Iteración": i,
                "k": k,
                "Alcance": alcance,
                "Mecanismo": mecanismo,
                "Partición": resultado["particion"],
                "Pérdida": resultado["perdida"],
                "Tiempo de ejecución (s)": resultado["tiempo"],
            }
        )

    # Lógica: Convierte la lista de diccionarios a DataFrame y lo exporta al archivo Excel de salida.
    #         `mkdir(parents=True, exist_ok=True)` crea el directorio si no existe (sin error si ya existe).
    # Sintaxis: `pd.DataFrame(lista_de_dicts)` infiere las columnas desde las claves del primer dict.
    df_resultados = pd.DataFrame(resultados)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_resultados.to_excel(ruta_salida, index=False)
    print(f"Resultados guardados en {ruta_salida}")


def run_prueba(
    alcance: str,
    mecanismo: str,
    k: int = 2,
    estado_inicio: str | None = None,
    condiciones: str | None = None,
    variante: str = "A",
    n: int | None = None,
) -> None:
    """Ejecuta una prueba individual con notación de letras del Excel de pruebas.

    Args:
        alcance:       Letras del Alcance o Purview (t+1), ej. "ABCDEFGHIJ" o "ACEGI".
        mecanismo:     Letras del Mecanismo (t),          ej. "ABCDEFGHIJ" o "BDFHJ".
        k:             Número de particiones (2=bipartición, 3,4,5=k-partición).
        estado_inicio: Bits del estado inicial, ej. "1000000000". Si es None se infiere.
        condiciones:   Bits del sistema candidato. Si es None se asume sistema completo.

    Ejemplo de uso:
        >>> run_prueba("ABCDEFGHIJ", "ACEGI", k=2)
        >>> run_prueba("ABCDEFGHI",  "BDFHJ", k=3, estado_inicio="1000000000")
    """
    estado_inicio = estado_inicio or inferir_estado_inicial(n)

    # Lógica: Determina n (número de nodos) a partir del estado inicial, que es la cadena
    #         de bits de referencia para todo el sistema.
    # Sintaxis: `len(str)` retorna el número de caracteres en O(1) para cadenas Python.
    n = len(estado_inicio)

    # Lógica: Si no se proveen condiciones, asume sistema candidato completo (todos los nodos activos).
    #         "1"*n genera la cadena "1111...1" de n caracteres que indica ningún nodo condicionado.
    # Sintaxis: La multiplicación `str * int` repite el string n veces en O(n).
    condiciones = condiciones or "1" * n

    # Lógica: Convierte la notación de letras del Excel de pruebas a cadena de bits que el
    #         método sia_preparar_subsistema espera como entrada.
    #         Ej: "ACEGI" con n=10 → "1010101010" (posición 0,2,4,6,8 activas).
    # Sintaxis: Doble asignación paralela con la misma función — misma n para coherencia de tamaño.
    alcance_bits   = letras_a_bits(alcance,   n)
    mecanismo_bits = letras_a_bits(mecanismo, n)

    # Lógica: Construye la representación legible del sistema completo (ej. "ABCDEFGHIJ")
    #         para el encabezado de la salida, usando las primeras n etiquetas del abecedario.
    # Sintaxis: `"".join(iterable)` concatena los elementos sin separador en O(n).
    sistema_str = "".join(ABECEDARY[:n])

    # Lógica: Imprime el encabezado de diagnóstico que muestra la conversión letras→bits,
    #         permitiendo verificar visualmente que la traducción es correcta antes de ver resultados.
    # Sintaxis: f-string con `{'='*50}` genera una línea divisora de 50 signos iguales en O(1).
    #           `{alcance:>{n}}` alinea la cadena a la derecha en un campo de ancho n para tabulación.
    print(f"\n{'='*50}")
    print(f"Sistema:        {sistema_str}")
    print(f"Estado inicial: {estado_inicio}")
    print(f"Alcance:        {alcance:>{n}} -> {alcance_bits}")
    print(f"Mecanismo:      {mecanismo:>{n}} -> {mecanismo_bits}")
    print(f"k = {k}")
    print(f"{'='*50}")

    # Lógica: Resuelve la ruta del CSV con la TPM usando la variante indicada y la carga como NDArray float64.
    #         `variante` permite seleccionar N15B.csv en lugar de N15A.csv sin cambiar la lógica de búsqueda.
    # Sintaxis: `np.genfromtxt(ruta, delimiter=",")` lee un CSV sin encabezado como ndarray float64.
    tpm_path = resolver_tpm_path(estado_inicio, variante=variante)
    tpm      = np.genfromtxt(tpm_path, delimiter=",")

    # Lógica: Crea un Manager por cada llamada para garantizar independencia entre pruebas.
    # Sintaxis: Keyword argument `estado_inicial=...` coincide con el campo del dataclass Manager.
    config   = Manager(estado_inicial=estado_inicio)

    # Lógica: Bifurca el despacho según k: k=K_MIN(2) usa GeometricSIA (bi-partición exacta),
    #         k>2 usa KGeometricSIA (k-partición heurística greedy).
    #         La separación garantiza que k=2 sea idéntico al flujo original sin regresión.
    # Sintaxis: `if k == K_MIN` compara con la constante K_MIN=2 importada de constants.models.
    if k == K_MIN:
        # Lógica: Instancia GeometricSIA y ejecuta la estrategia de bi-partición.
        # Sintaxis: La firma es (condicion, alcance, mecanismo, tpm) — sin kwarg k.
        estrategia = GeometricSIA(config)
        resultado  = estrategia.aplicar_estrategia(condiciones, alcance_bits, mecanismo_bits, tpm)
    else:
        # Lógica: Instancia KGeometricSIA y ejecuta la estrategia de k-partición greedy.
        # Sintaxis: `k=k` keyword argument coincide con la firma de aplicar_estrategia en KGeometricSIA.
        estrategia = KGeometricSIA(config)
        resultado  = estrategia.aplicar_estrategia(condiciones, alcance_bits, mecanismo_bits, tpm, k=k)

    # Lógica: Reconfigura stdout a UTF-8 antes de imprimir para que los caracteres unicode
    #         del objeto Solution (═, ≡, φ, colores ANSI de colorama) se rendericen
    #         correctamente en la consola Windows, que por defecto usa CP1252.
    # Sintaxis: `sys.stdout.reconfigure(encoding="utf-8")` es Python 3.7+ y opera in-place
    #           sin reemplazar el stream — colorama sigue funcionando sobre el mismo objeto.
   
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Lógica: Imprime el objeto Solution que contiene partición, pérdida (EMD) y tiempo.
    #         __str__ de Solution ya formatea toda la información de manera legible.
    # Sintaxis: `print(obj)` invoca implícitamente obj.__str__().
    print(resultado)


def iniciar():
    # Lógica: Lee la ruta del Excel de entrada desde la variable de entorno o usa la ruta por defecto del proyecto.
    # Sintaxis: `os.getenv("VAR", default)` retorna el valor de la variable si está definida, o `default` si no.
    ruta_entrada = Path(
        os.getenv(
            "GEOMIP_INPUT_XLSX",
            str(GEOMIP_ROOT / "results" / "Pruebas_Metodo2.xlsx"),
        )
    )

    # Lógica: Lee el valor de k desde KGEOMIP_K; default K_MIN=2 para mantener comportamiento original.
    #         k=2 → despacha a GeometricSIA (bi-partición exacta, sin regresión).
    #         k∈{3,4,5} → despacha a KGeometricSIA (k-partición con heurística greedy).
    # Sintaxis: `int(os.getenv("KGEOMIP_K", str(K_MIN)))` — os.getenv retorna str; int() la convierte a entero.
    k = int(os.getenv("KGEOMIP_K", str(K_MIN)))

    # Lógica: Bifurcación de flujo según k — garantiza que k=2 sea idéntico al comportamiento pre-existente.
    # Sintaxis: `if k == K_MIN` compara con la constante K_MIN=2 importada de constants.models.
    if k == K_MIN:
        # Lógica: Ruta de salida por defecto para el flujo GeometricSIA (bi-partición).
        # Sintaxis: Mismo patrón de lectura de variable de entorno con fallback.
        ruta_salida = Path(
            os.getenv(
                "GEOMIP_OUTPUT_XLSX",
                str(GEOMIP_ROOT / "results" / "resultados_Geometric.xlsx"),
            )
        )
        # Lógica: Ejecuta el flujo original de bi-particiones; no pasa k porque GeometricSIA no acepta ese parámetro.
        # Sintaxis: Llamada directa a función; el flujo k=2 queda sin cambios respecto a la versión anterior.
        ejecutar_desde_excel(ruta_entrada, ruta_salida)
    else:
        # Lógica: Nombre de archivo incluye el valor de k para distinguir resultados de distintas configuraciones.
        #         Ejemplo: resultados_KGeometric_k3.xlsx, resultados_KGeometric_k4.xlsx, etc.
        # Sintaxis: f-string `f"resultados_KGeometric_k{k}.xlsx"` interpola el valor entero k en el nombre.
        ruta_salida = Path(
            os.getenv(
                "GEOMIP_OUTPUT_XLSX",
                str(GEOMIP_ROOT / "results" / f"resultados_KGeometric_k{k}.xlsx"),
            )
        )
        # Lógica: Ejecuta el flujo K-GeoMIP usando KGeometricSIA para el k leído del entorno.
        # Sintaxis: Keyword argument `k=k` coincide con la firma de ejecutar_k_geometric_desde_excel.
        ejecutar_k_geometric_desde_excel(ruta_entrada, ruta_salida, k=k)