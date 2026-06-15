import time
from datetime import datetime

from pathlib import Path
from functools import wraps
from typing import Optional, Callable, Any
from pyinstrument import Profiler
from pyinstrument.renderers import HTMLRenderer
from src.models.base.application import aplicacion


from src.constants.base import (
    PROFILING_PATH,
    HTML_EXTENSION,
)


class ProfilingManager:
    """
    Gestor central de profiling que mantiene configuración y estado
    """

    def __init__(
        self,
        habilitado: bool = aplicacion.profiler_habilitado,
        dir_salida: Path = Path(PROFILING_PATH),
        intervalo: float = 0.001,
    ):
        # Lógica: Almacena si el profiling está habilitado o no. Por defecto toma el valor
        #         de `aplicacion.profiler_habilitado` (False) para que las pruebas normales
        #         no incurran en el overhead de ~73s del renderizador HTML.
        # Sintaxis: `habilitado: bool = ...` es un parámetro con valor por defecto evaluado
        #           en tiempo de definición de la clase (eager evaluation).
        self.enabled = habilitado
        # Lógica: Almacena el directorio base donde se guardarán los reportes HTML de profiling,
        #         organizado por sesión y timestamp para fácil localización.
        # Sintaxis: `dir_salida` es un objeto `Path` de pathlib; se asigna directamente.
        self.output_dir = dir_salida
        # Lógica: Almacena el intervalo de muestreo del profiler en segundos (1ms por defecto);
        #         valores más bajos dan mayor precisión pero más overhead de CPU.
        # Sintaxis: `float` en segundos; pyinstrument usa esto como `interval` del Profiler.
        self.interval = intervalo
        # Lógica: Almacena el nombre de la sesión actual para construir las rutas de salida;
        #         None indica que no hay sesión activa.
        # Sintaxis: `Optional[str]` indica que puede ser str o None; se inicializa como None.
        self.current_session: Optional[str] = None
        # Lógica: Crea el directorio de profiling si el profiler está habilitado,
        #         evitando errores al intentar guardar reportes en directorios inexistentes.
        # Sintaxis: Llamada al método privado; en Python los métodos `_nombre` son convención
        #           de "uso interno" pero accesibles desde fuera (no hay name mangling).
        self._setup_directories()

    def _setup_directories(self) -> None:
        """Prepara estructura de directorios para resultados"""
        # Lógica: Solo crea el directorio si el profiling está habilitado; si está deshabilitado
        #         no tiene sentido crear carpetas que nunca se usarán.
        # Sintaxis: `self.output_dir.mkdir(parents=True, exist_ok=True)` crea la ruta completa
        #           recursivamente sin error si ya existe — equivalente a `mkdir -p`.
        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, session_name: str) -> None:
        # Lógica: Abre una nueva sesión de profiling creando un subdirectorio con timestamp
        #         para agrupar todos los reportes HTML de una misma ejecución de red.
        # Sintaxis: `if self.enabled` es la guarda; sin ella se crearían directorios vacíos
        #           en cada análisis aunque el profiling esté deshabilitado.
        if self.enabled:
            # Lógica: Genera un timestamp legible en formato DD_MM_YYYY/HHhrs para organizar
            #         los reportes por fecha y hora en el sistema de archivos.
            # Sintaxis: `datetime.now().strftime(fmt)` formatea la fecha/hora actual;
            #           los "/" en el formato crean subdirectorios anidados en la ruta.
            # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamp = datetime.now().strftime("%d_%m_%Y/%Hhrs")
            # Lógica: Construye la ruta de la sesión combinando el directorio base,
            #         el nombre de sesión (ej: "NET10A") y el timestamp.
            # Sintaxis: Operador `/` de pathlib concatena segmentos de ruta de forma
            #           multiplataforma — equivalente a os.path.join en todos los OS.
            session_path = self.output_dir / session_name / timestamp
            session_path.mkdir(parents=True, exist_ok=True)
            # Lógica: Almacena la ruta de la sesión como string relativo al output_dir
            #         para construir rutas de salida individuales por análisis.
            # Sintaxis: `.relative_to(base)` retorna la parte de la ruta después de `base`;
            #           `str(path)` convierte el objeto Path a string.
            self.current_session = str(session_path.relative_to(self.output_dir))

    def get_output_path(self, name: str, format: str) -> Path:
        """Genera ruta de salida para un perfil específico"""
        # Lógica: Si no hay sesión activa (profiler no inició sesión), usa "default" como
        #         nombre de directorio para no perder reportes de ejecuciones sin sesión.
        # Sintaxis: `self.current_session or "default"` usa el operador `or` de Python;
        #           retorna el segundo operando si el primero es falsy (None o "").
        session_dir = self.current_session or "default"
        # Lógica: Construye la ruta completa del archivo de reporte combinando el directorio
        #         de salida, la sesión, el nombre del análisis y la extensión del formato.
        # Sintaxis: `f"{name}.{format}"` construye el nombre del archivo con la extensión;
        #           el operador `/` de pathlib encadena todos los segmentos.
        return self.output_dir / session_dir / f"{name}.{format}"


