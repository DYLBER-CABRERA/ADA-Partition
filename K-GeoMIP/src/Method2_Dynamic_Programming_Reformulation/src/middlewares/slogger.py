import sys
import logging
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Any, Callable

from colorama import init, Fore, Style

from src.constants.base import LOGS_PATH


class ColorFormatter(logging.Formatter):
    """Formatter personalizado para consola con colores usando colorama."""

    # Lógica: Mapa de nivel de log a color ANSI; permite distinguir visualmente en consola
    #         DEBUG (gris), INFO (azul), WARNING (amarillo), ERROR (rojo), CRITICAL (magenta).
    # Sintaxis: Dict de int→str usando constantes de logging como claves y constantes
    #           Fore/Style de colorama como valores de código de escape ANSI.
    COLORS = {
        logging.DEBUG: Fore.LIGHTBLACK_EX,  # gris
        logging.INFO: Fore.BLUE,  # azul
        logging.WARNING: Fore.YELLOW,  # amarillo
        logging.ERROR: Fore.RED,  # rojo
        logging.CRITICAL: Fore.MAGENTA,  # magenta
        logging.FATAL: Fore.RED + Style.BRIGHT,  # rojo brillante
    }

    def __init__(self, *args, **kwargs):
        # Lógica: Llama al __init__ del Formatter padre para configurar el formato de
        #         mensaje y fecha antes de inicializar colorama.
        # Sintaxis: `super().__init__(*args, **kwargs)` reenvía todos los argumentos al padre;
        #           `*args, **kwargs` captura `fmt` y `datefmt` que se usan en el formato.
        super().__init__(*args, **kwargs)
        # Lógica: Inicializa colorama para que los códigos de escape ANSI funcionen en
        #         Windows (cmd.exe y PowerShell no los interpretan nativamente sin esto).
        # Sintaxis: `init(autoreset=True)` configura colorama para que resetee el color
        #           automáticamente al final de cada print, evitando "contagio" de color.
        init(autoreset=True)  # Inicializa colorama

    def format(self, record: logging.LogRecord) -> str:
        # Lógica: Obtiene el color ANSI para el nivel del log actual; si el nivel no está
        #         en el mapa de colores, retorna string vacío (sin color).
        # Sintaxis: `dict.get(key, default)` retorna el valor o el default si la clave
        #           no existe; `""` como default deja el texto sin color.
        color = self.COLORS.get(record.levelno, "")
        # Lógica: Guarda el nombre del nivel original antes de aplicar colores para
        #         restaurarlo después del formateo y no contaminar el record.
        # Sintaxis: `record.levelname` es el atributo string del nivel (ej: "DEBUG", "INFO");
        #           se muta temporalmente y luego se restaura.
        original_levelname = record.levelname
        # Lógica: Envuelve el nombre del nivel con los códigos de color ANSI para que
        #         aparezca coloreado en la consola.
        # Sintaxis: `f"{color}{text}{Style.RESET_ALL}"` inserta el código de color antes
        #           y el reset ANSI al final del nombre del nivel.
        record.levelname = f"{color}{original_levelname}{Style.RESET_ALL}"

        # Lógica: Delega el formateo real al Formatter padre, que aplica el template de
        #         formato definido en __init__ (ej: "%(levelname)s (%(asctime)s): %(message)s").
        # Sintaxis: `super().format(record)` llama al método format del padre con el record
        #           modificado (levelname con color ya aplicado).
        formatted = super().format(record)
        # Lógica: Restaura el nombre original del nivel en el record para evitar efectos
        #         secundarios en otros handlers que procesen el mismo record.
        # Sintaxis: Asignación directa de vuelta al string original sin colores.
        record.levelname = original_levelname
        return formatted


