from src.constants.base import ACTIVOS, INACTIVOS
from src.models.enums.distance import MetricDistance
from src.models.enums.notation import Notation


class Application:
    """
    La clase aplicación es un singleton utilizado para la obtención y configuración de parámetros.
    """

    def __init__(self) -> None:
        # Lógica: Inicializa la configuración global del sistema con valores por defecto.
        #         `pagina_sample_network` = "A" selecciona la primera variante de cada red.
        #         `semilla_numpy` = 73 garantiza reproducibilidad en la generación de redes.
        #         `notacion` = LIL_ENDIAN porque el proyecto usa representación little-endian
        #         para indexar estados binarios (bit menos significativo primero).
        #         `modo_estados` = ACTIVOS indica que se trabaja con estados activos (valor 1).
        #         `distancia_metrica` = EMD_EFECTO es la métrica por defecto del análisis IIT.
        # Sintaxis: Asignaciones directas de atributo de instancia; `.value` extrae el string
        #           del enum para almacenarlo como string plano en lugar del enum completo.
        self.pagina_sample_network: str = "A"
        self.semilla_numpy = 73
        self.notacion: str = Notation.LIL_ENDIAN.value
        self.modo_estados = ACTIVOS
        self.distancia_metrica = MetricDistance.EMD_EFECTO.value
        # Lógica: El profiler genera reportes HTML interactivos con timeline por cada llamada
        #         a aplicar_estrategia. Está deshabilitado por defecto porque agrega ~73s
        #         de overhead de renderizado por prueba, siendo el cuello de botella dominante
        #         al correr múltiples pruebas en run_10A_k.py.
        # Sintaxis: `False` deshabilita el profiler; cambiar a `True` activa los reportes HTML
        #           en review/profiling/ usando pyinstrument con timeline=True.
        self.profiler_habilitado = False

    def set_notacion(self, tipo: Notation):
        """ Lógica: Permite cambiar la notación de indexación en tiempo de ejecución.
                Afecta cómo se interpretan los índices de estados en todo el sistema.
        Sintaxis: `.value` extrae el string del enum Notation para almacenarlo como str. """
        self.notacion = tipo

    def set_distancia(self, tipo: MetricDistance):
        """ Lógica: Permite cambiar la métrica de distancia usada para calcular la pérdida
                φ entre distribuciones. Afecta a todas las estrategias del sistema.
        Sintaxis: `tipo` es un valor del enum MetricDistance; `.value` lo convierte a str. """
        self.distancia_metrica = tipo

    def set_estados_activos(self):
        """ Lógica: Configura el sistema para trabajar con estados activos (valor=1).
                Determina qué cara del hipercubo se analiza en el condicionamiento.
        Sintaxis: `ACTIVOS = True` es la constante importada de base.py. """
        self.modo_estados = ACTIVOS

    def set_estados_inactivos(self):
        """ Lógica: Configura el sistema para trabajar con estados inactivos (valor=0).
                Determina qué cara del hipercubo se analiza en el condicionamiento.
        Sintaxis: `INACTIVOS = False` es la constante importada de base.py. """
        self.modo_estados = INACTIVOS


""" Lógica: Instancia singleton de Application creada al importar el módulo.
        Al ser un módulo Python, esta instancia es compartida globalmente en
        el proceso — cualquier import de `aplicacion` accede al mismo objeto.
Sintaxis: Instanciación a nivel de módulo; Python cachea el módulo después del
          primer import, garantizando que `aplicacion` sea el mismo objeto en todo el proceso. """
aplicacion = Application()
