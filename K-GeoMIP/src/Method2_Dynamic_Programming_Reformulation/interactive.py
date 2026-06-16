#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interactive.py -- Interfaz interactiva de terminal para K-GeoMIP
=================================================================
Permite al usuario ingresar estado inicial, alcance, mecanismo,
número de particiones k y variante del CSV desde la terminal,
ejecutar el algoritmo K-GeoMIP y generar una gráfica de rendimiento.

Ejecución (desde Method2_Dynamic_Programming_Reformulation/):
    .venv\\Scripts\\python.exe interactive.py
"""

# ── Módulos de la biblioteca estándar ────────────────────────────────────────
import sys                          # Lógica: Acceso a stdout/stderr y argv del proceso.
import os                           # Lógica: Operaciones de sistema de archivos y variables de entorno.
import re                           # Lógica: Expresiones regulares para parsear nombres de CSV.
import time                         # Lógica: Medición de tiempos de ejecución (perf_counter).
import io                           # Lógica: StringIO para redirigir stdout durante el benchmark.
import contextlib                   # Lógica: redirect_stdout para silenciar salida durante benchmark.
from pathlib import Path            # Lógica: Rutas multiplataforma (Windows / Linux / macOS).
from datetime import datetime       # Lógica: Timestamp para el nombre del archivo de gráfica.

# ── Cálculo de rutas del proyecto ────────────────────────────────────────────
# Lógica: interactive.py vive en Method2_Dynamic_Programming_Reformulation/
#         Por eso parents[1] apunta a K-GeoMIP/src/ y parents[2] a K-GeoMIP/.
# Sintaxis: Path(__file__).resolve() convierte la ruta relativa a ruta absoluta del sistema.
SCRIPT_DIR  = Path(__file__).resolve().parent       # .../Method2_Dynamic_Programming_Reformulation/
GEOMIP_ROOT = Path(__file__).resolve().parents[2]   # .../K-GeoMIP/
SAMPLES_DIR = GEOMIP_ROOT / "data" / "samples"     # .../K-GeoMIP/data/samples/
OUTPUT_DIR  = SCRIPT_DIR / "interactive_output"     # Carpeta donde se guardan las gráficas

# Lógica: Agrega el directorio de trabajo al frente de sys.path para que
#         `from src.xxx import yyy` resuelva desde SCRIPT_DIR, igual que pytest.
# Sintaxis: sys.path.insert(0, str(...)) da prioridad a SCRIPT_DIR sobre otros paths.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ── Colorama ──────────────────────────────────────────────────────────────────
# Lógica: colorama habilita los códigos de color ANSI en Windows sin configuración extra.
#         autoreset=True reinicia el color al final de cada print() automáticamente.
# Sintaxis: Si no está instalado, se usan objetos "stub" con atributos que retornan "".
try:
    from colorama import Fore, Back, Style, init as _colorama_init
    _colorama_init(autoreset=True)      # Lógica: Activa la traducción ANSI en Windows.
    _HAS_COLOR = True                   # Lógica: Bandera para saber si colorama está disponible.
except ImportError:
    class _Stub:
        """Objeto fallback cuando colorama no está instalado."""
        # Lógica: __getattr__ retorna string vacío para cualquier atributo (Fore.RED, etc.)
        # Sintaxis: `_` en el argumento indica que el parámetro no se usa (convención PEP8).
        def __getattr__(self, _): return ""
    # Lógica: Asigna stubs para que el resto del código funcione sin modificaciones.
    Fore = Back = Style = _Stub()
    _HAS_COLOR = False

# ── Matplotlib ────────────────────────────────────────────────────────────────
# Lógica: manim (dependencia del proyecto) instala matplotlib como dependencia.
#         Backend "Agg" genera imágenes PNG sin necesitar ventana gráfica ni display.
# Sintaxis: Se importa con try/except para que la gráfica sea opcional, no un requisito.
try:
    import matplotlib
    matplotlib.use("Agg")               # Lógica: Debe configurarse ANTES de importar pyplot.
    import matplotlib.pyplot as plt     # Lógica: API principal de matplotlib para crear figuras.
    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False

# ── Importaciones del proyecto ────────────────────────────────────────────────
# Lógica: Se importan DESPUÉS de modificar sys.path para que resuelvan desde SCRIPT_DIR.
#         Si falla, el mensaje de error guía al usuario sobre cómo solucionar el problema.
# Sintaxis: try/except ImportError con mensaje descriptivo es mejor que dejar crashear.
try:
    from src.main import run_prueba, resolver_tpm_path
    from src.constants.models import K_MIN, K_MAX
    from src.funcs.base import ABECEDARY
    from src.funcs.format import letras_a_bits
    from src.controllers.manager import Manager
    from src.controllers.strategies.geometric import GeometricSIA
    from src.controllers.strategies.k_geometric import KGeometricSIA
    import numpy as np
    _IMPORTS_OK  = True
    _IMPORT_MSG  = ""
except ImportError as _err:
    # Lógica: Captura el error y guarda el mensaje para mostrarlo al usuario al inicio de main().
    # Sintaxis: str(_err) convierte la excepción a string legible con el motivo del fallo.
    _IMPORTS_OK  = False
    _IMPORT_MSG  = str(_err)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILIDADES DE PANTALLA
# ══════════════════════════════════════════════════════════════════════════════

def _cls():
    """Limpia la pantalla de la terminal."""
    # Lógica: cls en Windows (os.name=='nt'), clear en Unix/macOS/Linux.
    # Sintaxis: os.system() ejecuta un comando de shell nativo y retorna su código de salida.
    os.system("cls" if os.name == "nt" else "clear")


def _titulo(texto: str):
    """Imprime un título con doble línea decorativa de caja Unicode."""
    # Lógica: La línea tiene el ancho del texto más márgenes para un encuadre visual.
    # Sintaxis: '═' (U+2550) repetido n veces crea la línea doble de caja.
    ancho = len(texto) + 4
    linea = "═" * ancho
    print(f"\n{Fore.CYAN}{linea}")
    print(f"  {Fore.WHITE}{texto}{Fore.CYAN}")
    print(f"{linea}{Style.RESET_ALL}\n")


def _seccion(texto: str):
    """Imprime un separador de sección con línea simple."""
    # Lógica: Rellena con guiones hasta 60 caracteres para separación uniforme entre secciones.
    # Sintaxis: max(2, N) garantiza que siempre haya al menos 2 guiones aunque el texto sea largo.
    relleno = "─" * max(2, 58 - len(texto))
    print(f"\n{Fore.YELLOW}── {texto} {relleno}{Style.RESET_ALL}")


def _ok(msg: str):
    """Imprime un mensaje de éxito (verde con checkmark)."""
    # Lógica: ✓ indica acción completada exitosamente.
    print(f"{Fore.GREEN}  ✓  {msg}{Style.RESET_ALL}")


def _info(msg: str):
    """Imprime un mensaje informativo (cian con ℹ)."""
    print(f"{Fore.CYAN}  ℹ  {msg}{Style.RESET_ALL}")


def _warn(msg: str):
    """Imprime una advertencia (amarillo con ⚠)."""
    print(f"{Fore.YELLOW}  ⚠  {msg}{Style.RESET_ALL}")


def _err(msg: str):
    """Imprime un error (rojo con ✗)."""
    print(f"{Fore.RED}  ✗  {msg}{Style.RESET_ALL}")


def _prompt(texto: str, default: str = "") -> str:
    """Lee una línea de la terminal con prompt estilizado y valor por defecto.

    Args:
        texto:   Texto que se muestra antes del cursor de entrada.
        default: Valor que se usa si el usuario presiona Enter sin escribir nada.
    Returns:
        El string ingresado por el usuario, o `default` si el input fue vacío.
    """
    # Lógica: Muestra el valor por defecto entre corchetes para que el usuario sepa
    #         qué pasará si solo presiona Enter sin escribir.
    # Sintaxis: f-string con expresión ternaria `A if cond else B`.
    sufijo = f" {Fore.WHITE}[{default}]{Style.RESET_ALL}" if default else ""
    # Lógica: `input()` bloquea hasta que el usuario presiona Enter; .strip() elimina
    #         espacios y saltos de línea del inicio y fin del string ingresado.
    # Sintaxis: `or default` retorna default cuando valor es string vacío (falsy en Python).
    valor = input(f"{Fore.CYAN}  › {texto}{sufijo}: {Style.RESET_ALL}").strip()
    return valor or default


def _banner():
    """Muestra el banner ASCII de bienvenida del sistema."""
    # Lógica: El banner es lo primero que ve el usuario: establece contexto y sistema.
    # Sintaxis: Triple-quote f-string multilinea; los caracteres de caja son Unicode.
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  {Fore.WHITE}  K - G e o M I P   I n t e r a c t i v o{Fore.CYAN}                ║
║  {Fore.YELLOW}  K-Partición de Mínima Información (k-MIP){Fore.CYAN}               ║
║  {Fore.WHITE}  IIT — Integrated Information Theory{Fore.CYAN}                      ║
║                                                              ║
║  {Fore.WHITE}  Análisis y Diseño de Algoritmos — 2026-1{Fore.CYAN}                 ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")


# ══════════════════════════════════════════════════════════════════════════════
#  DETECCIÓN DE CSV DISPONIBLES
# ══════════════════════════════════════════════════════════════════════════════

def _detectar_csvs() -> dict:
    """Escanea las carpetas de muestras y retorna los CSV disponibles por n.

    Busca en las mismas rutas candidatas que resolver_tpm_path() en src/main.py,
    para garantizar consistencia entre lo que muestra la interfaz y lo que
    carga el algoritmo.

    Returns:
        dict[int, list[str]] mapeando número de nodos a lista de variantes.
        Ejemplo: {3: ['A', 'B'], 10: ['A'], 15: ['A', 'B']}
    """
    # Lógica: Rutas candidatas en el mismo orden de prioridad que resolver_tpm_path().
    #         Si un archivo existe en varias rutas, solo se registra una vez (primero en orden).
    # Sintaxis: Tupla de Path; el operador / de pathlib concatena segmentos de ruta.
    candidatos = (
        SCRIPT_DIR / "src" / ".samples",   # Prioridad 1: carpeta .samples dentro de src/
        SCRIPT_DIR / ".samples",            # Prioridad 2: carpeta .samples en raíz del método
        SAMPLES_DIR,                         # Prioridad 3: K-GeoMIP/data/samples/
    )
    # Lógica: Patrón regex que extrae n (número de nodos) y variante (letra A-Z) del nombre.
    #         Ejemplo: "N15B.csv" → grupo(1)="15", grupo(2)="B".
    # Sintaxis: re.compile() precompila el patrón para reutilizarlo en el loop sin recompilar.
    patron = re.compile(r"^N(\d+)([A-Z])\.csv$")
    # Lógica: dict[int → list[str]] donde la clave es n y el valor es lista de variantes.
    # Sintaxis: Inicializado vacío; se rellena con setdefault() + append() en el loop.
    encontrados: dict = {}

    for carpeta in candidatos:
        # Lógica: Ignora rutas que no existen en disco sin lanzar FileNotFoundError.
        # Sintaxis: Path.exists() retorna bool; continue salta al siguiente ciclo del for.
        if not carpeta.exists():
            continue
        # Lógica: sorted() garantiza orden alfanumérico consistente en la lista de archivos.
        # Sintaxis: glob("N*.csv") retorna generador de Path que coincidan con el patrón shell.
        for archivo in sorted(carpeta.glob("N*.csv")):
            m = patron.match(archivo.name)  # Lógica: match() ancla al inicio del nombre.
            if m:
                n_nodos  = int(m.group(1))  # Lógica: grupo 1 = número de nodos como entero.
                variante = m.group(2)        # Lógica: grupo 2 = letra variante (A, B, C...).
                lista = encontrados.setdefault(n_nodos, [])
                # Lógica: Evita duplicados si el mismo archivo existe en varias rutas candidatas.
                # Sintaxis: `if variante not in lista` es O(len(lista)) -- aceptable para listas pequeñas.
                if variante not in lista:
                    lista.append(variante)

    # Lógica: Ordena el dict por n ascendente y las variantes de cada n alfabéticamente.
    # Sintaxis: Dict comprehension con sorted() sobre .items() para ordenar por clave (n).
    return {n: sorted(vs) for n, vs in sorted(encontrados.items())}


def _mostrar_tabla_csvs(csvs: dict):
    """Imprime una tabla formateada de los CSV disponibles en disco.

    Args:
        csvs: dict {n: [variantes]} retornado por _detectar_csvs().
    """
    # Lógica: Encabezado de tabla con columnas alineadas para lectura fácil.
    # Sintaxis: {:>4} alinea a la derecha en campo de 4 chars; {:<20} a la izquierda en 20.
    print(f"\n  {Fore.WHITE}{'n':>4}  {'Variante(s)':<14}  {'Filas TPM':>12}  {'Archivo(s)'}{Style.RESET_ALL}")
    print(f"  {'─'*4}  {'─'*14}  {'─'*12}  {'─'*24}")
    for n, variantes in csvs.items():
        # Lógica: 2^n es el número de filas de la TPM (un estado inicial por fila).
        # Sintaxis: 1 << n es equivalente a 2**n usando desplazamiento de bit (más rápido).
        filas         = 1 << n
        variantes_str = "  ".join(variantes)           # Lógica: Letras separadas por espacios.
        archivos_str  = ", ".join(f"N{n}{v}.csv" for v in variantes)
        print(f"  {Fore.CYAN}{n:>4}{Style.RESET_ALL}  {Fore.WHITE}{variantes_str:<14}{Style.RESET_ALL}  {filas:>12,}  {Fore.YELLOW}{archivos_str}{Style.RESET_ALL}")


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDACIÓN DE ENTRADAS
# ══════════════════════════════════════════════════════════════════════════════

def _validar_letras(letras: str, n: int) -> tuple:
    """Valida que todas las letras corresponden a nodos válidos del sistema.

    Args:
        letras: String de letras de nodos, ej. "ACEGI" (case-insensitive).
        n:      Número de nodos del sistema.
    Returns:
        tuple[bool, str]: (True, "") si válido; (False, mensaje_error) si no.
    """
    # Lógica: Conjunto de etiquetas válidas para el sistema de n nodos.
    # Sintaxis: set() permite búsqueda O(1) en vez de O(n) con list/tuple.
    validas = set(ABECEDARY[:n])
    if not letras:                                      # Lógica: Input vacío es inválido.
        return False, "No puede estar vacío."
    letras_upper = letras.upper()
    # Lógica: Recoge las letras inválidas para mostrarlas en el mensaje de error.
    # Sintaxis: List comprehension con filtro `if c not in validas`.
    invalidas = [c for c in letras_upper if c not in validas]
    if invalidas:
        return False, f"Letra(s) inválida(s): {', '.join(set(invalidas))}. Rango: A..{ABECEDARY[n-1]}"
    # Lógica: No se permiten repeticiones -- cada nodo puede aparecer máximo una vez.
    # Sintaxis: len(set(s)) == len(s) compara el tamaño sin vs con duplicados.
    if len(set(letras_upper)) != len(letras_upper):
        return False, "No se permiten letras repetidas."
    return True, ""


def _validar_estado(estado: str) -> tuple:
    """Valida que el estado inicial es un string binario con al menos 2 bits.

    Args:
        estado: String a validar, ej. "1000000000".
    Returns:
        tuple[bool, str]: (True, "") si válido; (False, mensaje_error) si no.
    """
    if not estado:
        return False, "No puede estar vacío."
    # Lógica: all() retorna True solo si todos los caracteres son '0' o '1'.
    # Sintaxis: Generator expression `c in "01"` -- evaluación lazy con cortocircuito.
    if not all(c in "01" for c in estado):
        return False, "Solo se permiten los caracteres '0' y '1'."
    if len(estado) < 2:
        return False, "El sistema necesita al menos 2 nodos."
    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 1 — SISTEMA, ESTADO INICIAL Y VARIANTE
# ══════════════════════════════════════════════════════════════════════════════

def _paso_sistema(csvs: dict) -> tuple:
    """Guía al usuario para seleccionar el sistema (n nodos) y la variante CSV.

    Ofrece dos modos:
        1) Elegir de la lista de sistemas disponibles (menú numerado).
        2) Escribir el estado inicial directamente en bits.

    Args:
        csvs: dict {n: [variantes]} retornado por _detectar_csvs().
    Returns:
        tuple[str, str]: (estado_inicio, variante) -- estado inicial y variante elegida.
    """
    _seccion("PASO 1 de 4 — Sistema, Estado Inicial y Variante")
    print(f"\n  ¿Cómo deseas ingresar el sistema?")
    print(f"  {Fore.WHITE}1{Style.RESET_ALL})  Elegir de la lista de CSV disponibles (recomendado)")
    print(f"  {Fore.WHITE}2{Style.RESET_ALL})  Escribir el estado inicial en bits manualmente")
    print()

    while True:
        # Lógica: Loop hasta obtener opción válida; el default "1" facilita el flujo feliz.
        opcion = _prompt("Opción", default="1")
        if opcion in ("1", "2"):
            break
        _err("Ingresa 1 o 2.")

    # ── MODO LISTA ─────────────────────────────────────────────────────────────
    if opcion == "1":
        # Lógica: Genera la lista de n disponibles ordenada para el menú numerado.
        # Sintaxis: sorted() retorna nueva lista sin modificar el dict original.
        ns_disponibles = sorted(csvs.keys())
        print()
        for i, n in enumerate(ns_disponibles, start=1):
            # Lógica: Muestra archivos disponibles para que el usuario sepa qué eligir.
            archivos = ", ".join(f"N{n}{v}.csv" for v in csvs[n])
            filas    = f"({1<<n:,} filas)"    # Lógica: 2^n filas formateadas con separador de miles.
            print(f"  {Fore.WHITE}{i:>2}){Style.RESET_ALL}  {Fore.CYAN}{n:>2} nodos{Style.RESET_ALL}  —  {Fore.YELLOW}{archivos}{Style.RESET_ALL}  {filas}")
        print()

        while True:
            eleccion = _prompt(f"Elige un número (1-{len(ns_disponibles)})")
            # Lógica: isdigit() valida que la entrada sea solo dígitos antes de convertir a int.
            # Sintaxis: `1 <= int(x) <= len(lista)` verifica que el índice esté en rango.
            if eleccion.isdigit() and 1 <= int(eleccion) <= len(ns_disponibles):
                n_elegido = ns_disponibles[int(eleccion) - 1]
                break
            _err(f"Ingresa un número entre 1 y {len(ns_disponibles)}.")

        # Lógica: Estado canónico estándar del proyecto: primer nodo activo, resto inactivos.
        # Sintaxis: "1" + "0" * (n-1) construye el string en O(n); ej. n=10 → "1000000000".
        estado_inicio = "1" + "0" * (n_elegido - 1)

        # Lógica: Ofrece al usuario cambiar el estado inicial si necesita un caso específico.
        print(f"\n  Estado canónico: {Fore.WHITE}{estado_inicio}{Style.RESET_ALL}  (nodo A activo, resto inactivos)")
        cambiar = _prompt("¿Cambiar estado inicial? (s/N)", default="N").upper()
        if cambiar in ("S", "SI", "Y", "YES"):
            while True:
                nuevo = _prompt("Estado inicial (bits)", default=estado_inicio)
                valido, msg = _validar_estado(nuevo)
                if not valido:
                    _err(msg)
                    continue
                if len(nuevo) != n_elegido:
                    _err(f"Debe tener {n_elegido} bits (tienes {len(nuevo)}).")
                    continue
                estado_inicio = nuevo
                break

    # ── MODO MANUAL ─────────────────────────────────────────────────────────────
    else:
        n_elegido = None    # Lógica: Se infiere de la longitud del estado ingresado.
        print()
        _info("Escribe el estado inicial como una cadena de 0s y 1s.")
        _info("Ejemplo para 10 nodos: 1000000000  (primer nodo activo)")
        print()
        while True:
            estado_inicio = _prompt("Estado inicial (bits)", default="1000000000")
            valido, msg = _validar_estado(estado_inicio)
            if valido:
                n_elegido = len(estado_inicio)
                _ok(f"Estado: {Fore.WHITE}{estado_inicio}{Fore.GREEN}  ({n_elegido} nodos detectados)")
                break
            _err(msg)

    # ── SELECCIÓN DE VARIANTE ──────────────────────────────────────────────────
    variantes_n = csvs.get(n_elegido, [])  # Lógica: Lista de variantes para el n elegido.

    if not variantes_n:
        # Lógica: No hay CSV para este n -- la ejecución fallará más adelante con FileNotFoundError.
        _warn(f"No se encontró CSV para N={n_elegido}. La ejecución fallará al cargar la TPM.")
        _info(f"Genera el CSV con: from src.controllers.manager import Manager; Manager('{'1'+'0'*(n_elegido-1)}').generar_red({n_elegido})")
        variante = "A"      # Lógica: Valor de placeholder; resolver_tpm_path dará mensaje de error claro.

    elif len(variantes_n) == 1:
        # Lógica: Única variante disponible -- se selecciona automáticamente sin preguntar.
        variante = variantes_n[0]
        _ok(f"CSV detectado: {Fore.WHITE}N{n_elegido}{variante}.csv{Style.RESET_ALL}  (única variante disponible)")

    else:
        # Lógica: Múltiples variantes para el mismo n -- el usuario debe elegir cuál usar.
        _seccion("Variante del CSV")
        print(f"\n  Hay {Fore.WHITE}{len(variantes_n)}{Style.RESET_ALL} variantes disponibles para N={n_elegido}:")
        print()
        for i, v in enumerate(variantes_n, start=1):
            nombre_csv = f"N{n_elegido}{v}.csv"
            ruta_csv   = SAMPLES_DIR / nombre_csv
            # Lógica: Muestra el tamaño del archivo en MB para ayudar a elegir entre variantes.
            # Sintaxis: Path.stat().st_size retorna tamaño en bytes; /1e6 convierte a megabytes.
            try:
                size_mb  = ruta_csv.stat().st_size / 1_000_000
                size_str = f"~{size_mb:.1f} MB"
            except (FileNotFoundError, OSError):
                size_str = "tamaño desconocido"
            print(f"  {Fore.WHITE}{i}){Style.RESET_ALL}  {Fore.YELLOW}{nombre_csv}{Style.RESET_ALL}  ({size_str})")
        print()

        while True:
            eleccion = _prompt(f"Elige variante (1-{len(variantes_n)})", default="1")
            if eleccion.isdigit() and 1 <= int(eleccion) <= len(variantes_n):
                variante = variantes_n[int(eleccion) - 1]
                break
            _err(f"Elige un número entre 1 y {len(variantes_n)}.")

    # Lógica: Confirmación final del CSV que se cargará al ejecutar el algoritmo.
    _ok(f"Se cargará: {Fore.WHITE}N{n_elegido}{variante}.csv")
    _ok(f"Estado inicial: {Fore.WHITE}{estado_inicio}")
    return estado_inicio, variante


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 2 — ALCANCE Y MECANISMO
# ══════════════════════════════════════════════════════════════════════════════

def _paso_alcance_mecanismo(n: int) -> tuple:
    """Solicita el alcance y mecanismo con validación y ayuda contextual.

    Args:
        n: Número de nodos del sistema (longitud del estado inicial).
    Returns:
        tuple[str, str]: (alcance, mecanismo) en notación de letras mayúsculas.
    """
    _seccion("PASO 2 de 4 — Alcance y Mecanismo")
    # Lógica: Muestra las letras válidas del sistema para que el usuario sepa qué puede ingresar.
    # Sintaxis: "".join(ABECEDARY[:n]) concatena las primeras n etiquetas sin separador.
    sistema_completo = "".join(ABECEDARY[:n])
    print(f"\n  Sistema de {Fore.WHITE}{n}{Style.RESET_ALL} nodos:  {Fore.YELLOW}{sistema_completo}{Style.RESET_ALL}")
    print(f"  Rango válido: {Fore.WHITE}A{Style.RESET_ALL} .. {Fore.WHITE}{ABECEDARY[n-1]}{Style.RESET_ALL}")
    _info("Presiona Enter para usar el sistema completo como valor por defecto.")
    print()

    # ── ALCANCE ────────────────────────────────────────────────────────────────
    # Lógica: El alcance (purview) son los nodos futuros observados (t+1), columna B del Excel.
    print(f"  {Fore.CYAN}Alcance{Style.RESET_ALL} — nodos futuros observados (columna B del Excel, tiempo t+1)")
    while True:
        alcance = _prompt("Alcance", default=sistema_completo).upper()
        valido, msg = _validar_letras(alcance, n)
        if valido:
            # Lógica: Muestra la conversión letras→bits para verificación visual inmediata.
            bits_alc = letras_a_bits(alcance, n)
            _ok(f"Alcance:   {Fore.WHITE}{alcance:>{n}}{Fore.GREEN}  →  {Fore.YELLOW}{bits_alc}")
            break
        _err(msg)

    print()
    # ── MECANISMO ──────────────────────────────────────────────────────────────
    # Lógica: El mecanismo son los nodos presentes del subsistema (t), columna C del Excel.
    print(f"  {Fore.CYAN}Mecanismo{Style.RESET_ALL} — nodos presentes del subsistema (columna C del Excel, tiempo t)")
    while True:
        mecanismo = _prompt("Mecanismo", default=sistema_completo).upper()
        valido, msg = _validar_letras(mecanismo, n)
        if valido:
            bits_mec = letras_a_bits(mecanismo, n)
            _ok(f"Mecanismo: {Fore.WHITE}{mecanismo:>{n}}{Fore.GREEN}  →  {Fore.YELLOW}{bits_mec}")
            break
        _err(msg)

    return alcance, mecanismo


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 3 — NÚMERO DE PARTICIONES k
# ══════════════════════════════════════════════════════════════════════════════

def _paso_k() -> int:
    """Solicita el número de particiones k con descripción de cada opción.

    Returns:
        int: k en el rango [K_MIN, K_MAX].
    """
    _seccion("PASO 3 de 4 — Número de Particiones (k)")
    # Lógica: Tabla de descripción para que el usuario entienda qué hace cada valor de k.
    # Sintaxis: dict mapea k (int) a descripción (str); indexado directamente en el loop.
    desc = {
        2: "Bi-partición exacta    — GeoMIP (GeometricSIA), algoritmo de referencia",
        3: "Tri-partición greedy   — K-GeoMIP (KGeometricSIA), heurística LPT",
        4: "Cuad-partición greedy  — K-GeoMIP (KGeometricSIA), heurística LPT",
        5: "Quint-partición greedy — K-GeoMIP (KGeometricSIA), heurística LPT",
    }
    print()
    for k_val in range(K_MIN, K_MAX + 1):
        color = Fore.GREEN if k_val == K_MIN else Fore.WHITE
        print(f"  {Fore.CYAN}{k_val}{Style.RESET_ALL})  {color}{desc[k_val]}{Style.RESET_ALL}")
    print()
    # Lógica: Muestra la garantía matemática de la heurística LPT (Graham, 1969)
    #         para que el usuario tenga contexto sobre la calidad aproximada.
    _info("Garantía LPT (k≥3):  makespan(LPT) ≤ (4/3 − 1/(3k)) × OPT")
    print()

    while True:
        eleccion = _prompt("Valor de k", default=str(K_MIN))
        # Lógica: isdigit() verifica que la entrada sea un entero positivo antes de convertir.
        # Sintaxis: `K_MIN <= int(x) <= K_MAX` es la comparación de rango en Python (encadenada).
        if eleccion.isdigit():
            k = int(eleccion)
            if K_MIN <= k <= K_MAX:
                estrategia_str = "GeometricSIA (exacta)" if k == K_MIN else f"KGeometricSIA greedy (k={k})"
                _ok(f"k = {k}  →  Estrategia: {Fore.WHITE}{estrategia_str}")
                return k
        _err(f"k debe ser un entero entre {K_MIN} y {K_MAX}.")


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 4 — CONFIRMACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _paso_confirmar(estado_inicio: str, alcance: str, mecanismo: str, k: int, variante: str) -> bool:
    """Muestra un resumen de la configuración y pide confirmación antes de ejecutar.

    Args:
        estado_inicio, alcance, mecanismo, k, variante: Parámetros de la ejecución.
    Returns:
        bool: True si el usuario confirma, False si cancela.
    """
    _seccion("PASO 4 de 4 — Confirmar y Ejecutar")
    n          = len(estado_inicio)
    csv_nombre = f"N{n}{variante}.csv"
    # Lógica: Muestra todos los parámetros juntos para que el usuario verifique de un vistazo
    #         que la configuración es la correcta antes de lanzar el algoritmo.
    # Sintaxis: Caja de texto con caracteres de caja Unicode (┌─┐│└┘) para mejor presentación.
    print(f"""
  {Fore.CYAN}Resumen de la ejecución:{Style.RESET_ALL}

  ┌──────────────────────────────────────────────────────┐
  │  {Fore.YELLOW}Nodos (n)       :{Style.RESET_ALL}  {Fore.WHITE}{n}{Style.RESET_ALL}
  │  {Fore.YELLOW}Estado inicial  :{Style.RESET_ALL}  {Fore.WHITE}{estado_inicio}{Style.RESET_ALL}
  │  {Fore.YELLOW}Alcance (t+1)   :{Style.RESET_ALL}  {Fore.WHITE}{alcance}{Style.RESET_ALL}
  │  {Fore.YELLOW}Mecanismo (t)   :{Style.RESET_ALL}  {Fore.WHITE}{mecanismo}{Style.RESET_ALL}
  │  {Fore.YELLOW}k (particiones) :{Style.RESET_ALL}  {Fore.WHITE}{k}{Style.RESET_ALL}
  │  {Fore.YELLOW}CSV / TPM       :{Style.RESET_ALL}  {Fore.GREEN}{csv_nombre}{Style.RESET_ALL}
  └──────────────────────────────────────────────────────┘
