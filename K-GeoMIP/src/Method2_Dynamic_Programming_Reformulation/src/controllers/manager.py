from dataclasses import dataclass
from pathlib import Path
import time
import os

import numpy as np

from src.models.base.application import aplicacion
from src.constants.base import (
    ABC_START,
    COLON_DELIM,
    CSV_EXTENSION,
    SAMPLES_PATH,
    RESOLVER_PATH,
)


@dataclass
class Manager:
    """
    El gestor es el encargado de en función al tamaño del estado inicial y la página asociada traer el fichero de formato CSV con las TPM's almacenadas en `.samples/` 
    para hacer una rápida depuración de los datos para la creación de sistemas.

    Args:
    ----
        - `estado_inicial` (str): Dado se manejan sistemas binarios es un número base dos de tamaño asociado a la red que se quiera cargar.
        - `pagina` (str): En la ruta de samples se tiene un literal asociado al tamaño de las redes por si se necesita añadir varias de un mismo tamaño.
        ruta_base (Path): Ruta donde se encuentran las muestras de TPMs en representación estado-nodo-on (TPM estado-nodo simplificada).

    Returns:
    -------
        Manager: Así mismo se encarga de asociar el directorio donde se mostrarán análisis de las ejecuciones, donde sea el programador haga uso del módulo de logging y profilling.
    """

    estado_inicial: str
    ruta_base: Path = Path(SAMPLES_PATH)

    def __post_init__(self) -> None:
        """Resolve sample path across legacy and current repository layouts."""
        # Lógica: La variable de entorno GEOMIP_SAMPLES_DIR permite sobrescribir la ruta
        #         de muestras sin modificar el código — útil en entornos CI/CD o servidores
        #         donde los datos están en una ruta personalizada.
        # Sintaxis: `os.getenv("VAR")` retorna el valor de la variable o None si no existe;
        #           `.expanduser()` expande `~` a la home del usuario, `.resolve()` canonicaliza.
        env_samples_dir = os.getenv("GEOMIP_SAMPLES_DIR")
        if env_samples_dir:
            env_path = Path(env_samples_dir).expanduser().resolve()
            if env_path.exists():
                self.ruta_base = env_path
                return

        # Lógica: Calcula las raíces del proyecto usando la posición del archivo actual.
        #         `parents[2]` sube 2 niveles desde manager.py → src/controllers → src → Method2_root.
        #         `parents[4]` sube 4 niveles → K-GeoMIP root donde está data/samples/.
        # Sintaxis: `Path(__file__).resolve()` obtiene la ruta absoluta del archivo actual;
        #           `.parents[n]` accede al n-ésimo ancestro de la ruta (0=padre, 1=abuelo...).
        method2_root = Path(__file__).resolve().parents[2]
        geomip_root = Path(__file__).resolve().parents[4]

        # Lógica: Lista de candidatos en orden de prioridad para encontrar las muestras.
        #         Se intenta primero src/.samples (legacy), luego .samples (alternativo),
        #         finalmente data/samples (layout actual del repositorio).
        # Sintaxis: Tupla de objetos Path construidos con el operador `/` de pathlib,
        #           que concatena segmentos de ruta de forma multiplataforma.
        candidates = (
            method2_root / "src" / ".samples",
            method2_root / ".samples",
            geomip_root / "data" / "samples",
        )

        # Lógica: Itera candidatos y usa el primero que exista en disco. El `return`
        #         temprano evita que se continúe buscando una vez encontrado el directorio.
        # Sintaxis: `.exists()` retorna True si la ruta existe (archivo o directorio);
        #           es O(1) — llamada al sistema operativo, no recorre el directorio.
        for candidate in candidates:
            if candidate.exists():
                self.ruta_base = candidate
                return

        # Lógica: Fallback: si ningún candidato existe, construye la ruta por defecto
        #         como ruta absoluta desde Method2_root para evitar rutas relativas ambiguas.
        # Sintaxis: `method2_root / self.ruta_base` concatena la raíz con el valor por
        #           defecto del campo; `.resolve()` lo convierte a ruta absoluta canónica.
        self.ruta_base = (method2_root / self.ruta_base).resolve()

    @property
    def pagina(self) -> str:
        # Lógica: Delega a la configuración global de la aplicación para obtener el sufijo
        #         de página (A, B, C...) que identifica variantes de la misma red.
        # Sintaxis: `@property` convierte el método en atributo de solo lectura accesible
        #           como `manager.pagina` sin paréntesis; `aplicacion` es el singleton global.
        return aplicacion.pagina_sample_network

    @property
    def tpm_filename(self) -> Path:
        # Lógica: Construye el nombre del archivo CSV de TPM a partir del tamaño del
        #         estado inicial (número de nodos) y la página actual.
        #         Ejemplo: estado_inicial="1000000000" → N10A.csv
        # Sintaxis: f-string con `len(self.estado_inicial)` calcula n en O(1);
        #           el operador `/` de Path concatena la ruta base con el nombre del archivo.
        return (
            self.ruta_base / f"N{len(self.estado_inicial)}{self.pagina}.{CSV_EXTENSION}"
        )

    @property
    def output_dir(self) -> Path:
        # Lógica: Genera el directorio de salida único por sistema (N+página+estado_inicial)
        #         para que cada configuración tenga su propio espacio de resultados y logs.
        # Sintaxis: f-string que interpola tres valores en la ruta; `Path(str)` convierte
        #           el string resultante a objeto Path para compatibilidad con pathlib.
        return Path(
            f"{RESOLVER_PATH}/N{len(self.estado_inicial)}{self.pagina}/{self.estado_inicial}"
        )

    def generar_red(self, dimensiones: int, datos_discretos: bool = True) -> str:
        """
        Genera una TPM (Transition Probability Matrix) en notación little-endian para un
        sistema determinista (datos_discretos=True) o probabilístico (datos_discretos=False).

        La generación se realiza en bloques (chunks) de CHUNK_SIZE filas para evitar alojar
        toda la matriz 2ⁿ×n en RAM simultáneamente. Sin esta técnica, n=25 requeriría ~800 MB
        de RAM de golpe y n=27 causaría MemoryError en máquinas estándar. Con chunks, el pico
        de RAM es O(CHUNK_SIZE × n) ≈ 4 MB independientemente de n.

        La reproducibilidad se preserva: como np.random avanza su estado interno en el mismo
        orden secuencial chunk a chunk, el archivo resultante es bit-a-bit idéntico al que se
        obtendría generando toda la matriz de una sola vez.

        Args:
            dimensiones (int): Número de nodos de la red. Determina 2ⁿ filas en la TPM.
            datos_discretos (bool): True → valores {0,1} (int8, sistema determinista).
                                    False → valores [0,1) (float64, sistema probabilístico).

        Returns:
            str | None: Nombre del archivo CSV generado (ej. "N20A.csv"),
                        o None si el usuario cancela ante el aviso de tamaño.

        Raises:
            ValueError: Si dimensiones < 1.
        """
        # Inicializa el generador pseudoaleatorio Mersenne Twister de NumPy con la semilla
        # global de la aplicación (default: 73). Garantiza que la misma semilla produzca
        # siempre la misma red, lo que hace las ejecuciones reproducibles entre sesiones.
        np.random.seed(aplicacion.semilla_numpy)

        # Guard temprano: 0 dimensiones produciría 2^0=1 fila con 0 columnas — no es TPM válida.
        # Se lanza antes de cualquier cálculo costoso para fallar rápido y con mensaje claro.
        if dimensiones < 1:
            raise ValueError("Las dimensiones deben ser positivas")

        # `1 << dimensiones` es desplazamiento bit a bit: equivale a 2**dimensiones pero
        # se evalúa en O(1) en hardware sin pasar por aritmética de punto flotante.
        # Representa el número total de estados posibles del sistema binario de n nodos.
        num_estados = 1 << dimensiones

        # Estima el tamaño del CSV resultante.
        # Fórmula: filas × columnas × bytes_por_valor / bytes_por_GB
        # Para datos discretos cada valor ocupa ~2 chars en texto ("0," o "1,") → se usa
        # 1 byte como aproximación conservadora del valor lógico subyacente (int8).
        # Para float64 el texto "0.123456," son ~10 chars; aquí se aproxima como 1 byte
        # también para la estimación de aviso, siendo la estimación levemente optimista.
        total_size_gb = (num_estados * dimensiones) / (1024**3)

        # Heurística de tiempo: ~2 segundos por GB de archivo final (incluye generación
        # numpy + escritura a disco). Es una cota superior aproximada para dar al usuario
        # una idea del orden de magnitud; no considera caché del SO ni velocidad del disco.
        estimated_time = total_size_gb * 2

        print(f"Tamaño estimado: {total_size_gb:.6f} GB")
        print(f"Tiempo estimado: {estimated_time:.1f} segundos")

        # Solicita confirmación antes de escribir archivos > 1 GB para evitar llenar el disco
        # accidentalmente. `input(...).lower()` normaliza la respuesta a minúsculas;
        # se acepta solo "s" (sí en español) — cualquier otra entrada cancela la operación.
        if total_size_gb > 1:
            if (
                input("El sistema ocupará más de 1GB. ¿Continuar? (s/n): ").lower()
                != "s"
            ):
                return None

        # Crea el directorio de muestras si aún no existe.
        # `parents=True` crea directorios intermedios; `exist_ok=True` no lanza error si ya existe.
        base_path = Path(SAMPLES_PATH)
        base_path.mkdir(parents=True, exist_ok=True)

        # Determina el sufijo de letra (A, B, C…) para nombrar el archivo nuevo.
        # Si ya existe "N20A.csv", pregunta si generar "N20B.csv", etc.
        # `chr(ord(suffix) + 1)` incrementa el carácter ASCII: 'A'→'B'→'C'…
        suffix = ABC_START
        while (base_path / f"N{dimensiones}{suffix}.{CSV_EXTENSION}").exists():
            if (
                input(
                    f"Ya existe N{dimensiones}{suffix}.{CSV_EXTENSION}. ¿Generar nueva red? (s/n): "
                ).lower()
                != "s"
            ):
                # El usuario prefiere reutilizar el archivo existente; retorna su nombre.
                return f"N{dimensiones}{suffix}.{CSV_EXTENSION}"
            suffix = chr(ord(suffix) + 1)

        # Construye los nombres definitivos del archivo una vez confirmado el sufijo.
        filename = f"N{dimensiones}{suffix}.{CSV_EXTENSION}"
        filepath = base_path / filename

        # ── Generación por chunks ────────────────────────────────────────────────────────
        """ 
        ¿QUÉ ES UN CHUNK?
          Un chunk ("trozo" en inglés) es una porción del total de datos que se genera
          y procesa de a una vez, en lugar de manejar todo el conjunto de una sola vez.
          Analogía: copiar un libro de 1M páginas copiando 100 páginas a la vez en lugar
          de intentar memorizar el libro completo antes de escribir. El resultado es
          idéntico, pero el esfuerzo simultáneo es 10 000 veces menor.
          En código: en vez de crear un array de 2^n filas en RAM (puede ser GB),
          creamos CHUNK_SIZE filas, las escribimos al disco, y repetimos hasta terminar.
        
        PROBLEMA sin chunks:
          np.random.randint(2, size=(2^n, n)) aloca TODA la matriz en RAM de golpe.
          n=25 → 2^25 × 25 bytes ≈ 800 MB en RAM; n=27 → ~3.2 GB → MemoryError.
        
        SOLUCIÓN con chunks:
          Generar e escribir bloques de CHUNK_SIZE filas sucesivamente.
          El estado interno del Mersenne Twister avanza en el mismo orden secuencial
          que si se generara todo el array de una sola vez, por lo que el CSV resultante
          es bit-a-bit idéntico al método anterior — la reproducibilidad se conserva.
        
        CHUNK_SIZE = 2^16 = 65 536 filas por lote:
          - RAM por chunk: 65 536 × n bytes ≈ 1.6 MB para n=25 (vs 800 MB sin chunks).
          - Número de chunks para n=25: 2^25 / 2^16 = 2^9 = 512 iteraciones.
          - El valor es potencia de 2 para alinear con el banco de páginas del SO (4 KB). """
          
        CHUNK_SIZE = 1 << 16  # 65 536 filas por lote (= 2^16)

        print(f"Generando y guardando '{filepath}' en chunks de {CHUNK_SIZE} filas...")
        start_time = time.time()

        # Abre el archivo en modo escritura de texto desde el principio.
        # El bloque `with` garantiza que el descriptor de archivo se cierre aunque ocurra
        # una excepción a mitad de la escritura, evitando archivos corruptos huérfanos.
        with open(filepath, "w") as f:

            # Itera sobre todos los estados del sistema en bloques de CHUNK_SIZE filas.
            # `range(0, num_estados, CHUNK_SIZE)` produce los índices de inicio de cada chunk:
            # 0, 65536, 131072, … hasta num_estados.
            for chunk_start in range(0, num_estados, CHUNK_SIZE):

                # Calcula el índice final del chunk actual.
                # `min` evita sobrepasar num_estados en el último chunk, que puede tener
                # menos de CHUNK_SIZE filas si num_estados no es múltiplo exacto de CHUNK_SIZE.
                chunk_end = min(chunk_start + CHUNK_SIZE, num_estados)

                # Número real de filas en este chunk: CHUNK_SIZE en todos menos el último.
                chunk_rows = chunk_end - chunk_start

                if datos_discretos:
                    # Genera enteros {0, 1} con distribución uniforme para el chunk actual.
                    # `dtype=np.int8` usa 1 byte por valor (rango −128…127), suficiente para {0,1},
                    # reduciendo a la mitad el uso de RAM respecto a int16 o int32.
                    chunk = np.random.randint(
                        2, size=(chunk_rows, dimensiones), dtype=np.int8
                    )
                else:
                    # Genera flotantes en [0, 1) con distribución uniforme para el chunk.
                    # float64 (8 bytes/valor) representa probabilidades de transición continuas
                    # para sistemas no deterministas (TPM estocástica por filas).
                    chunk = np.random.random(size=(chunk_rows, dimensiones))

                # Serializa el chunk al archivo de texto ya abierto.
                # Al recibir un file object en lugar de una ruta, np.savetxt escribe en la
                # posición actual del cursor (sin truncar), acumulando chunks secuencialmente.
                # `fmt="%d"` escribe enteros sin decimales; `fmt="%.6f"` escribe 6 decimales.
                # `delimiter=COLON_DELIM` separa columnas con el delimitador configurado (coma).
                np.savetxt(
                    f,
                    chunk,
                    delimiter=COLON_DELIM,
                    fmt="%d" if datos_discretos else "%.6f",
                )

        # Mide el tamaño real del archivo generado para confirmación al usuario.
        # `os.path.getsize` retorna bytes; la división entre 1024**3 convierte a gigabytes.
        file_size_gb = os.path.getsize(filepath) / (1024**3)
        print(f"Archivo guardado: {file_size_gb:.6f} GB")
        print(f"Tiempo total: {time.time() - start_time:.2f} segundos")

        return filename