class SafeLogger:
    """Logger seguro/robusto para manejar cualquier tipo de entrada y caracteres especiales."""

    def __init__(self, name: str):
        # Lógica: Configura el logger con toda su estructura de handlers y directorios
        #         al momento de construir la instancia.
        # Sintaxis: `self._logger` con prefijo `_` indica uso interno; el resultado de
        #           `__setup_logger` es el logging.Logger nativo de Python.
        self._logger = self.__setup_logger(name)

    def _safe_str(self, obj: Any) -> str:
        """Convierte cualquier objeto a string de forma segura."""
        try:
            # Lógica: Para colecciones (list, tuple, set, dict) usa `str()` directamente
            #         ya que su __str__ es siempre seguro y produce output legible.
            # Sintaxis: `isinstance(obj, (type1, type2, ...))` verifica si `obj` es instancia
            #           de alguno de los tipos dados — equivalente a un OR de isinstance.
            if isinstance(obj, (list, tuple, set, dict)):
                return str(obj)
            # Lógica: Para otros objetos, codifica a UTF-8 ignorando caracteres inválidos
            #         (reemplazándolos con '?') y decodifica de vuelta a str para evitar
            #         UnicodeEncodeError en terminales con encoding no-UTF-8.
            # Sintaxis: `.encode("utf-8", errors="replace")` convierte str→bytes
            #           reemplazando caracteres no codificables; `.decode("utf-8")` regresa a str.
            return str(obj).encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            # Lógica: Captura cualquier excepción inesperada en el formateo para que el
            #         logger nunca lance excepciones y no interrumpa la ejecución principal.
            # Sintaxis: `except Exception` captura todas las excepciones derivadas de Exception;
            #           retorna un string de fallback descriptivo.
            return "[Objeto no representable]"

    def _safe_format(self, *args, **kwargs) -> str:
        """Formatea los argumentos de forma segura."""
        # Lógica: Convierte todos los argumentos posicionales a string seguro y los une
        #         con espacio, para que el mensaje sea siempre un string válido.
        # Sintaxis: Generator expression con `_safe_str` sobre `args`; `" ".join(...)` los
        #           une con espacio como separador.
        args_str = " ".join(self._safe_str(arg) for arg in args)
        if kwargs:
            # Lógica: Si hay argumentos nombrados, los formatea como "key=value" y los
            #         añade al mensaje separados por espacio.
            # Sintaxis: f-string `f"{k}={self._safe_str(v)}"` para cada par; `" ".join(...)`
            #           une todos los pares con espacio.
            kwargs_str = " ".join(f"{k}={self._safe_str(v)}" for k, v in kwargs.items())
            return f"{args_str} {kwargs_str}"
        return args_str

    def __setup_logger(self, name: str) -> logging.Logger:
        """Configura el logger con manejo de encodings y formateo personalizado."""
        # Lógica: Crea la estructura de directorios para logs: un directorio base `.logs/`,
        #         subdirectorio por fecha y subdirectorio por hora.
        # Sintaxis: `Path(LOGS_PATH)` convierte el string de ruta a objeto Path;
        #           `.mkdir(exist_ok=True)` crea el directorio sin error si ya existe.
        base_log_dir = Path(LOGS_PATH)
        base_log_dir.mkdir(exist_ok=True)

        # Lógica: Organiza logs por fecha (DD_MM_YYYY) y hora (HHhrs) para que cada
        #         sesión de análisis tenga sus propios archivos de log.
        # Sintaxis: `datetime.now().strftime(fmt)` formatea la fecha/hora actual;
        #           operador `/` de pathlib concatena segmentos de ruta.
        current_time = datetime.now()
        date_dir = base_log_dir / current_time.strftime("%d_%m_%Y")
        date_dir.mkdir(exist_ok=True)

        hour_dir = date_dir / f"{current_time.strftime('%H')}hrs"
        hour_dir.mkdir(exist_ok=True)

        # Lógica: `detailed_log_file` archiva todos los logs con timestamp completo para
        #         diagnóstico posterior; `last_log_file` guarda solo el último log de cada
        #         ejecución para acceso rápido sin buscar en el árbol de fechas.
        # Sintaxis: Operador `/` construye la ruta final concatenando directorio y nombre
        #           de archivo con extensión `.log`.
        detailed_log_file = hour_dir / f"{name}.log"
        last_log_file = base_log_dir / f"last_{name}.log"

        # Lógica: Obtiene (o crea) el logger Python con el nombre dado y limpia todos sus
        #         handlers previos para evitar duplicación de mensajes entre instancias.
        # Sintaxis: `logging.getLogger(name)` retorna el logger del registro global;
        #           `.handlers.clear()` elimina todos los handlers registrados anteriormente.
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)
        # Lógica: Deshabilita la propagación al logger raíz para que los mensajes no se
        #         impriman dos veces (una por el handler propio y otra por el logger raíz).
        # Sintaxis: `propagate = False` corta la cadena de propagación del sistema logging.
        logger.propagate = False
        logger.handlers.clear()

        # Lógica: Define dos formateadores: uno sin colores para archivos (ANSI no legible
        #         en editores de texto) y uno con colores para la consola.
        # Sintaxis: `logging.Formatter(fmt, datefmt)` configura el template; `%(asctime)s`
        #           inserta la fecha/hora, `%(levelname)s` el nivel, `%(message)s` el mensaje.
        plain_formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s %(processName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",  # Removido %f para evitar el error
        )

        # Lógica: `ColorFormatter` añade colores ANSI por nivel de log para la consola;
        #         el formato simplificado sin fecha completa es más legible en terminal.
        # Sintaxis: `ColorFormatter` hereda de `logging.Formatter` y sobreescribe `format`.
        colored_formatter = ColorFormatter(
            "%(levelname)s (%(asctime)s): %(message)s",
            datefmt="%H:%M:%S",  # Formato simplificado para la consola
        )

        # Lógica: Handler de archivo detallado: archiva todos los logs (DEBUG+) con
        #         timestamp completo en el subdirectorio de fecha/hora de esta sesión.
        # Sintaxis: `FileHandler(path, mode="w", encoding="utf-8")` abre el archivo
        #           en modo escritura (sobrescribe) con codificación UTF-8 explícita.
        detailed_file_handler = logging.FileHandler(
            detailed_log_file, mode="w", encoding="utf-8"
        )
        detailed_file_handler.setLevel(logging.DEBUG)
        detailed_file_handler.setFormatter(plain_formatter)

        # Lógica: Handler de archivo "last": guarda solo el log de la última ejecución
        #         en la raíz de `.logs/` para acceso rápido sin navegar el árbol de fechas.
        # Sintaxis: `mode="w"` sobrescribe el archivo en cada ejecución — solo el último log persiste.
        last_file_handler = logging.FileHandler(
            last_log_file, mode="w", encoding="utf-8"
        )
        last_file_handler.setLevel(logging.DEBUG)
        last_file_handler.setFormatter(plain_formatter)

        # Lógica: Handler de consola: muestra los logs en stdout con colores ANSI para
        #         diagnóstico en tiempo real durante la ejecución de análisis.
        # Sintaxis: `StreamHandler(sys.stdout)` dirige los logs a la salida estándar;
        #           `setLevel(DEBUG)` muestra todos los niveles en consola.
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            logging.DEBUG
        )  # Cambiado a DEBUG para ver todos los mensajes
        console_handler.setFormatter(colored_formatter)

        # Lógica: Registra los tres handlers en el logger para que cada mensaje se
        #         procese en paralelo por el archivo detallado, el last y la consola.
        # Sintaxis: `logger.addHandler(h)` registra el handler; el logger invoca
        #           `h.emit(record)` para cada mensaje que supere el nivel configurado.
        logger.addHandler(detailed_file_handler)
        logger.addHandler(last_file_handler)
        logger.addHandler(console_handler)

        return logger

    def set_log(self, level: int, *args, **kwargs) -> None:
        """Método genérico de logging."""
        # Lógica: Formatea los argumentos de forma segura y delega al logger nativo de Python
        #         con el nivel especificado.
        # Sintaxis: `_safe_format` convierte args/kwargs a string; `_logger.log(level, msg)`
        #           es el método genérico de logging que acepta el nivel como entero.
        message = self._safe_format(*args, **kwargs)
        self._logger.log(level, message)

    def debug(self, *args, **kwargs) -> None:
        """Log a nivel DEBUG."""
        # Lógica: Método de conveniencia que fija el nivel DEBUG para diagnóstico detallado.
        # Sintaxis: `logging.DEBUG = 10` es la constante de nivel más bajo del módulo logging.
        self.set_log(logging.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs) -> None:
        """Log a nivel INFO."""
        # Lógica: Nivel INFO para mensajes informativos generales sobre el estado del análisis.
        # Sintaxis: `logging.INFO = 20`.
        self.set_log(logging.INFO, *args, **kwargs)

    def warn(self, *args, **kwargs) -> None:
        """Log a nivel WARNING."""
        # Lógica: Nivel WARNING para situaciones inesperadas que no detienen la ejecución.
        # Sintaxis: `logging.WARNING = 30`.
        self.set_log(logging.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        """Log a nivel ERROR."""
        # Lógica: Nivel ERROR para errores que afectan la ejecución del análisis actual.
        # Sintaxis: `logging.ERROR = 40`.
        self.set_log(logging.ERROR, *args, **kwargs)

    def critic(self, *args, **kwargs) -> None:
        """Log a nivel CRITICAL."""
        # Lógica: Nivel CRITICAL para eventos críticos del pipeline (creación de sistema,
        #         candidato, subsistema); se usa para marcar hitos del análisis.
        # Sintaxis: `logging.CRITICAL = 50`; el nivel crítico activa el color magenta
        #           en ColorFormatter.
        self.set_log(logging.CRITICAL, *args, **kwargs)

    def fatal(self, *args, **kwargs) -> None:
        """Log a nivel FATAL."""
        # Lógica: Nivel FATAL para errores irrecuperables que detienen completamente el proceso.
        # Sintaxis: `logging.FATAL = logging.CRITICAL = 50`; en Python FATAL y CRITICAL
        #           son el mismo nivel numérico.
        self.set_log(logging.FATAL, *args, **kwargs)


def get_logger(name: str) -> SafeLogger:
    """Función de conveniencia para obtener una instancia del logger."""
    # Lógica: Función de factoría para crear un SafeLogger con el nombre dado;
    #         permite obtener loggers en un solo import sin instanciar directamente.
    # Sintaxis: Retorna una nueva instancia de SafeLogger; no cachea — cada llamada
    #           crea un logger nuevo (a diferencia de logging.getLogger que cachea).
    return SafeLogger(name)


# Decorador opcional para logging automático
def log_execution(logger: SafeLogger):
    def decorator(func: Callable):
        # Lógica: `@wraps(func)` preserva el nombre y docstring de la función original
        #         en el wrapper para que la introspección funcione correctamente.
        # Sintaxis: `functools.wraps(func)` es un decorador de decoradores; sin él,
        #           `func.__name__` reportaría "wrapper" en lugar del nombre real.
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Lógica: Registra el inicio y fin de la función automáticamente en DEBUG
                #         para trazar la ejecución de funciones decoradas sin modificarlas.
                # Sintaxis: `func.__name__` accede al nombre de la función original;
                #           los f-strings construyen mensajes descriptivos.
                logger.debug(f"Iniciando {func.__name__}")
                result = func(*args, **kwargs)
                logger.debug(f"Completado {func.__name__}")
                return result
            except Exception as e:
                # Lógica: Captura cualquier excepción, la registra en ERROR y la re-lanza
                #         para que el comportamiento de error sea el mismo que sin el decorador.
                # Sintaxis: `raise` sin argumentos re-lanza la excepción activa con su
                #           traceback original; `f"Error en {func.__name__}: {e}"` describe el fallo.
                logger.error(f"Error en {func.__name__}: {e}")
                raise

        return wrapper

    return decorator