""")
    respuesta = _prompt("¿Ejecutar? (S/n)", default="S").upper()
    # Lógica: Acepta Enter (→ "S" por default), "S", "SI", "Y" o "YES" como confirmación.
    # Sintaxis: `in (...)` comprueba pertenencia al conjunto de respuestas afirmativas.
    return respuesta in ("S", "SI", "Y", "YES")


# ══════════════════════════════════════════════════════════════════════════════
#  BENCHMARK Y GRÁFICA DE RENDIMIENTO
# ══════════════════════════════════════════════════════════════════════════════

def _benchmark(alcance: str, mecanismo: str, estado_inicio: str, variante: str) -> dict:
    """Ejecuta el algoritmo para k=2,3,4,5 y retorna tiempos y pérdidas.

    Llama directamente a las estrategias (sin run_prueba) para acceder al objeto
    Solution y obtener .perdida y .tiempo_ejecucion sin imprimir la salida completa.
    No se genera síntesis de voz porque no se llama print(solucion) (que dispara __str__).

    Args:
        alcance, mecanismo: Notación de letras (ej. "ABCDEFGHIJ").
        estado_inicio:      Bits del estado inicial (ej. "1000000000").
        variante:           Letra de la variante CSV (A, B, C...).
    Returns:
        dict {k: {"tiempo_pared": float, "tiempo_interno": float, "perdida": float}}
        para k en {K_MIN..K_MAX}. Los valores pueden ser None si hubo error.
    """
    n           = len(estado_inicio)
    condiciones = "1" * n          # Lógica: Sistema candidato completo (todos los nodos activos).
    # Lógica: Convierte letras a bits una sola vez; se reutiliza en todos los k del benchmark.
    # Sintaxis: letras_a_bits(str, int) retorna string de n bits; .upper() normaliza a mayúsculas.
    alc_bits    = letras_a_bits(alcance.upper(),   n)
    mec_bits    = letras_a_bits(mecanismo.upper(), n)

    # Lógica: Carga la TPM una sola vez para todos los k del benchmark.
    #         np.genfromtxt lee el CSV como ndarray float64 sin encabezado.
    # Sintaxis: resolver_tpm_path() lanza FileNotFoundError si el CSV no existe.
    with contextlib.redirect_stdout(io.StringIO()):  # Lógica: Silencia el print "[TPM] Usando: ..."
        tpm_path = resolver_tpm_path(estado_inicio, variante=variante)
    # Lógica: genfromtxt carga el CSV sin encabezado (skip_header=0 por defecto).
    # Sintaxis: delimiter="," indica que las columnas están separadas por coma.
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    resultados = {}
    for k in range(K_MIN, K_MAX + 1):
        # Lógica: Crea un Manager nuevo por cada k para garantizar independencia entre ejecuciones.
        # Sintaxis: Manager(estado_inicial=...) -- keyword argument explícito para legibilidad.
        config = Manager(estado_inicial=estado_inicio)
        print(f"  {Fore.CYAN}Ejecutando k={k}...{Style.RESET_ALL}", end="", flush=True)
        # Lógica: perf_counter() mide el tiempo de pared (wall-clock) con alta resolución.
        #         Es más preciso que time.time() para intervalos cortos porque no sufre
        #         ajustes del reloj del sistema (NTP, DST, etc.).
        # Sintaxis: t0 = inicio del intervalo; t1 - t0 = tiempo transcurrido en segundos.
        t0 = time.perf_counter()
        try:
            # Lógica: Redirige stdout para silenciar cualquier print interno de las estrategias
            #         durante el benchmark. La voz (TTS) no se activa porque no llamamos
            #         print(solucion) -- __str__ no se invoca, así que el Thread TTS no se lanza.
            # Sintaxis: contextlib.redirect_stdout() es un context manager estándar de Python.
            with contextlib.redirect_stdout(io.StringIO()):
                if k == K_MIN:
                    # Lógica: k=2 usa GeometricSIA (bi-partición exacta, sin heurística).
                    # Sintaxis: aplicar_estrategia() retorna un objeto Solution con .perdida y .tiempo_ejecucion.
                    estrategia = GeometricSIA(config)
                    solucion   = estrategia.aplicar_estrategia(condiciones, alc_bits, mec_bits, tpm)
                else:
                    # Lógica: k≥3 usa KGeometricSIA (heurística greedy LPT de Graham 1969).
                    # Sintaxis: keyword argument k=k coincide exactamente con la firma del método.
                    estrategia = KGeometricSIA(config)
                    solucion   = estrategia.aplicar_estrategia(condiciones, alc_bits, mec_bits, tpm, k=k)
        except Exception as exc:
            # Lógica: Captura error en una ejecución individual del benchmark sin detener las demás.
            # Sintaxis: `except Exception` captura todas las subclases, excepto SystemExit/KeyboardInterrupt.
            t1 = time.perf_counter()
            print(f"  {Fore.RED}ERROR: {exc}{Style.RESET_ALL}")
            resultados[k] = {"tiempo_pared": None, "tiempo_interno": None, "perdida": None}
            continue

        t1 = time.perf_counter()

        # Lógica: Accede a los atributos de la solución sin llamar print(solucion),
        #         lo que evita que se active el Thread de síntesis de voz (TTS).
        # Sintaxis: solucion.perdida y solucion.tiempo_ejecucion son atributos directos de Solution.
        try:
            perdida_val  = float(solucion.perdida)
        except (ValueError, TypeError, AttributeError):
            perdida_val  = None
        try:
            tiempo_int   = float(solucion.tiempo_ejecucion)
        except (ValueError, TypeError, AttributeError):
            tiempo_int   = None

        tiempo_pared = t1 - t0  # Lógica: Tiempo total de pared incluyendo setup de la estrategia.

        resultados[k] = {
            "tiempo_pared":    tiempo_pared,     # Lógica: Tiempo real medido externamente.
            "tiempo_interno":  tiempo_int,        # Lógica: Tiempo reportado por la propia Solution.
            "perdida":         perdida_val,       # Lógica: δk (EMD) -- pérdida de información.
        }
        # Lógica: Muestra el resultado en línea continuando el "Ejecutando k=X..." previo.
        t_str = f"{tiempo_pared:.4f} s"
        p_str = f"{perdida_val:.6f}" if perdida_val is not None else "N/A"
        print(f"  {Fore.GREEN}✓  {t_str}  (δ{k} = {p_str}){Style.RESET_ALL}")

    return resultados


def _generar_grafica(resultados: dict, n: int, alcance: str, mecanismo: str, variante: str):
    """Genera y guarda una gráfica de barras comparando tiempos y pérdidas por k.

    Crea dos subfiguras lado a lado:
        - Izquierda: Tiempo de ejecución (segundos) por k.
        - Derecha:   Pérdida δk (EMD) por k.

    Args:
        resultados: dict {k: {"tiempo_pared", "perdida"}} retornado por _benchmark().
        n:          Número de nodos del sistema.
        alcance, mecanismo, variante: Para el título y nombre del archivo PNG.
    Returns:
        Path del archivo PNG generado, o None si matplotlib no está disponible o hubo error.
    """
    if not _HAS_MATPLOTLIB:
        _warn("matplotlib no está disponible -- gráfica no generada.")
        return None

    # Lógica: Extrae solo los k con datos válidos (excluye los que tuvieron error).
    # Sintaxis: List comprehension con condición; r["tiempo_pared"] is not None filtra errores.
    ks       = [k for k, r in resultados.items() if r["tiempo_pared"] is not None]
    tiempos  = [resultados[k]["tiempo_pared"] for k in ks]
    perdidas = [resultados[k]["perdida"] if resultados[k]["perdida"] is not None else 0 for k in ks]

    if not ks:
        _warn("No hay datos de benchmark para graficar.")
        return None

    # Lógica: Crea la carpeta de salida si no existe; exist_ok evita error si ya existe.
    # Sintaxis: mkdir(parents=True, exist_ok=True) crea todos los directorios intermedios.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Lógica: Figura con 2 subfiguras (1 fila × 2 columnas) de 12×5 pulgadas (alta resolución).
    # Sintaxis: plt.subplots(nrows, ncols, figsize=(ancho, alto)) en pulgadas (default DPI=72).
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("#1e1e2e")   # Lógica: Fondo oscuro estilo terminal (Catppuccin Mocha).

    # Lógica: Paleta de colores por k (azul=k2, verde=k3, rojo=k4, naranja=k5).
    # Sintaxis: List comprehension extrae el color del índice `i % len(paleta)` para soporte ilimitado de k.
    paleta  = ["#89b4fa", "#a6e3a1", "#f38ba8", "#fab387"]
    colores = [paleta[i % len(paleta)] for i in range(len(ks))]
    etiq_x  = [f"k = {k}" for k in ks]   # Lógica: Etiquetas del eje X con formato "k = N".

    # ── Subfigura 1: Tiempo de ejecución ──────────────────────────────────────
    barras1 = ax1.bar(
        etiq_x,        # Eje X: etiquetas "k = 2", "k = 3", ...
        tiempos,        # Eje Y: tiempos en segundos
        color=colores,  # Lógica: Color distinto por k para diferenciar visualmente.
        width=0.5,      # Lógica: Ancho de barras (0-1); 0.5 deja espacio entre barras.
        edgecolor="white",
        linewidth=0.8,
    )
    # Lógica: Etiquetas sobre cada barra con el valor exacto de tiempo.
    # Sintaxis: ax.bar_label(barras, fmt="...", padding=N) coloca el label N pts arriba de la barra.
    ax1.bar_label(barras1, fmt="%.4f s", padding=4, color="white", fontsize=9)
    ax1.set_title("Tiempo de ejecución por k", color="white", fontsize=12, pad=10)
    ax1.set_xlabel("k  (número de particiones)", color="#a6adc8", fontsize=10)
    ax1.set_ylabel("Segundos",                  color="#a6adc8", fontsize=10)
    ax1.set_facecolor("#181825")               # Lógica: Fondo del área de la gráfica.
    ax1.tick_params(colors="white")             # Lógica: Texto de ticks en blanco para contraste.
    for spine in ax1.spines.values():
        spine.set_color("#45475a")              # Lógica: Bordes del área en gris oscuro.

    # ── Subfigura 2: Pérdida δk (EMD) ─────────────────────────────────────────
    barras2 = ax2.bar(etiq_x, perdidas, color=colores, width=0.5, edgecolor="white", linewidth=0.8)
    ax2.bar_label(barras2, fmt="%.6f", padding=4, color="white", fontsize=9)
    ax2.set_title("Pérdida dk (EMD) por k",   color="white", fontsize=12, pad=10)
    ax2.set_xlabel("k  (número de particiones)", color="#a6adc8", fontsize=10)
    ax2.set_ylabel("dk  (Earth Mover's Distance)", color="#a6adc8", fontsize=10)
    ax2.set_facecolor("#181825")
    ax2.tick_params(colors="white")
    for spine in ax2.spines.values():
        spine.set_color("#45475a")

    # ── Título general de la figura ────────────────────────────────────────────
    # Lógica: suptitle aparece encima de ambas subfiguras como título de la figura completa.
    # Sintaxis: rect=[0, 0, 1, 0.95] en tight_layout reserva el 5% superior para suptitle.
    fig.suptitle(
        f"K-GeoMIP  —  N{n}{variante}.csv  |  Alcance: {alcance}  |  Mecanismo: {mecanismo}",
        color="white", fontsize=11, fontweight="bold",
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    # ── Guardar PNG ────────────────────────────────────────────────────────────
    # Lógica: El timestamp en el nombre evita sobreescribir ejecuciones anteriores.
    # Sintaxis: strftime("%Y%m%d_%H%M%S") genera "20260615_143022" como sufijo único.
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_png = f"benchmark_N{n}{variante}_{alcance}_{mecanismo}_k{K_MIN}a{K_MAX}_{timestamp}.png"
    ruta_png   = OUTPUT_DIR / nombre_png

    # Lógica: dpi=150 genera imagen de alta resolución apta para incluir en el manual de usuario.
    # Sintaxis: bbox_inches="tight" recorta bordes blancos extra alrededor de la figura.
    plt.savefig(ruta_png, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)   # Lógica: Libera la memoria de la figura después de guardarla en disco.
    return ruta_png


# ══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Función principal de la interfaz interactiva K-GeoMIP."""
    _cls()      # Lógica: Limpia la pantalla antes de mostrar el banner para presentación limpia.
    _banner()

    # ── Verificar importaciones del proyecto ──────────────────────────────────
    # Lógica: Si las importaciones fallaron, el script no puede funcionar. Muestra un
    #         mensaje de error claro con instrucciones de solución antes de salir.
    if not _IMPORTS_OK:
        _err("No se pudieron importar los módulos del proyecto.")
        _err(f"Detalle: {_IMPORT_MSG}")
        print(f"""
  {Fore.YELLOW}Asegúrate de ejecutar este script desde la carpeta correcta:

    cd "K-GeoMIP\\src\\Method2_Dynamic_Programming_Reformulation"
    .venv\\Scripts\\python.exe interactive.py

  Si es la primera vez, instala las dependencias primero:
    .venv\\Scripts\\python.exe -m pip install -e .{Style.RESET_ALL}
""")
        sys.exit(1)

    # ── Detectar CSV disponibles ──────────────────────────────────────────────
    _seccion("CSV disponibles en disco")
    csvs = _detectar_csvs()     # Lógica: Escanea las rutas candidatas y retorna {n: [variantes]}.
    if not csvs:
        _warn("No se encontraron archivos CSV de muestras (TPM).")
        _info(f"Ruta buscada: {SAMPLES_DIR}")
        _info("Genera un CSV de prueba con:")
        _info("  from src.controllers.manager import Manager; Manager('1000000000').generar_red(10)")
    else:
        _mostrar_tabla_csvs(csvs)

    # ── PASO 1: Sistema, estado inicial y variante ────────────────────────────
    estado_inicio, variante = _paso_sistema(csvs)
    n = len(estado_inicio)     # Lógica: El número de nodos se infiere del estado inicial.

    # ── PASO 2: Alcance y mecanismo ───────────────────────────────────────────
    alcance, mecanismo = _paso_alcance_mecanismo(n)

    # ── PASO 3: k ─────────────────────────────────────────────────────────────
    k = _paso_k()

    # ── PASO 4: Confirmación ──────────────────────────────────────────────────
    if not _paso_confirmar(estado_inicio, alcance, mecanismo, k, variante):
        _info("Ejecución cancelada. Hasta pronto.")
        return

    # ── EJECUCIÓN PRINCIPAL ───────────────────────────────────────────────────
    _seccion("EJECUCIÓN")
    csv_nombre = f"N{n}{variante}.csv"
    print()
    _info(f"Cargando TPM: {Fore.WHITE}{csv_nombre}{Style.RESET_ALL} ...")
    print()

    try:
        # Lógica: Reconfigura stdout a UTF-8 para que caracteres especiales de Solution
        #         (═, ≡, φ, colores ANSI) se rendericen correctamente en Windows (CP1252).
        # Sintaxis: reconfigure() opera in-place sobre el stream existente; colorama sigue activo.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        # Lógica: run_prueba() maneja toda la lógica de conversión, carga y display del resultado.
        # Sintaxis: Keyword arguments explícitos para claridad y para evitar errores de posición.
        run_prueba(
            alcance       = alcance,
            mecanismo     = mecanismo,
            k             = k,
            estado_inicio = estado_inicio,
            variante      = variante,
        )
    except FileNotFoundError as exc:
        # Lógica: Captura el error cuando el CSV no existe y da un mensaje claro al usuario.
        _err(f"Archivo CSV no encontrado: {exc}")
        _info("Verifica que el archivo exista en K-GeoMIP/data/samples/")
        return
    except KeyboardInterrupt:
        # Lógica: El usuario presionó Ctrl+C durante la ejecución; cierre limpio.
        print()
        _warn("Ejecución interrumpida por el usuario (Ctrl+C).")
        return
    except Exception as exc:
        # Lógica: Captura cualquier otro error inesperado y muestra el traceback para debugging.
        # Sintaxis: import traceback local evita importarlo en el top-level si no se necesita.
        _err(f"Error inesperado durante la ejecución: {exc}")
        import traceback
        traceback.print_exc()
        return

    # ── GRÁFICA DE RENDIMIENTO ────────────────────────────────────────────────
    print()
    _seccion("Gráfica de Rendimiento (Opcional)")
    print()
    _info(f"Ejecuta el algoritmo para k={K_MIN},{K_MIN+1},...,{K_MAX} y compara tiempos y pérdidas.")
    if n >= 20:
        # Lógica: Advierte al usuario que el benchmark puede tardar mucho para n grandes.
        _warn(f"Para n={n} el benchmark puede tardar varios minutos. Ten paciencia.")
    print()

    hacer = _prompt(f"¿Generar gráfica de rendimiento k={K_MIN}..{K_MAX}? (S/n)", default="S").upper()

    if hacer in ("S", "SI", "Y", "YES"):
        print()
        _info("Ejecutando benchmark para todos los valores de k...")
        print()

        try:
            resultados = _benchmark(alcance, mecanismo, estado_inicio, variante)
        except FileNotFoundError as exc:
            _err(f"Error al cargar CSV para benchmark: {exc}")
            return
        except KeyboardInterrupt:
            print()
            _warn("Benchmark interrumpido por el usuario.")
            return
        except Exception as exc:
            _err(f"Error en benchmark: {exc}")
            import traceback
            traceback.print_exc()
            return

        # ── Tabla resumen del benchmark ────────────────────────────────────────
        print()
        _seccion("Resultados del Benchmark")
        print(f"\n  {Fore.WHITE}{'k':>4}  {'Tiempo pared (s)':>18}  {'Tiempo interno (s)':>20}  {'delta_k (EMD)':>14}{Style.RESET_ALL}")
        print(f"  {'─'*4}  {'─'*18}  {'─'*20}  {'─'*14}")
        for k_val, r in resultados.items():
            # Lógica: Formatea cada campo con N/A si el valor es None (hubo error).
            # Sintaxis: Expresión ternaria `A if cond else B` en cada f-string.
            tp_str = f"{r['tiempo_pared']:.4f}"    if r["tiempo_pared"]    is not None else "N/A"
            ti_str = f"{r['tiempo_interno']:.4f}"  if r["tiempo_interno"]  is not None else "N/A"
            pk_str = f"{r['perdida']:.6f}"         if r["perdida"]         is not None else "N/A"
            print(f"  {Fore.CYAN}{k_val:>4}{Style.RESET_ALL}  {tp_str:>18}  {ti_str:>20}  {pk_str:>14}")

        # ── Generar PNG ────────────────────────────────────────────────────────
        print()
        ruta_png = _generar_grafica(resultados, n, alcance, mecanismo, variante)
        if ruta_png:
            _ok(f"Gráfica guardada en:")
            print(f"\n  {Fore.WHITE}{ruta_png}{Style.RESET_ALL}\n")
            _info("Ábrela con el explorador de archivos para incluirla en el Manual de Usuario.")

    # ── CIERRE ────────────────────────────────────────────────────────────────
    print()
    print(f"{Fore.CYAN}{'═' * 64}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}K-GeoMIP — Sesión terminada.  ¡Hasta pronto!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 64}{Style.RESET_ALL}\n")


# ── Guard de ejecución ────────────────────────────────────────────────────────
# Lógica: El guard `if __name__ == "__main__"` garantiza que main() solo se ejecuta
#         cuando el script se lanza directamente (no cuando se importa como módulo).
#         Esto permite usar las funciones de este módulo desde otros scripts sin
#         disparar la interfaz interactiva automáticamente.
# Sintaxis: `__name__` es una variable especial de Python; vale "__main__" al ejecutar
#           el script y el nombre del módulo cuando se importa.
if __name__ == "__main__":
    main()