class ProfilerContext:
    """
    Contexto para medición de una función específica
    """

    def __init__(
        self,
        manager: ProfilingManager,
        name: str,
        context: dict,
    ):
        # Lógica: Almacena la referencia al ProfilingManager para acceder a la configuración
        #         (habilitado, output_dir, interval) y construir las rutas de salida.
        # Sintaxis: Asignación directa de atributo de instancia; `manager` es el gestor
        #           global `profiler_manager` en todos los usos del proyecto.
        self.manager = manager
        # Lógica: Almacena el nombre del análisis para usarlo como nombre del archivo HTML
        #         de reporte de profiling generado en __exit__.
        # Sintaxis: String plano; se interpola en el f-string de la ruta de salida.
        self.name = name
        # Lógica: Almacena el contexto adicional del análisis (tipo de estrategia, args)
        #         para enriquecer los metadatos del reporte de profiling.
        # Sintaxis: `dict` con claves como TYPE_TAG, "args", "kwargs" aportadas por el
        #           decorador @profile al construir ProfilerContext.
        self.context = context
        # Lógica: `start_time` se inicializa en None y se asigna en __enter__ para medir
        #         la duración total del bloque perfilado.
        # Sintaxis: `self.start_time = None` como centinela; se sobreescribe en __enter__.
        self.start_time = None
        # Lógica: Crea el Profiler de pyinstrument solo si el profiling está habilitado,
        #         evitando el overhead de instanciar el profiler en ejecuciones normales.
        # Sintaxis: Operador ternario `None if not enabled else Profiler(...)`;
        #           `async_mode="disabled"` deshabilita el soporte de asyncio (no necesario aquí).
        self.profiler = (
            None
            if not manager.enabled
            else Profiler(interval=manager.interval, async_mode="disabled")
        )

    def __enter__(self):
        # Lógica: Al entrar al bloque `with`, inicia la medición de tiempo y el profiler
        #         si el profiling está habilitado.
        # Sintaxis: `__enter__` es el protocolo del context manager; `return self` permite
        #           usar `as` en el `with` para acceder al contexto (aunque no se usa aquí).
        if self.manager.enabled:
            # Lógica: `time.perf_counter()` usa el reloj de alta resolución del sistema
            #         para medir duraciones con mayor precisión que `time.time()`.
            # Sintaxis: `perf_counter()` retorna float en segundos; la diferencia con
            #           el valor en __exit__ da la duración del bloque.
            self.start_time = time.perf_counter()
            self.profiler.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Lógica: Si el profiling está deshabilitado, sale inmediatamente sin procesar nada;
        #         el bloque `with` se comporta como si no existiera.
        # Sintaxis: `return` sin valor en __exit__ deja que las excepciones propaguen
        #           normalmente (no las suprime).
        if not self.manager.enabled:
            return

        # Lógica: Detiene el profiler y calcula la duración total del bloque perfilado.
        # Sintaxis: `profiler.stop()` finaliza la captura de muestras de pyinstrument;
        #           `perf_counter() - start_time` da la duración en segundos.
        self.profiler.stop()
        duration = time.perf_counter() - self.start_time

        # Lógica: Genera el reporte HTML interactivo con timeline completo del análisis
        #         y lo guarda en la ruta de la sesión actual.
        # Sintaxis: `HTMLRenderer(show_all=True, timeline=True)` genera el reporte HTML
        #           con todas las funciones y vista de línea de tiempo activadas.
        html_path = self.manager.get_output_path(f"{self.name}", HTML_EXTENSION)
        with open(html_path, "w") as f:
            f.write(
                self.profiler.output(
                    renderer=HTMLRenderer(show_all=True, timeline=True)
                )
            )


# Lógica: Instancia global del gestor de profiling creada al importar el módulo.
#         Al ser módulo Python, esta instancia es compartida en todo el proceso —
#         todos los @profile importan el mismo `profiler_manager`.
# Sintaxis: Instanciación a nivel de módulo; Python cachea el módulo tras el primer
#           import, garantizando que `profiler_manager` sea el mismo objeto en todo el proceso.
profiler_manager = ProfilingManager()


def profile(name: Optional[str] = None, context: Optional[dict] = None) -> Callable:
    """
    Decorador para perfilar funciones

    Args:
        name: Nombre personalizado para el perfil
        context: Información adicional de contexto
    """

    def decorator(func: Callable) -> Callable:
        # Lógica: `@wraps(func)` preserva el nombre, docstring y atributos de la función
        #         original en el wrapper, evitando que el decorador los oculte.
        # Sintaxis: `functools.wraps` es un decorador de decoradores; permite que
        #           `func.__name__` y `func.__doc__` sean accesibles en el wrapper.
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Lógica: Si el profiling está deshabilitado, llama directamente a la función
            #         sin overhead alguno — el decorador se vuelve transparente.
            # Sintaxis: `*args, **kwargs` captura todos los argumentos posicionales y nombrados
            #           para reenviarlos a `func` sin modificación.
            if not profiler_manager.enabled:
                return func(*args, **kwargs)

            # Lógica: Usa el nombre personalizado si se proporcionó, o el nombre de la función
            #         decorada como fallback para identificar el reporte HTML.
            # Sintaxis: `name or func.__name__` usa el operador `or`; retorna `func.__name__`
            #           si `name` es None o string vacío.
            profile_name = name or func.__name__
            # Lógica: Combina el contexto del decorador con los args/kwargs de la llamada
            #         para enriquecer los metadatos del reporte de profiling.
            # Sintaxis: `{**(context or {}), ...}` desempaqueta el dict de contexto y añade
            #           las claves "args" y "kwargs" con sus representaciones string.
            profile_context = {
                **(context or {}),
                "args": str(args),
                "kwargs": str(kwargs),
            }

            # Lógica: Envuelve la ejecución de la función en un ProfilerContext para medir
            #         su tiempo de ejecución y generar el reporte HTML al salir.
            # Sintaxis: `with ProfilerContext(...) as ctx:` usa el protocolo context manager;
            #           __enter__ inicia el profiler y __exit__ lo detiene y guarda el reporte.
            with ProfilerContext(
                profiler_manager,
                profile_name,
                profile_context,
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator
