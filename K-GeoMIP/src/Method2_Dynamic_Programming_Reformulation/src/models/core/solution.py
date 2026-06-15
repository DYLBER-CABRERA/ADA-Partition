from colorama import init, Fore, Style
import pyttsx3
from pyttsx3.engine import Engine
from pyttsx3.voice import Voice
import numpy as np
from threading import Thread
from typing import Optional

from src.constants.base import FLOAT_ZERO
from src.models.base.application import aplicacion

# Lógica: colorama.init() debe llamarse una vez antes de usar colores ANSI en Windows.
#         Sin esta llamada, los códigos de escape de color no se renderizan en la consola.
# Sintaxis: `init()` sin argumentos activa el modo de autoreset implícito de colorama;
#           opera en el módulo globalmente, no por instancia.
init()


class Solution:
    """
    Clase Solution para representar y visualizar soluciones del sistema IIT.

    Esta clase maneja la representación, visualización y anunciación por voz de las soluciones
    encontradas durante el análisis de Integrated Information Theory (IIT). Proporciona
    funcionalidades para mostrar distribuciones de probabilidad, particiones del sistema
    y el valor φ (phi|small phi) asociado a la pérdida de información.

    Args:
    ----
        estrategia (str):
            La estrategia utilizada para la resolución del problema.

        perdida (float):
            El valor φ que representa la pérdida de información en el sistema.
            Este valor cuantifica la diferencia entre la distribución del subsistema
            y la distribución de la partición.

        distribucion_subsistema (np.ndarray):
            Array que representa la distribución de probabilidad del subsistema completo.
            Contiene las probabilidades de cada estado posible en el espacio del subsistema.

        distribucion_particion (np.ndarray):
            Array que representa la distribución de probabilidad de la partición.
            Contiene las probabilidades de cada estado en el espacio de la partición
            que minimiza la información integrada.

        particion (str):
            Representación en formato string de la mejor partición encontrada.
            Utiliza notación matemática para mostrar la estructura de la partición.

        hablar (bool, opcional):
            Si es True, anuncia la solución encontrada usando síntesis de voz.
            Por defecto es True.

        voz (Optional[str], opcional):
            Identificador específico de la voz a utilizar para la síntesis.
            Si no se especifica, se busca automáticamente una voz en español.

    Attributes:
    ----------
        perdida (float):
            El valor φ de la solución.

        distribucion_subsistema (np.ndarray):
            La distribución de probabilidad del subsistema.

        distribucion_particion (np.ndarray):
            La distribución de probabilidad de la partición.

        particion (str):
            La representación de la mejor partición.

        id_voz (Optional[str]):
            El identificador de la voz seleccionada para la síntesis.

    Examples:
    --------
    >>> # Crear una solución básica
    >>> solucion = Solution(
    ...     perdida=0.25,
    ...     distribucion_subsistema=np.array([0.0, 1.0, 0.0, 0.0]),
    ...     distribucion_particion=np.array([0.0, 0.75, 0.0, 0.25]),
    ...     particion="⎛ A,C ⎞⎛ B ⎞
    ...                ⎝a,b,c⎠⎝ ∅ ⎠"
    ... )
    >>> print(solucion)  # Muestra la solución formateada con colores

    >>> # Crear una solución sin anuncio por voz
    >>> solucion_silenciosa = Solution(
    ...     perdida=0.25,
    ...     distribucion_subsistema=np.array([0.0, 1.0, 0.0, 0.0]),
    ...     distribucion_particion=np.array([0.0, 0.75, 0.0, 0.25]),
    ...     particion="⎛ A,C ⎞⎛ B ⎞
    ...                ⎝a,b,c⎠⎝ ∅ ⎠",
    ...     hablar=False
    ... )
    """

    def __init__(
        self,
        estrategia: str,
        perdida: float,
        distribucion_subsistema: np.ndarray,
        distribucion_particion: np.ndarray,
        particion: str,
        tiempo_total: float = FLOAT_ZERO,
        hablar: bool = True,
        voz: Optional[str] = None,
    ) -> None:
        """
        Inicializa una nueva instancia de Solution.
        Consultar la documentación de la clase para detalles de los parámetros.
        """
        # Lógica: Almacena todos los atributos de la solución para su posterior visualización
        #         y uso por parte de estrategias que calculan tiempos y particiones.
        # Sintaxis: Asignaciones directas de atributo de instancia vía `self.`; el parámetro
        #           `tiempo_total` se almacena con nombre distinto (`tiempo_ejecucion`) para
        #           mantener la interfaz pública coherente con el resto del sistema.
        self.estrategia = estrategia
        self.perdida = perdida
        self.distribucion_subsistema = distribucion_subsistema
        self.distribucion_particion = distribucion_particion
        self.particion = particion
        self.tiempo_ejecucion = tiempo_total
        self.id_voz = voz
        self.hablar = hablar

    def __obtener_voz_espanol(self, motor: Engine) -> Optional[str]:
        """
        Busca y obtiene un identificador de voz en español del sistema.

        Esta función implementa un sistema de prioridades para seleccionar
        la mejor voz disponible en español, priorizando voces específicas
        de diferentes regiones hispanohablantes.

        Args:
        ----
            motor:
                Instancia del motor de síntesis de voz pyttsx3.Engine.

        Returns:
        -------
            Optional[str]:
                El identificador de la voz seleccionada, o None si no se
                encuentra ninguna voz.

        Notes:
        -----
            El orden de prioridad es:
            1. Sabina (México)
            2. Helena (España)
            3. Cualquier voz con "spanish" en el nombre
            4. Cualquier voz con "español" en el nombre
            5. Cualquier voz con "es-" en el identificador
            6. Primera voz disponible si no se encuentra ninguna en español
        """
        # Lógica: Obtiene la lista de todas las voces instaladas en el sistema operativo.
        #         La propiedad "voices" de pyttsx3 retorna una lista de objetos Voice con
        #         atributos name, id, languages, gender, age.
        # Sintaxis: `motor.getProperty("voices")` es la API de pyttsx3 para acceder a
        #           propiedades del motor TTS; retorna list[Voice] con anotación explícita.
        voces: list[Voice] = motor.getProperty("voices")

        # Lógica: Lista de tuplas (nombre_buscado, región) que define el orden de prioridad
        #         para seleccionar la voz. Voces concretas (Sabina, Helena) tienen prioridad
        #         sobre las genéricas ("spanish", "español", "es-").
        #         `None` en región indica que cualquier variante del idioma es aceptable.
        # Sintaxis: Lista de tuplas de 2 elementos; el orden importa porque se itera en secuencia
        #           y se retorna al primer match — comportamiento de "primera coincidencia gana".
        prioridades = [
            ("sabina", "méxico"),
            ("helena", "españa"),
            ("spanish", None),
            ("español", None),
            ("es-", None),
        ]

        # Lógica: Búsqueda exhaustiva con prioridades: para cada criterio de prioridad,
        #         itera todas las voces disponibles buscando coincidencia en nombre o id.
        #         El doble bucle garantiza que la prioridad externa (lista prioridades)
        #         domine sobre el orden de las voces del sistema.
        # Sintaxis: Bucles for anidados; `.lower()` normaliza a minúsculas para comparación
        #           case-insensitive; `in` sobre string verifica substring.
        for nombre_buscado, region in prioridades:
            for voz in voces:
                nombre_voz = voz.name.lower()
                id_voz = voz.id.lower()

                # Lógica: Verifica coincidencia en nombre O en id de la voz, y opcionalmente
                #         también en la región. Si region es None, cualquier variante sirve.
                # Sintaxis: Operadores `or` e `in` encadenados; `is None` comprueba identidad
                #           con None (más correcto que `== None` para valores opcionales).
                if nombre_buscado in nombre_voz or nombre_buscado in id_voz:
                    if region is None or region in nombre_voz:
                        return voz.id

        # Lógica: Fallback: si ningún criterio de prioridad coincide, retorna la primera voz
        #         disponible para garantizar que siempre haya síntesis de voz funcional.
        #         Si no hay voces instaladas, retorna None y se silencia el motor.
        # Sintaxis: Operador ternario `A if cond else B`; `voces[0].id` accede al id de la
        #           primera voz; `if voces` evalúa si la lista no está vacía (truthy check).
        return voces[0].id if voces else None

    def __anunciar_solucion(self) -> None:
        """
        Anuncia la solución encontrada usando síntesis de voz en español.

        Esta función configura y utiliza el motor de síntesis de voz para anunciar de forma audible que se ha encontrado una solución, incluyendo el valor φ calculado.

        La función se ejecuta en un hilo separado para no bloquear la ejecución principal del programa mientras se realiza la síntesis de voz.

        Notes:
        -----
            - Utilizar una velocidad de habla más lenta (150) para mejor comprensión
            - Se establece el volumen al 90% por defecto
            - Maneja excepciones de forma silenciosa para no interrumpir la ejecución
        """
        try:
            # Lógica: Inicializa el motor TTS del sistema operativo. En Windows usa SAPI5,
            #         en macOS usa NSSpeechSynthesizer, en Linux usa espeak.
            # Sintaxis: `pyttsx3.init()` sin argumentos selecciona automáticamente el backend
            #           disponible en el SO; retorna un objeto Engine.
            motor = pyttsx3.init()

            # Lógica: Si no se especificó una voz explícita al crear la solución,
            #         busca automáticamente la mejor voz en español disponible.
            # Sintaxis: `self.id_voz or self.__obtener_voz_espanol(motor)` usa cortocircuito
            #           de `or` — evalúa el lado derecho solo si `self.id_voz` es falsy (None).
            id_voz = self.id_voz or self.__obtener_voz_espanol(motor)
            if id_voz:
                motor.setProperty("voice", id_voz)

            # Lógica: Configura velocidad (rate=150 palabras/min, más lento que default 200)
            #         y volumen al 90% para garantizar claridad en el anuncio.
            # Sintaxis: `motor.setProperty(key, value)` es la API de pyttsx3 para configurar
            #           propiedades del motor TTS antes de sintetizar.
            motor.setProperty("rate", 150)
            motor.setProperty("volume", 0.9)

            # Lógica: Construye el mensaje de voz distinguiendo entre soluciones con pérdida
            #         positiva (informa el valor φ) y sin pérdida (informa que el sistema
            #         es irreducible con φ=0).
            # Sintaxis: Concatenación de f-string con expresión ternaria `A if cond else B`;
            #           `:.2f` formatea el float con 2 decimales para pronunciación natural.
            mensaje = f"Solución encontrada con {self.estrategia}." + (
                f"El valor de fi es de {self.perdida:.2f}"
                if self.perdida > FLOAT_ZERO
                else "No hubo pérdida."
            )
            # Lógica: `say()` encola el texto para síntesis; `runAndWait()` bloquea hasta
            #         completar la síntesis. Deben llamarse en este orden específico.
            # Sintaxis: Métodos del objeto Engine de pyttsx3; `runAndWait()` es bloqueante
            #           — por eso esta función se ejecuta en un Thread separado (ver __str__).
            motor.say(mensaje)
            motor.runAndWait()
        except Exception as e:
            # Lógica: Captura silenciosamente cualquier error del motor TTS para que un
            #         fallo en la síntesis de voz nunca interrumpa el flujo del análisis.
            # Sintaxis: `except Exception` captura todas las subclases excepto BaseException
            #           (SystemExit, KeyboardInterrupt); el print mantiene visibilidad del error.
            print(f"Error al inicializar el motor de voz: {e}")

    def __str__(self) -> str:
        """
        Genera una representación en string formateada y coloreadita de la solución.

        Returns:
        -------
            str:
                Representación visual de la solución que incluye:
                - Valor φ en verdecito
                - Distribuciones del subsistema y partición
                - Mejor partición encontrada en magenta
                - Elementos decorativos en cyan

        Notes:
        -----
            Utiliza la biblioteca colorama para el formato de colores, permitiedo una visualización clara por terminal.
        """
        # Lógica: Separadores visuales de doble y triple línea para delimitar secciones
        #         del output en terminal, mejorando la legibilidad del resultado.
        # Sintaxis: `"═" * 50` repite el carácter Unicode 50 veces — operador `*` sobre str
        #           genera la cadena resultante en O(n).
        bilinea = "═" * 50
        trilinea = "≡" * 50

        def formatear_distribucion(
            distribucion: np.ndarray,
            evitar_desbordamiento=True,
        ):
            # Lógica: Formatea un array de probabilidades con colores: valores positivos en
            #         blanco (visibles) y ceros en gris (menos prominentes). Limita la salida
            #         a 64 valores para evitar desbordamiento visual en subsistemas grandes.
            # Sintaxis: Función anidada (closure) con acceso al scope externo de __str__;
            #           `distribucion.size` retorna el total de elementos del NDArray.
            rango = distribucion.size
            mensaje_desborde = ""
            if evitar_desbordamiento:
                # Lógica: Límite de 64 valores mostrados — suficiente para n≤6 (2^6=64).
                #         Para n>6, muestra los primeros 64 e indica cuántos quedan.
                # Sintaxis: `excedente = rango - LIMITE` calcula cuántos valores se omiten;
                #           solo se actualiza `rango` si hay excedente, preservando el original.
                LIMITE = 64
                excedente = rango - LIMITE
                if excedente > 0:
                    mensaje_desborde = f" {excedente} valores más.."
                    rango = LIMITE

            # Lógica: Genera la representación coloreada de cada valor de probabilidad.
            #         Valores > 0 en blanco brillante; valores 0 en gris con "0." abreviado
            #         para reducir el ancho visual de los ceros (que suelen ser mayoría).
            # Sintaxis: Generator expression dentro de `" ".join()` — cada iteración produce
            #           un string con código de color ANSI. `:.4f` formatea a 4 decimales.
            datos = " ".join(
                f"{Fore.WHITE}{distribucion[idx]:.4f}"
                if distribucion[idx] > 0
                else f"{Fore.LIGHTBLACK_EX}0."
                for idx in range(rango)
            )
            return f"[ {datos}{mensaje_desborde} {Fore.WHITE}]"

        # Lógica: Lanza la síntesis de voz en un Thread daemon separado para no bloquear
        #         el retorno del string. El Thread termina naturalmente cuando el proceso principal acaba.
        # Sintaxis: `Thread(target=func)` crea un hilo que ejecuta `func` sin argumentos;
        #           `.start()` lo lanza sin bloquear el hilo llamante.
        if self.hablar:
            voz = Thread(target=self.__anunciar_solucion)
            voz.start()

        # Lógica: Pyphi maneja sus propias distribuciones (no marginales), por lo que el
        #         label "marginal" solo aplica a las estrategias propias (Geometric, KGeometric).
        # Sintaxis: Comparación de string con `==`; operador ternario selecciona el label.
        es_pyphi = self.estrategia == "Pyphi"
        tipo_distribucion = "" if es_pyphi else "marginal"

        # Lógica: Precomputa las tres representaciones de tiempo (horas, minutos, segundos)
        #         a partir del tiempo total en segundos para mostrar en unidades convenientes.
        # Sintaxis: Desempaquetado de tupla en una sola línea con 3 variables; cada elemento
        #           es un f-string con formato float distinto (horas:.2f, minutos:.1f, segundos:.4f).
        tiempo_h, tiempo_m, tiempo_s = (
            f"{self.tiempo_ejecucion/3600:.2f}",
            f"{self.tiempo_ejecucion/60:.1f}",
            f"{self.tiempo_ejecucion:.4f}",
        )
        # Lógica: f-string multilínea que ensambla el output final con secciones coloreadas.
        #         El orden es: separador, estrategia, métrica, notación, distribuciones,
        #         partición, pérdida φ, tiempos de ejecución.
        # Sintaxis: `f"""..."""` permite multilínea con interpolaciones; las constantes
        #           de colorama (Fore.*, Style.*) se interpolan como strings ANSI inline.
        return f"""{Fore.CYAN}{bilinea}

{Fore.RED}{self.estrategia} fue la estrategia de solucion.

{Fore.BLUE}Distancia métrica utilizada:
{Fore.WHITE}{aplicacion.distancia_metrica}
{Fore.BLUE}Notación utilizada en indexación:
{Fore.WHITE}{aplicacion.notacion}

{Fore.YELLOW}Distribucion {tipo_distribucion} del Subsistema:
{Style.RESET_ALL}{formatear_distribucion(self.distribucion_subsistema)}
{Fore.YELLOW}Distribucion {tipo_distribucion} de la Partición:
{Style.RESET_ALL}{formatear_distribucion(self.distribucion_particion)}

{Fore.YELLOW}Mejor Bi-Partición:
{Fore.MAGENTA}{self.particion}
{Fore.GREEN}Perdida mínima ( φ ) = {self.perdida:.4f}

{Fore.BLUE}Tiempos de ejecución:
{Fore.WHITE}Horas: {tiempo_h} = Minutos: {tiempo_m} = Segundos: {tiempo_s}

{Fore.CYAN}{trilinea}{Style.RESET_ALL}"""

    def __repr__(self) -> str:
        """
        Implementa la representación oficial de la clase Solution.

        Returns:
        -------
            str:
                La misma representación que __str__ para consistencia.
        """
        # Lógica: Delega a __str__ para que `repr(solution)` y `str(solution)` sean idénticos.
        #         En clases de resultado/datos, esta consistencia simplifica el debugging.
        # Sintaxis: `return self.__str__()` invoca explícitamente el método dunder;
        #           equivalente a `return str(self)` pero más explícito sobre la intención.
        return self.__str__()
