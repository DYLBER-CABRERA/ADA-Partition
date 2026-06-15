# Documentación Unificada KGeoMIP

Este documento contiene la unión de los 6 archivos DOCX convertidos a Markdown.

---

# Proyecto_KGeoMIP


Algoritmo Geométrico KGeoMIP

Análisis y Diseño de Algoritmos

Proyecto 2026-1

# Introducción

En trabajos anteriores se ha desarrollado con la implementación de algoritmos eficientes para resolver el problema de la Partición de Mínima Información (MIP) en el contexto de la Teoría de la Información Integrada (IIT). Específicamente, se trabajó con el algoritmo QNodes, basado en la minimización de funciones submodulares mediante el algoritmo de Queyranne, y posteriormente se desarrolló la estrategia geométrica GeoMIP, que reformula el problema aprovechando la correspondencia natural entre estados binarios del sistema y vértices de un hipercubo n-dimensional.

Ambas estrategias han demostrado reducciones significativas en la complejidad computacional respecto a los métodos exhaustivos tradicionales, permitiendo el análisis de sistemas con hasta 20-23 nodos en tiempos razonables. Sin embargo, estas implementaciones se han centrado exclusivamente en el caso de bi-particiones, donde el sistema se divide en exactamente dos partes independientes. Esta restricción, si bien conceptualmente clara y algorítmicamente tratable, no explora completamente el espacio de posibles divisiones del sistema.

El presente proyecto propone extender la estrategia geométrica GeoMIP al caso general de k-particiones, donde el sistema puede dividirse en k partes independientes con k ≥ 2. Esta extensión no solo representa un desafío algorítmico interesante, sino que también tiene implicaciones teóricas profundas para la comprensión de la estructura causal de sistemas complejos y para la cuantificación de la información integrada en configuraciones más generales.

## 1.1 Contexto del Proyecto

La Teoría de la Información Integrada (IIT) proporciona un marco matemático riguroso para cuantificar la conciencia en sistemas físicos. Un componente fundamental de esta teoría es el concepto de Partición de Mínima Información (MIP), que identifica cómo debe dividirse un sistema para minimizar la pérdida de información integrada. Esta división revela la estructura causal del sistema y cuantifica su irreducibilidad, propiedades que según IIT distinguen el procesamiento consciente del inconsciente.

En el caso de bi-particiones, el problema consiste en encontrar una división del sistema V en dos partes S₁ y S₂ tal que se minimice la discrepancia entre la dinámica del sistema original y la dinámica reconstruida a partir de las partes. Esta discrepancia se cuantifica mediante la Earth Mover's Distance (EMD) con métrica de Hamming, que mide el trabajo mínimo necesario para transformar una distribución de probabilidad en otra.

Se han implementado dos estrategias principales para resolver este problema. La estrategia QNodes, basada en la demostración de que la función de pérdida EMD es submodular para sistemas Markovianos discretos, logra reducir la complejidad de O(2ⁿ) a O(N³) mediante el algoritmo de Queyranne. Por su parte, la estrategia geométrica GeoMIP reformula el problema aprovechando la representación del espacio de estados como un hipercubo n-dimensional, calculando una tabla de costos de transiciones entre estados que permite identificar biparticiones óptimas sin evaluación exhaustiva del espacio de soluciones.

# Fundamentos Teóricos de k-Particiones

El concepto de k-partición generaliza la idea de bi-partición al caso donde el sistema puede dividirse en k partes independientes en lugar de solo dos. Esta generalización, aparentemente simple en su formulación, introduce complejidades tanto teóricas como computacionales que requieren análisis cuidadoso.

## 2.1 Definición Formal de k-Particiones

Consideremos un sistema V compuesto por n variables binarias. Una k-partición del sistema es una división de V en k subconjuntos disjuntos S₁, S₂, ..., Sₖ tales que la unión de todos los subconjuntos recupera el sistema completo y ningún par de subconjuntos comparte elementos. Formalmente, una k-partición satisface las siguientes condiciones: la unión de todos los subconjuntos S₁ ∪ S₂ ∪ ... ∪ Sₖ es igual a V, la intersección de cualquier par de subconjuntos Sᵢ ∩ Sⱼ es el conjunto vacío para todo i ≠ j, y cada subconjunto Sᵢ es no vacío.

La evaluación de una k-partición requiere comparar la dinámica del sistema original con la dinámica reconstruida a partir de las k partes independientes. Bajo el principio de independencia condicional, la distribución de probabilidad conjunta del sistema particionado se puede expresar como el producto tensorial de las distribuciones marginales de cada parte. La discrepancia entre el sistema original y el sistema reconstruido se cuantifica mediante la misma métrica EMD utilizada en el caso de bi-particiones, pero ahora aplicada a la reconstrucción k-partita.

## 2.2 Complejidad del Espacio de k-Particiones

El número de posibles k-particiones de un conjunto de n elementos está dado por los números de Stirling del segundo tipo, denotados S(n,k). Estos números crecen extremadamente rápido con n y k, representando un desafío computacional significativo. Por ejemplo, para un sistema de solo 10 variables, el número de posibles tri-particiones (k=3) es de 9,330 configuraciones, mientras que para 15 variables este número alcanza más de 2.3 millones de tri-particiones posibles.

Esta explosión combinatoria hace inviable la búsqueda exhaustiva para sistemas de tamaño moderado a grande. Sin embargo, es importante notar que no todas las k-particiones son igualmente significativas desde el punto de vista de la estructura causal del sistema. Muchas particiones pueden ser triviales o redundantes, lo que sugiere que enfoques inteligentes de búsqueda podrían identificar particiones óptimas o cuasi-óptimas sin necesidad de evaluación exhaustiva.

Además, la relación entre bi-particiones y k-particiones es importante. Toda bi-partición es una 2-partición, y conceptualmente, una k-partición puede verse como el resultado de aplicar k-1 bi-particiones sucesivas al sistema. Esta observación sugiere que las técnicas desarrolladas para bi-particiones podrían extenderse o adaptarse al caso k-partito, aunque la optimalidad de este enfoque greedy no está garantizada.

## 2.3 Interpretación Geométrica de k-Particiones

La estrategia geométrica GeoMIP se fundamenta en la representación del espacio de estados como un hipercubo n-dimensional, donde cada vértice corresponde a un posible estado binario del sistema y las aristas conectan estados que difieren en exactamente una variable. En este marco geométrico, una bi-partición puede interpretarse como la división del hipercubo mediante un hiperplano, separando el espacio en dos regiones correspondientes a las dos partes de la partición.

Esta interpretación geométrica se extiende naturalmente al caso de k-particiones. Una k-partición del sistema corresponde a la división del hipercubo n-dimensional mediante k-1 hiperplanos, creando k regiones disjuntas que particionan completamente el espacio de estados. La configuración geométrica de estos hiperplanos determina qué variables se asignan a cada parte de la partición y, por lo tanto, afecta directamente la pérdida de información asociada a la partición.

Un aspecto crucial de la estrategia GeoMIP es la tabla de costos de transiciones entre estados, que cuantifica la energía o inercia requerida para la transición entre cada par de estados del sistema. Esta tabla, calculada mediante una función de costo que incorpora la distancia de Hamming entre estados y la estructura topológica del hipercubo, captura información sobre la estructura causal del sistema que es independiente de la forma específica de particionarlo. Por lo tanto, la misma tabla de costos calculada para el análisis de bi-particiones puede potencialmente reutilizarse para el análisis de k-particiones, evitando la necesidad de recalcular esta información costosa.

# Planteamiento del Problema

El objetivo central de este proyecto es diseñar e implementar una extensión de la estrategia geométrica GeoMIP que permita identificar la k-Partición de Mínima Información (k-MIP) para valores de k mayores que 2. Esta extensión debe aprovechar la infraestructura existente, incluyendo la representación del espacio de estados como hipercubo n-dimensional, la tabla de costos de transiciones entre estados, y las estructuras de datos N-Cubos ya implementadas.

## 3.1 Formulación Matemática del Problema

Dado un sistema V con n variables binarias y su correspondiente Matriz de Probabilidad de Transición que especifica la dinámica P(Vₜ₊₁|Vₜ), el problema consiste en encontrar una k-partición óptima del sistema que minimice la discrepancia entre la distribución de probabilidad del sistema original y la distribución reconstruida a partir de las k partes independientes.

Formalmente, se busca encontrar la k-partición de V en subconjuntos S₁, S₂, ..., Sₖ que minimice la función de pérdida δₖ definida como la Earth Mover's Distance entre la distribución original del sistema y el producto tensorial de las distribuciones marginales de cada parte. El problema requiere no solo encontrar una partición con pérdida baja, sino identificar la partición óptima global entre todas las posibles k-particiones del sistema.

Es importante destacar que el problema debe resolverse para diferentes valores de k, típicamente k ∈ {2, 3, 4, 5}, permitiendo analizar cómo la estructura óptima de partición del sistema varía con el número de partes permitidas. Esta información puede revelar aspectos fundamentales sobre la organización modular del sistema y la naturaleza de sus dependencias causales.

## 3.2 Restricciones y Consideraciones

La implementación debe mantener compatibilidad con la arquitectura existente del proyecto, heredando de la clase base SIA y siguiendo los patrones de diseño establecidos en semestres anteriores. Esto asegura la interoperabilidad con las herramientas de validación y comparación ya desarrolladas, particularmente la posibilidad de comparar resultados con las implementaciones de referencia PyPhi y QNodes para casos donde estas sean computacionalmente viables.

La solución debe ser capaz de procesar los mismos conjuntos de datos de prueba utilizados en proyectos anteriores, permitiendo validación cruzada y análisis comparativo de rendimiento. Los datasets incluyen sistemas con diferentes números de variables, desde casos pequeños de validación con 3-6 nodos hasta sistemas de escala moderada con 10-15 nodos, y casos de escalabilidad con 20 o más nodos donde solo aproximaciones heurísticas podrían ser viables.

Un aspecto fundamental es que la implementación debe reutilizar eficientemente los componentes existentes de GeoMIP. Particularmente, la tabla de costos de transiciones entre estados, que constituye uno de los cálculos más costosos del método geométrico, debe calcularse una única vez y luego utilizarse para evaluar todas las k-particiones candidatas independientemente del valor de k. Esta reutilización es crucial para mantener la eficiencia computacional del enfoque.

## 3.3 Alcance del Proyecto

El proyecto debe producir una implementación funcional que extienda GeoMIP para identificar k-particiones óptimas con k comprendido entre 2 y 5. Para valores pequeños de k y sistemas de tamaño reducido, donde la búsqueda exhaustiva es computacionalmente viable, la implementación debe ser capaz de encontrar la k-MIP óptima global con certeza. Para sistemas más grandes o valores mayores de k, donde la búsqueda exhaustiva se vuelve intratable, se espera que la implementación encuentre k-particiones de alta calidad, aunque no necesariamente óptimas globales, en tiempos razonables.

La evaluación del proyecto considerará tanto la calidad de las soluciones encontradas como la eficiencia computacional del enfoque. Se espera que para sistemas de tamaño moderado, la implementación logre speedups significativos respecto a métodos de búsqueda exhaustiva, manteniendo al mismo tiempo alta precisión en la identificación de particiones óptimas o cuasi-óptimas. El análisis debe incluir comparación con las bi-particiones encontradas por GeoMIP original para k=2, validando que la extensión reproduce correctamente los resultados previos en este caso base.

Además de los aspectos algorítmicos, el proyecto debe incluir análisis experimental comprehensivo que caracterice el comportamiento del método propuesto. Esto incluye estudiar cómo la calidad de las soluciones y los tiempos de ejecución escalan con el tamaño del sistema n y el número de particiones k, identificar patrones en las k-particiones óptimas encontradas que revelen estructura modular en los sistemas analizados, y comparar diferentes estrategias o variantes del enfoque si se implementan múltiples alternativas.

# Entregables del Proyecto

El proyecto requiere la entrega de componentes de software, documentación técnica y análisis experimental que demuestren la comprensión del problema, la calidad de la solución implementada y la capacidad de análisis crítico de los resultados obtenidos.

## 4.1 Componentes de Software

Se debe entregar una implementación completa y funcional que extienda la estrategia geométrica GeoMIP para k-particiones. El código debe organizarse como una nueva clase que herede de la clase base SIA, siguiendo la estructura modular establecida en el proyecto. La implementación debe ubicarse en el archivo correspondiente dentro de la jerarquía de directorios del proyecto, específicamente en src/controllers/strategies/, manteniendo consistencia con las estrategias existentes.

El código debe incluir como mínimo la implementación del método principal que encuentra la k-MIP para un valor de k dado, métodos auxiliares necesarios para la evaluación de k-particiones candidatas utilizando la tabla de costos existente, funciones para el cálculo de distribuciones marginales y productos tensoriales de k términos, y mecanismos para identificar y generar k-particiones candidatas para evaluación. La implementación debe reutilizar eficientemente los componentes existentes de GeoMIP, particularmente la infraestructura de N-Cubos y el cálculo de la tabla de costos de transiciones.

El código entregado debe estar completamente documentado mediante docstrings que expliquen la función de cada método, los parámetros de entrada y salida, y las asunciones o precondiciones importantes. Se deben incluir comentarios en línea para secciones de código particularmente complejas o no obvias. Además, se deben proporcionar tests unitarios que validen el correcto funcionamiento de los componentes principales, particularmente la evaluación correcta de k-particiones y la consistencia con los resultados de bi-partición para el caso k=2.

## 4.2 Documentación Técnica

Se debe entregar un reporte técnico comprehensivo que documente el trabajo realizado. Este reporte debe comenzar con una explicación matemática clara y rigurosa de cómo se extiende el marco teórico de GeoMIP de bi-particiones a k-particiones. Esto incluye la formulación precisa del problema de optimización, la definición de la función de pérdida para k-particiones, y la justificación de que la tabla de costos calculada para bi-particiones es aplicable al caso k-partito.

El reporte debe incluir una descripción detallada del enfoque algorítmico implementado, explicando las decisiones de diseño tomadas, las estructuras de datos utilizadas, y cómo se aborda el desafío de la explosión combinatoria del espacio de k-particiones. Esta descripción debe ser suficientemente detallada para que otro equipo pueda comprender el funcionamiento del algoritmo sin necesidad de leer el código fuente.

Se debe proporcionar un análisis de complejidad completo, tanto teórico como empírico. El análisis teórico debe caracterizar la complejidad temporal y espacial del algoritmo en función de n (número de variables) y k (número de particiones), identificando los cuellos de botella computacionales principales. El análisis empírico debe medir los tiempos de ejecución reales en los datasets de prueba y comparar estos tiempos con las predicciones teóricas y con los métodos de referencia.

La documentación debe incluir secciones que describan las limitaciones conocidas de la implementación, casos donde el método puede no funcionar óptimamente, posibles mejoras futuras identificadas durante el desarrollo, y lecciones aprendidas del proceso de implementación. Esta reflexión crítica sobre el trabajo realizado es fundamental para demostrar comprensión profunda del problema.

## 4.3 Resultados Experimentales

Se debe realizar una validación experimental exhaustiva utilizando los datasets de prueba proporcionados. Para sistemas pequeños donde la búsqueda exhaustiva es viable, se debe comparar las k-particiones encontradas por la implementación con las k-MIPs óptimas globales, calculando métricas de precisión como la tasa de acierto exacto y el error relativo en la pérdida de información. Para el caso particular k=2, se debe verificar que los resultados coinciden con los obtenidos por la implementación original de GeoMIP para bi-particiones.

Los resultados deben presentarse de forma clara y sistemática mediante tablas que resuman métricas clave como tiempos de ejecución, tasas de acierto, errores relativos y speedups obtenidos respecto a métodos de referencia. Se deben incluir gráficas que ilustren cómo estas métricas varían con el tamaño del sistema y el valor de k, permitiendo identificar patrones y tendencias en el comportamiento del algoritmo.

El análisis experimental debe ir más allá de la simple presentación de números, incluyendo interpretación de los resultados obtenidos. Esto incluye discusión sobre qué patrones se observan en las k-particiones óptimas encontradas, si existe estructura modular recurrente en los sistemas analizados, cómo cambia la partición óptima al variar k, y qué revela esto sobre la organización causal del sistema. Se debe analizar también casos donde el método encuentra soluciones subóptimas, investigando las causas y proponiendo posibles remedios.

Finalmente, si el equipo implementó múltiples variantes o estrategias alternativas del enfoque básico, se debe incluir comparación experimental entre estas variantes, analizando los trade-offs entre precisión y eficiencia, identificando qué variante funciona mejor en qué circunstancias, y proporcionando recomendaciones sobre cuándo usar cada alternativa.

## 4.4 Presentación Final

Cada equipo debe preparar y entregar una presentación que resuma el trabajo realizado y los resultados obtenidos. La presentación tendrá una duración máxima de 15 minutos, más 5 minutos para preguntas y discusión. El contenido debe estructurarse de manera que primero se contextualice el problema y se explique la extensión teórica de bi-particiones a k-particiones, luego se presente el enfoque algorítmico desarrollado de manera clara pero concisa, se muestren los resultados experimentales más significativos mediante visualizaciones efectivas, y finalmente se discutan las conclusiones y lecciones aprendidas.

Se espera que la presentación incluya una demostración en vivo del software funcionando, ejecutando la búsqueda de k-particiones en al menos un sistema de prueba y mostrando los resultados obtenidos. Si es posible, se debe incluir visualización de las k-particiones encontradas sobre la representación del hipercubo, ilustrando cómo los k-1 hiperplanos dividen el espacio de estados. Esta componente visual ayuda a transmitir la intuición geométrica del método y hace la presentación más comprensible y memorable.

## 4.5 Criterios de Evaluación

La evaluación del proyecto considerará múltiples dimensiones de calidad. La correctitud de la implementación se evaluará verificando que produce resultados correctos en casos de validación, que mantiene consistencia con GeoMIP original para k=2, y que el código es robusto frente a diferentes inputs y casos edge. La eficiencia se medirá comparando tiempos de ejecución con métodos de referencia cuando estos sean viables, analizando la escalabilidad con n y k, y evaluando el uso efectivo de recursos computacionales.

La calidad del código se evaluará considerando la claridad y organización del código, la completitud de la documentación y comentarios, el seguimiento de las convenciones de estilo del proyecto, y la inclusión de tests que validen funcionalidad. La documentación técnica se evaluará por la claridad en la explicación de conceptos matemáticos y algorítmicos, la profundidad del análisis de complejidad, la calidad del análisis experimental y visualizaciones, y la reflexión crítica sobre limitaciones y mejoras posibles.

Finalmente, la presentación se evaluará considerando la claridad en la comunicación de ideas complejas, la efectividad de las visualizaciones utilizadas, la calidad de la demostración en vivo, y la capacidad de responder preguntas y defender decisiones de diseño. El trabajo en equipo y la distribución equitativa de responsabilidades también serán considerados en la evaluación global del proyecto.

# Observaciones Finales

Este proyecto representa una oportunidad para profundizar en problemas de optimización combinatoria complejos, aplicar y extender técnicas de representación geométrica de sistemas discretos, y desarrollar soluciones algorítmicas eficientes para problemas con relevancia teórica en el campo de la cuantificación de información integrada y la teoría de la conciencia.

El desafío principal radica en diseñar enfoques que balanceen adecuadamente la necesidad de encontrar particiones de alta calidad con la restricción de hacerlo en tiempos computacionales razonables. Este balance requiere creatividad algorítmica, comprensión profunda de las propiedades matemáticas del problema, y capacidad para identificar y explotar estructura en el espacio de soluciones.

El trabajo desarrollado en este proyecto contribuirá a extender las capacidades de análisis de sistemas complejos más allá de las bi-particiones tradicionales, abriendo nuevas posibilidades para investigar la estructura modular y las dependencias causales en sistemas con múltiples niveles de organización. Los métodos y conocimientos adquiridos tendrán aplicabilidad no solo en el contexto específico de IIT, sino más generalmente en problemas de clustering, detección de comunidades, y análisis de redes donde la identificación de particiones óptimas juega un papel fundamental.


---

# MANUAL DE USUARIO


MANUAL DE USUARIO – GeoMIP

1. Introducción

Este manual describe el uso del framework GeoMIP desde la perspectiva del usuario final. Su objetivo es guiar al investigador en el proceso de instalación, configuración y ejecución del software, así como en la interpretación de los resultados obtenidos al resolver el problema de la Minimum Information Partition (MIP) en el marco de la Teoría de la Información Integrada.

El manual está dirigido a usuarios con conocimientos básicos de programación en Python y familiaridad general con análisis computacional, pero no requiere experiencia previa en el desarrollo interno del framework ni en sus algoritmos subyacentes.

2. ¿Qué es GeoMIP y para qué sirve?

GeoMIP es un framework computacional diseñado para calcular de manera eficiente la Minimum Information Partition de sistemas descritos mediante matrices de transición probabilística. El software integra dos métodos complementarios que permiten abordar el problema desde distintas estrategias computacionales, manteniendo coherencia en la entrada, el procesamiento y la salida de resultados.

Desde el punto de vista del usuario, GeoMIP permite analizar sistemas de distintos tamaños, seleccionar el método de cálculo más adecuado según los recursos disponibles y obtener como salida la partición óptima junto con la medida de pérdida asociada.

El framework está orientado a investigación académica y puede utilizarse tanto para experimentos exploratorios como para análisis sistemáticos reproducibles.

3. Requisitos del usuario

Para utilizar GeoMIP, el usuario debe contar con:

Un entorno Python funcional

Acceso a una máquina con recursos computacionales acordes al tamaño del sistema a analizar,

Familiaridad básica con la ejecución de scripts desde línea de comandos o entornos de desarrollo.

No es necesario contar con hardware especializado para ejecutar el software, aunque el uso de GPU puede mejorar el rendimiento en uno de los métodos disponibles.

4. Instalación y configuración

GeoMIP se distribuye como código fuente y debe ejecutarse dentro de un entorno Python adecuadamente configurado. Se recomienda crear un entorno virtual para aislar dependencias y asegurar reproducibilidad.

Una vez descargado el repositorio base, el usuario debe instalar las dependencias declaradas en los archivos de configuración incluidos. Estas dependencias corresponden a bibliotecas científicas estándar ampliamente utilizadas en investigación computacional.

En el caso de utilizar el método geométrico con aceleración, el entorno puede configurarse para aprovechar paralelización multinúcleo y, de manera opcional, GPU compatible. Si el hardware no está disponible, el software se ejecuta correctamente en modo CPU sin requerir ajustes adicionales.

5. Uso básico del software

El uso de GeoMIP se basa en la ejecución de un script principal que orquesta la carga del sistema, la selección del método y la ejecución del cálculo. El usuario debe especificar el estado inicial del sistema, las máscaras que definen condición, mecanismo y alcance y el método de cálculo a utilizar. Estos parámetros pueden definirse directamente en el script de ejecución o proporcionarse mediante archivos de entrada, según el flujo de trabajo adoptado.

Durante la ejecución, el software informa el progreso del cálculo y, al finalizar, retorna una solución estructurada que contiene la partición óptima y la información asociada.

6. Ejecución de GeoMIP

6.1 Entrada de datos del sistema

Matriz de Transición Probabilística (TPM)

La matriz de transición probabilística (TPM) constituye el dato de entrada fundamental del framework GeoMIP, y es utilizada de manera común por todos los métodos de cálculo disponibles. La TPM describe la dinámica del sistema discreto bajo análisis y define la probabilidad de transición hacia estados futuros a partir de estados presentes.

En GeoMIP, la TPM se integra al sistema durante la fase de inicialización, antes de la ejecución de cualquier estrategia específica. Tanto el Método 1 (enfoque geométrico) como el Método 2 (programación dinámica) operan sobre el mismo modelo del sistema, construido a partir de esta matriz. La representación interna de la TPM se realiza mediante una estructura tensorial, que permite descomponer la dinámica global del sistema en componentes elementales asociados a cada variable. Esta representación facilita la construcción de estructuras n-dimensionales utilizadas posteriormente para evaluar subsistemas y particiones.

La TPM puede provenir de distintas fuentes, como datos experimentales o modelos sintéticos, siempre que preserve la coherencia dimensional requerida por el sistema.

Carga de la TPM

En la implementación de referencia, la TPM se carga explícitamente desde un archivo externo, por ejemplo en formato CSV. Este archivo contiene la matriz numérica que describe las transiciones del sistema completo. Un ejemplo típico de carga de la TPM es el siguiente:

import numpy as np

from pathlib import Path

tpm = np.genfromtxt(Path("src/.samples/N20A.csv"), delimiter=",")

Las redes de prueba se encuentran ubicadas en la siguiente ruta del proyecto:

GeoMIPMetodo2/src/.samples/

Dentro de este directorio, el usuario encontrará múltiples archivos CSV que representan redes de distintos tamaños, utilizadas tanto para pruebas como para ejecuciones experimentales. Por ejemplo, el archivo GeoMIPMetodo2/src/.samples/N20A.csv corresponde a una red de tamaño 20 y es utilizada como red de muestra en varios de los scripts de ejecución incluidos en el framework.

La carga explícita de la TPM puede observarse directamente en el código del método:

def ejecutar_desde_excel(...)

definido en el archivo GeoMIPMetodo2/src/main.py. En este método se muestra claramente cómo se inicializa el sistema utilizando una red de ejemplo, mediante una instrucción como:

tpm = np.genfromtxt(Path("src/.samples/N20A.csv"), delimiter=",")

Este fragmento ilustra el patrón estándar de uso: el usuario selecciona una red de la carpeta .samples, la carga en memoria y la utiliza como base para ejecutar el análisis sobre uno o varios subsistemas.

Estado inicial del sistema

El estado inicial define la configuración de partida del sistema y se representa mediante una cadena binaria, donde cada posición corresponde a una variable del sistema.

Por ejemplo, para una red de 20 nodos:

estado_inicial = "10000000000000000000"

La longitud del estado inicial debe coincidir con la dimensión de la TPM. Este estado se utiliza como referencia para la preparación de los subsistemas y para la evaluación de transiciones durante la ejecución de los métodos.

Máscaras binarias: condiciones, alcance y mecanismo

La definición del subsistema a analizar se realiza mediante máscaras binarias, también representadas como cadenas de caracteres '0' y '1'. Estas máscaras permiten seleccionar subconjuntos de variables del sistema:

condiciones (str): cadena binaria que define las variables condicionadas.

alcance (str): cadena binaria que define el purview o conjunto objetivo.

mecanismo (str): cadena binaria que define el mecanismo.

Todas las cadenas binarias deben tener la misma longitud que el estado inicial, y  usar '1' para indicar variables en estado ON y '0' para variables en estado OFF.

Ejemplo para una red de 20 variables:

condiciones = "11111111111111111111"

alcance     = "11110000000000000000"

mecanismo   = "00001111000000000000"

Inicialización del sistema

Una vez definidos la TPM y el estado inicial, el sistema se inicializa mediante un objeto de configuración, típicamente una instancia de la clase Manager. Este objeto encapsula la información necesaria para preparar las estructuras internas del sistema.

Ejemplo de inicialización:

from src.controllers.manager import Manager

config_sistema = Manager(estado_inicial=estado_inicial)

La TPM, cargada previamente, se asocia al sistema durante esta fase de inicialización o mediante la configuración del entorno correspondiente, de modo que esté disponible para la preparación de los subsistemas.

Preparación del subsistema

Antes de ejecutar cualquier método de cálculo, GeoMIP realiza una fase de preparación del subsistema, común a todas las estrategias. En esta fase se construyen las estructuras n-dimensionales que representan el sistema restringido por las máscaras de condiciones, alcance y mecanismo. Esta preparación se realiza internamente mediante métodos heredados de la clase base SIA y no requiere intervención directa del usuario, siempre que los datos de entrada hayan sido definidos correctamente.

6.2  Método Geométrico con GPU

Esta sección describe cómo ejecutar el Método 1 una vez que el usuario ha definido correctamente los datos de entrada del sistema (TPM, estado inicial y máscaras binarias), tal como se explica en la sección 6.1 Entrada de datos del sistema.El método geométrico está diseñado para explotar la estructura topológica del espacio de estados y puede beneficiarse de paralelización y aceleración por hardware. Desde la perspectiva del usuario, su ejecución no difiere conceptualmente de otros métodos: se selecciona la estrategia correspondiente y se ejecuta el cálculo. Cuando el entorno dispone de recursos de aceleración, el método los utiliza de forma transparente. En caso contrario, el cálculo se realiza íntegramente en CPU, manteniendo la corrección del resultado.

Este método es especialmente adecuado para sistemas de mayor tamaño, donde el espacio de particiones crece rápidamente.

Como prerrequisito el usuario debe construir un objeto de configuración de tipo Manager. Este objeto encapsula toda la información necesaria para describir el sistema bajo análisis, incluyendo: el estado inicial del sistema, la representación tensorial de la TPM (tensor de probabilidad condicional) y la configuración del experimento (etiquetas, página, etc.).

El Método 1 se ejecuta mediante la clase Geometry, definida en el archivo Geo_MIP_Metodo1\geometry.py.

El punto de entrada para ejecutar el Método 1 es el método público:

Geometry.aplicar_estrategia(...)

La clase Geometry hereda de la clase base SIA y reutiliza la fase común de preparación del subsistema. El usuario no interactúa directamente con esta fase; basta con suministrar correctamente las máscaras binarias del subsistema.

Paso a paso de la ejecución

Para ejecutar el Método 1, el usuario debe seguir estos pasos:

Inicializar los datos del sistema (TPM, estado inicial y máscaras), según la sección Entrada de datos del sistema.

Crear un objeto de configuración (Manager) que encapsule el estado inicial y la información del sistema.

Instanciar la clase Geometry, pasando el objeto de configuración.

Llamar al método aplicar_estrategia(...) con las máscaras de condiciones, alcance y mecanismo.

Ejemplo de ejecución

from geometry import Geometry

from src.controllers.manager import Manager

# Inicialización del sistema (ver sección Entrada de datos)

estado_inicial = "10000000000000000000"

config_sistema = Manager(estado_inicial=estado_inicial)

# Instanciar la estrategia geométrica

geo = Geometry(config_sistema)

# Definir el subsistema

condiciones = "11111111111111111111"

alcance     = "11110000000000000000"

mecanismo   = "00001111000000000000"

# Ejecutar el método

solucion = geo.aplicar_estrategia(condiciones, alcance, mecanismo)

print(solucion)

Resultado de la ejecución

El método retorna un objeto solución que contiene:

la bipartición óptima encontrada,

la pérdida asociada,

metadatos del proceso de cálculo.

Este objeto puede imprimirse, analizarse o utilizarse como entrada para etapas posteriores del análisis.

6.3 Método de Programación Dinámica

Esta sección describe cómo ejecutar el Método 2 utilizando la infraestructura del framework GeoMIP,  para la preparación del subsistema, que permite definir los datos de entrada según la sección Entrada de datos del sistema donde se orquesta la lectura de subsistemas y la carga de la TPM, para posteriormente proceder con la ejecución del algoritmo para hallar la MIP sobre cada subsistema.

Paso a paso de ejecución

Paso 1. Ubique el archivo de ejecución del Método 2

El flujo operativo del Método 2 se encuentra implementado en el archivo:

GeoMIPMetodo2/src/main.py

Dentro de este archivo, el método que conduce la ejecución es:

def ejecutar_desde_excel(ruta_excel, ruta_salida, inicio=0, cantidad=50)

Este método está diseñado para ejecutar el análisis sobre múltiples subsistemas descritos en un archivo Excel.

Paso 2. Identifique y seleccione la TPM de trabajo (red de entrada)

Antes de ejecutar el método, el usuario debe saber qué TPM se utilizará. En la implementación de referencia, la TPM se carga desde un archivo CSV ubicado en:

GeoMIPMetodo2/src/.samples/

Por ejemplo, el código de referencia carga una red de tamaño 20 desde:

GeoMIPMetodo2/src/.samples/N20A.csv

En el propio main.py, dentro de ejecutar_desde_excel(...), la carga se realiza con una instrucción como:

tpm = np.genfromtxt(Path("src/.samples/N20A.csv"), delimiter=",")

El usuario puede cambiar el archivo CSV por otra red disponible en .samples, siempre que sea consistente con la dimensión del estado inicial.

Paso 3. Prepare el archivo Excel con los subsistemas

El método ejecutar_desde_excel(...) espera un archivo Excel (ruta_excel) que contenga una lista de subsistemas. En el código de referencia, estos subsistemas se leen desde una hoja específica y una columna determinada, por ejemplo:

df = pd.read_excel(ruta_excel, sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"])

Cada fila debe representar un subsistema en el formato esperado por el script (por ejemplo, una cadena con alcance|mecanismo), ya que el método separa el texto usando split("|") y transforma cada parte a representación binaria mediante convertir_a_binario(...).

Paso 4. Verifique el estado inicial y condiciones globales del sistema

Dentro de ejecutar_desde_excel(...) se define explícitamente el estado inicial y la máscara de condiciones globales. En el ejemplo que indicaste, aparecen valores como:

estado_inicio = "10000000000000000000"

condiciones   = "11111111111111111111"

Estos valores deben ser coherentes con el tamaño de la red definida por la TPM seleccionada (por ejemplo, longitud 20 si se usa N20A.csv).

Paso 5. Inicialice el sistema (configuración)

En el mismo método se inicializa el sistema mediante la clase Manager, por ejemplo:

config_sistema = Manager(estado_inicial=estado_inicio)

A partir de esta configuración, el framework prepara las estructuras internas necesarias para ejecutar la estrategia del Método 2 sobre cada subsistema.

Paso 6. Ejecute el Método 2

Para ejecutar el Método 2, el usuario debe invocar ejecutar_desde_excel(...) indicando:

la ruta del Excel de subsistemas (ruta_excel),

la ruta donde quedarán los resultados (ruta_salida),

y opcionalmente el rango de filas a procesar (inicio, cantidad).

Ejemplo de ejecución programática (desde un script o consola Python dentro del proyecto):

from src.main import ejecutar_desde_excel

ruta_excel  = "ruta/al/archivo_de_subsistemas.xlsx"

ruta_salida = "ruta/de/salida/"

ejecutar_desde_excel(ruta_excel, ruta_salida, inicio=0, cantidad=50)

El método recorrerá los subsistemas leídos desde el Excel, y para cada uno:

construirá alcance y mecanismo en binario,

preparará el subsistema,

ejecutará el algoritmo del Método 2,

y registrará el resultado en la estructura de salida.

Paso 7. Ubique los resultados generados

Los resultados se almacenan en la ruta definida en ruta_salida. La estructura exacta de carpetas y archivos depende de la configuración del proyecto, pero el patrón general es que cada ejecución produce salidas organizadas por red y estado inicial, de modo que el usuario pueda inspeccionar los resultados por subsistema.

Ejemplo de ejecución

Este ejemplo permite al usuario  ejecutar GeoMIP sobre una red de muestra de 4 nodos, generando los artefactos de salida producidos por el framework.

El punto de entrada de la ejecución de muestra es el archivo:

exec.py

ubicado en la carpeta raíz del proyecto. Este archivo inicializa el entorno de ejecución y llama al flujo principal del aplicativo, definido internamente en el módulo correspondiente.

Los pasos para ejecutar la muestra son:

Abrir una terminal (PowerShell, CMD o terminal equivalente).

Ubicarse en la carpeta raíz del proyecto, donde se encuentra el archivo exec.py. Por ejemplo:

cd RUTA\A\GeoMIPMetodo2

Ejecutar el archivo de muestra utilizando uno de los siguientes comandos:

python .\exec.py   o, alternativamente:   py .\exec.py

7. Interpretación de resultados

El resultado de la ejecución de GeoMIP se presenta como una solución estructurada que contiene:

La partición óptima identificada,

el valor de la pérdida asociada,  ,

la información necesaria para interpretar el subsistema evaluado.

La partición indica cómo se divide el sistema en dos subconjuntos, mientras que la pérdida cuantifica el impacto de dicha partición en términos de información integrada. Estos resultados pueden utilizarse directamente en análisis posteriores o exportarse para su procesamiento externo.


---

# ManualGeoMIP


GeoMIP (Geometric-Topological and Dynamic Programming Framework for Enhanced Computational Tractability of Minimum Information Partition in Integrated Information Theory)

MANUAL TÉCNICO

1. Introducción

GeoMIP es un framework de software científico orientado a investigación académica que implementa un conjunto de técnicas computacionales para resolver el problema de la Minimum Information Partition (MIP) en IIT. El objetivo del software es reducir el costo computacional asociado al hallazgo de la bipartición mínima requerida para cuantificar pérdida por partición bajo métricas tipo Earth Mover’s Distance (EMD), conservando la formalidad del cálculo.

El framework integra dos métodos implementados de manera independiente pero coherente con una misma formalización: (i) un enfoque geométrico-topológico acelerado mediante paralelización (CPU y opcionalmente GPU/CUDA), y (ii) una reformulación del cálculo de costos que habilita un algoritmo de programación dinámica (DP) con memoización estructurada. En ambos casos, la base conceptual es representar los estados binarios del sistema como vértices de un hipercubo n-dimensional y explotar la distancia de Hamming para organizar el cálculo y reducir redundancias.

2. Alcance del software

GeoMIP cubre el ciclo completo de cálculo interno requerido para identificar MIP en subsistemas discretos binarios definidos por una TPM en formato compatible con IIT (por ejemplo, estado-a-nodo o representación equivalente). El software contempla explícitamente la separación entre mecanismo (variables en t) y purview/scope (variables en t+1), y asume que el subsistema a analizar puede describirse mediante máscaras binarias, índices o listas equivalentes.

El alcance de GeoMIP se centra en: preparación del subsistema, construcción de estructuras de costo para EMD, generación de biparticiones candidatas (exhaustivas en tamaños pequeños y heurísticas/estructuradas en tamaños grandes), evaluación y selección de la bipartición mínima, y retorno de un objeto solución formalizable para integración en pipelines de investigación. GeoMIP no pretende reemplazar herramientas completas de IIT, sino actuar como motor computacional especializado para la fase MIP.

3. Descripción general del framework GeoMIP

GeoMIP se organiza como un framework modular con un núcleo común y dos implementaciones de estrategia. El núcleo común proporciona: (1) normalización de entradas (TPM, mecanismo, scope), (2) representación del espacio de estados y utilidades bitwise, (3) servicios de métrica (Hamming/EMD), y (4) un modelo de “solución” que encapsula la partición elegida, la pérdida asociada y metadatos de ejecución.

Las implementaciones concretas difieren en el modo de construir la tabla de costos de transición y en la estrategia para generar/recorrer particiones. El método 1 privilegia paralelización y aceleración, mientras que el método 2 privilegia una reformulación matemática que hace el cálculo intrínsecamente reutilizable por DP.

4. Arquitectura del sistema

4.1 Visión general

GeoMIP adopta una arquitectura en capas, diseñada para desacoplar las decisiones estructurales de alto nivel de los detalles algorítmicos y de implementación. Esta arquitectura permite que diferentes estrategias computacionales coexistan dentro de un mismo framework, compartiendo un núcleo conceptual común y garantizando coherencia metodológica, extensibilidad y mantenibilidad del software.

Desde el punto de vista arquitectónico, GeoMIP no se concibe como una aplicación monolítica, sino como un framework científico orientado a estrategias, donde los métodos de resolución del problema de la Minimum Information Partition (MIP) se implementan como componentes intercambiables dentro de una misma capa funcional. Esta decisión permite incorporar nuevas formulaciones algorítmicas sin alterar la estructura global del sistema. La arquitectura abstrae explícitamente la preparación y representación del subsistema IIT, la construcción del espacio de estados, la selección de la estrategia computacional, la evaluación de particiones y la generación de resultados formales.

De este modo, GeoMIP separa claramente qué hace el sistema de cómo lo hace cada método.

4.2 Capas funcionales del framework GeoMIP

La arquitectura del sistema se organiza en cinco capas funcionales bien definidas, cada una con responsabilidades específicas y límites claros de actuación.

4.2.1 Capa de entrada y configuración

Esta capa es responsable de recibir y normalizar toda la información necesaria para ejecutar el análisis. Incluye la definición de la matriz de transición probabilística (TPM), la selección del mecanismo y del purview (alcance), así como los parámetros de ejecución que controlan el comportamiento del framework (por ejemplo, selección del método computacional o configuración de recursos).

Desde el punto de vista arquitectónico, esta capa actúa como frontera entre el usuario o pipeline externo y el núcleo computacional del sistema. No realiza ningún cálculo de IIT ni toma decisiones algorítmicas; su función es garantizar que la información de entrada se entregue al núcleo en un formato consistente y validado.

4.2.2 Capa de núcleo computacional IIT

La capa de núcleo computacional constituye el corazón conceptual del framework. En ella se definen las abstracciones fundamentales necesarias para el cálculo de la MIP, independientemente del método utilizado.

Esta capa encapsula la representación del subsistema IIT, la codificación del espacio de estados como una estructura discreta, la interpretación geométrica del espacio como un hipercubo n-dimensional y las métricas de distancia utilizadas para evaluar discrepancias entre distribuciones.

La capa de núcleo no contiene decisiones estratégicas sobre cómo explorar el espacio de estados ni cómo optimizar el cálculo; su propósito es proporcionar una base matemática y computacional común sobre la cual se apoyan todas las estrategias.

Capa de estrategias computacionales

La capa de estrategias computacionales es el elemento diferenciador de GeoMIP como framework. En esta capa se implementan los distintos métodos para resolver el problema de la MIP, cada uno con sus propias decisiones algorítmicas y compromisos computacionales. Esta capa incluye dos estrategias principales: Un enfoque geométrico–topológico acelerado mediante paralelización (y opcionalmente GPU) y una reformulación del problema basada en programación dinámica.

Ambas estrategias operan sobre el mismo núcleo computacional y producen resultados compatibles, pero difieren en la forma en que construyen los costos de transición y en cómo exploran el espacio de particiones. Arquitectónicamente, estas estrategias son intercambiables y coexistentes, lo que permite seleccionar la más adecuada según el contexto de ejecución.

4.2.4 Capa de evaluación de particiones

Esta capa es responsable de transformar los resultados intermedios de las estrategias computacionales en decisiones formales sobre la partición óptima. Incluye la generación de biparticiones candidatas, el cálculo de distribuciones marginales asociadas a cada partición y la evaluación de la pérdida mediante la métrica correspondiente.

La capa de evaluación actúa como un mecanismo de validación y selección: independientemente de cómo se generen los candidatos, la decisión final se toma bajo criterios uniformes, garantizando consistencia entre métodos.

4.2.5 Capa de salida y resultados

La capa de salida encapsula el resultado final del proceso de cálculo. Su función es producir una representación formal de la solución encontrada, que incluya la partición mínima, el valor de pérdida asociado y los metadatos relevantes del análisis.

Esta capa permite que GeoMIP se integre fácilmente en pipelines de investigación más amplios, ya que el resultado se presenta como un objeto estructurado y no como una salida ad-hoc o dependiente de la estrategia utilizada.

4.3 Interacción y flujo de datos entre capas

El flujo de datos en GeoMIP es predominantemente unidireccional y secuencial. La información fluye desde la capa de entrada hacia el núcleo computacional, luego hacia la capa de estrategias, continúa hacia la evaluación de particiciones y finalmente se materializa en la capa de salida.

Este flujo controlado evita dependencias circulares entre capas y permite razonar sobre el comportamiento del sistema de manera modular. La arquitectura garantiza que las estrategias computacionales no interactúan directamente con la capa de entrada ni con la capa de salida, sino únicamente a través de interfaces bien definidas proporcionadas por el núcleo y la capa de evaluación.

4.4 Diagrama de arquitectura general del framework GeoMIP

El siguiente diagrama representa la arquitectura general del sistema a nivel macro, modelada por capas funcionales (ver Figura 1). Este diagrama abstrae completamente los detalles de implementación y es válido independientemente de los métodos concretos o del lenguaje utilizado.

Figura 1.Diagrama de arquitectura del sistema

El diagrama presentado en la figura 1 constituye el diagrama de arquitectura oficial del framework GeoMIP y debe utilizarse como referencia para comprender la ubicación y el rol de cada método dentro del sistema.

La figura 2 presenta la arquitectura funcional de alto nivel del framework GeoMIP. El diagrama modela el sistema mediante una organización por capas, separando el núcleo computacional común de las estrategias específicas empleadas para la resolución del problema de la MIP.

Figura 2. Diagrama de arquitectura funcional del framework GeoMIP

Esta representación abstrae los detalles de implementación y pone de manifiesto el flujo general de datos y control, así como la coexistencia de múltiples métodos computacionales dentro de una misma arquitectura.

Los detalles internos de cada estrategia computacional se describen en las secciones siguientes mediante diagramas de componentes internos alineados con el código fuente.

5. Método 1: Enfoque Geométrico–Topológico Acelerado

5.1 Objetivo computacional del método

El Método 1 implementado en GeoMIP tiene como objetivo resolver el problema de la Minimum Information Partition mediante una reformulación geométrica del espacio de estados, explotando explícitamente la estructura topológica del hipercubo binario y combinándola con técnicas de programación dinámica y paralelización.

A diferencia de enfoques exhaustivos clásicos, este método no construye explícitamente todas las dinámicas particionadas posibles. En su lugar, evalúa directamente la calidad de las particiones a partir de patrones de costos de transición entre estados, calculados sobre el hipercubo n-dimensional que representa el sistema discreto.

El método está diseñado para:

escalar a sistemas con un número elevado de variables,

aprovechar paralelización a nivel de CPU y GPU,

y mantener compatibilidad con la definición formal de pérdida basada en Earth Mover’s Distance.

5.2 Organización del código y arquitectura real

El Método 1 se implementa como un módulo autocontenido compuesto principalmente por dos archivos:

geometry.py: contiene la estrategia geométrica principal, el ciclo de ejecución y la lógica de selección de particiones.

ncube.py: implementa la estructura del hipercubo, junto con las operaciones topológicas fundamentales (distancia de Hamming, vecinos, recorridos por niveles).

No existe una separación artificial entre “modelo” y “algoritmo”; el diseño es deliberadamente compacto para minimizar sobrecarga y maximizar control sobre estructuras internas, algo habitual en software científico de alto rendimiento.

5.3 Diagrama estructura funcional Método 1

El diagrama presentado en la figura 3 refleja la estructura funcional del Método 1

Figura 3.Estructura funcional Método 1

Este diagrama muestra  que:

1.Geometry.aplicar_estrategia() es el punto de entrada del método.

2.NCube es un componente auxiliar, pero crítico, que encapsula toda la topología del espacio de estados.

3.La tabla de costos (cost_matrix) es el artefacto central que conecta la fase geométrica con la evaluación de particiones.

5.4 Clase NCube: representación del espacio de estados

La clase NCube encapsula la representación del sistema como un hipercubo binario n-dimensional, donde cada vértice corresponde a un estado posible del sistema y cada arista representa un cambio elemental (flip de un bit).

Representación de estados

Los estados se representan internamente mediante índices enteros (para acceso eficiente a tablas), y conversiones implícitas a representaciones binarias cuando se requiere cálculo topológico.

Este diseño permite que operaciones intensivas (como recorrer niveles completos del hipercubo) se realicen sin crear estructuras intermedias costosas.

Distancia de Hamming y vecindad

La función hamming_distance(i, j) calcula la distancia topológica entre dos estados, definida como el número de bits distintos entre sus representaciones binarias. Esta métrica es el eje central de todo el método, ya que define niveles de exploración, controla el decaimiento exponencial del costo y estructura el recorrido del espacio de estados.

La función get_neighbors(state) devuelve los estados adyacentes a distancia de Hamming 1, lo que permite recorrer el hipercubo por capas concéntricas.

5.4.3 Generación de estados por nivel

La función generate_states_by_level(d) permite obtener todos los estados a distancia de Hamming d desde un estado inicial. Esta funcionalidad es clave para la construcción bottom-up de la tabla de costos, evitando exploraciones redundantes.

5.5 Clase Geometry: núcleo algorítmico del Método 1

La clase Geometry implementa la estrategia geométrica completa. Su diseño sigue un patrón de macro-algoritmo coordinador, donde cada fase del cálculo está claramente delimitada pero integrada en un flujo continuo.

Método aplicar_estrategia()

Este método es el orquestador principal. Su responsabilidad es ejecutar el ciclo completo del método geométrico: 1)Preparar el subsistema (mecanismo y scope)  2)Definir el estado inicial del hipercubo, 3)Construir la tabla de costos, 4)Seleccionar la estrategia de generación de particiones, 5)Evaluar cada partición candidata mediante EMD, 6)Retornar la mejor partición encontrada.

Desde el punto de vista  técnico, este método define el contrato funcional del Método 1.

5.5.2 Construcción de la tabla de costos (build_cost_table)

La función build_cost_table() implementa un algoritmo de programación dinámica bottom-up sobre el hipercubo. El cálculo se organiza por niveles de distancia de Hamming. En el nivel 0, el costo es cero (estado inicial). En el nivel 1, el costo se calcula directamente. En niveles mayores, el costo se calcula reutilizando valores de niveles anteriores.

Este enfoque evita recalcular transiciones complejas y reduce drásticamente el número de operaciones efectivas.

Internamente, los costos se almacenan en cost_matrix, una estructura indexada que permite acceso constante durante la evaluación de particiones.

5.5.3 Paralelización

El cálculo de costos se realiza por variable del scope, lo que introduce independencia natural entre subproblemas. El código aprovecha esta propiedad para paralelizar el cálculo utilizando múltiples hilos de CPU y, cuando está disponible, operaciones vectorizadas compatibles con GPU.

Desde el punto de vista del software, la paralelización no altera la semántica del algoritmo; solo modifica el orden temporal de evaluación de subproblemas independientes.

Generación de particiones (strategy_partitions)

El método strategy_partitions() controla cómo se generan las biparticiones candidatas. El diseño es adaptativo ya que para sistemas pequeños, se emplea exploración exhaustiva y para sistemas más grandes, se utilizan estrategias heurísticas basadas en patrones de costo y simetrías del hipercubo.

Esta separación es fundamental para controlar el crecimiento exponencial del espacio de búsqueda sin romper la coherencia del framework.

5.5.5 Evaluación de particiones (evaluate_partition)

Cada partición candidata se evalúa calculando las distribuciones marginales correspondientes y midiendo la discrepancia mediante EMD, usando como costos base la cost_matrix.

El método no aproxima el cálculo de EMD: la evaluación es exacta sobre el conjunto candidato generado. Esto permite afirmar que el Método 1 optimiza la búsqueda, no la métrica.

5.6 Estructuras de datos principales del Método 1

Desde el punto de vista técnico, las estructuras críticas son:

cost_matrix: matriz de costos de transición entre estados.

partition_candidates: conjunto (o generador) de biparticiones a evaluar.

best_partition: estructura que almacena la mejor solución encontrada hasta el momento, junto con su pérdida.

Estas estructuras están diseñadas para minimizar asignaciones dinámicas y permitir reutilización durante todo el ciclo de ejecución.

Requisitos de software específicos del Método 1

El Método 1 requiere Python científico (NumPy, SciPy), soporte para paralelización en CPU y opcionalmente, entorno CUDA compatible si se habilita aceleración GPU. El código detecta automáticamente la disponibilidad de GPU y degrada a CPU-only sin comprometer la corrección funcional.

Aunque el método reduce significativamente el costo computacional frente a enfoques exhaustivos, sigue estando condicionado por el crecimiento exponencial del espacio de estados. El uso de GPU amplía el rango práctico, pero no elimina límites físicos de memoria.

Además, las estrategias heurísticas de particionado implican que, para tamaños muy grandes, el método garantiza la mejor solución dentro del conjunto explorado, no necesariamente el óptimo global absoluto.

6. Método 2: Dynamic Programming Reformulation Approach

6.1 Objetivo computacional del método

El segundo método implementado en GeoMIP tiene como objetivo resolver el problema de la MIP mediante una reformulación algorítmica que habilita programación dinámica con memoización sistemática, eliminando redundancias estructurales presentes en formulaciones recursivas tradicionales del cálculo de costos.

A diferencia del enfoque geométrico acelerado, este método no depende de paralelización masiva ni de hardware especializado. Su fortaleza reside en una reorganización matemática del problema, que permite reutilizar de forma explícita los subcálculos de costos de transición y construir la solución de manera incremental, garantizando estabilidad, reproducibilidad y eficiencia en entornos CPU-only.

Desde el punto de vista arquitectónico, este método constituye una estrategia alternativa dentro de la capa de estrategias computacionales, plenamente integrada con el núcleo IIT y la capa de evaluación descritas previamente.

6.2 Organización del código y rol de cada componente

El Método 2 presenta una organización más explícita por responsabilidades, lo cual facilita su análisis y documentación formal. El código se estructura alrededor de cuatro componentes principales:

El módulo de ejecución, que orquesta el flujo completo del método,

El modelo del sistema, que encapsula la representación del subsistema IIT,

El algoritmo central de programación dinámica y

El objeto solución, que materializa el resultado final.

Esta separación permite razonar de manera clara sobre el flujo de control y sobre la vida útil de las estructuras de datos durante la ejecución.

6.3 Diagrama de componentes internos del Método 2

El diagrama de la figura 4 refleja la estructura real del código del Método 2, mostrando los módulos y sus interacciones sin entrar en detalles de clases auxiliares o funciones internas menores.

Figura 4. Diagrama de componentes internos del Método 2

6.4 Modelo del sistema y preparación del subsistema

El módulo system.py encapsula la representación del subsistema IIT que será analizado. Su función principal es transformar la información de entrada —TPM y selección de variables— en una estructura interna coherente que pueda ser utilizada por el algoritmo de programación dinámica.

Durante esta fase se fijan decisiones críticas que afectan todo el cálculo posterior, como la codificación de los estados discretos, el orden de las variables y la correspondencia entre representaciones binarias y estados indexados. Estas decisiones se toman una única vez y permanecen invariantes durante toda la ejecución del método, lo cual es esencial para garantizar la corrección de la memoización posterior.

Desde el punto de vista del método, el sistema se concibe como un espacio de estados discreto bien definido, sobre el cual se realizará una exploración incremental guiada por la distancia de Hamming.

6.5 Reformulación del cálculo de costos y principio de programación dinámica

La contribución central del Método 2 es la reformulación del cálculo de costos de transición que subyace al problema de la MIP. En formulaciones tradicionales, los costos se calculan de manera recursiva entre múltiples pares de estados, lo que introduce dependencias cruzadas difíciles de reutilizar y conduce a recomputaciones masivas.

El Método 2 elimina esta dificultad imponiendo una estructura en la cual todos los subproblemas dependen de un mismo estado inicial. Esta decisión transforma el problema en un escenario clásico de programación dinámica, donde cada subcálculo se realiza exactamente una vez y se almacena para su reutilización.

El algoritmo central, implementado en la función FIND_MIP, construye los costos de transición de forma incremental, recorriendo el espacio de estados por niveles crecientes de distancia de Hamming.

6.6 Algoritmo FIND_MIP: recorrido por niveles de Hamming

El algoritmo FIND_MIP organiza la exploración del espacio de estados en niveles definidos por la distancia de Hamming respecto al estado inicial. En el nivel cero se encuentra el estado de partida; en niveles sucesivos se agrupan los estados que difieren en uno, dos o más bits.

Para cada nivel, el algoritmo identifica los estados alcanzables desde niveles anteriores mediante flips dirigidos, calcula el costo de transición desde el estado inicial hacia cada uno de estos estados, y almacena dicho costo en una tabla de memoización.

Este procedimiento garantiza que, cuando se requiere un subcosto para calcular un costo de nivel superior, dicho subcosto ya ha sido calculado y almacenado. De este modo, el algoritmo evita cualquier forma de recursión no controlada y convierte el cálculo en un proceso determinista y ordenado.

6.7 Estructuras de datos internas del Método 2

El correcto funcionamiento del método depende de un conjunto reducido pero crítico de estructuras de datos.

La tabla de transiciones almacena los costos de transición desde el estado inicial hacia todos los estados alcanzados. Esta tabla constituye el núcleo de la memoización y es consultada repetidamente durante la generación y evaluación de particiones.

La estructura paths, organizada por niveles de Hamming, mantiene los conjuntos de estados que se encuentran a una distancia específica del estado inicial. Esta estructura no solo guía el recorrido del espacio, sino que también impone un orden topológico estricto que garantiza la corrección del enfoque dinámico.

Adicionalmente, se mantienen estructuras auxiliares para la generación de candidatos y para el seguimiento del mejor resultado encontrado, aunque estas no dominan el costo computacional del método.

6.8 Generación de particiones candidatas y reducción del espacio de búsqueda

Una vez construida la tabla de transiciones, el método procede a generar particiones candidatas. A diferencia de enfoques exhaustivos, el Método 2 explota explícitamente simetrías del espacio del hipercubo y propiedades de equivalencia topológica para reducir el número de candidatos que deben evaluarse.

En particular, el método limita la exploración a niveles intermedios del espacio de estados, evitando evaluar configuraciones que son simétricamente redundantes respecto a otras ya consideradas. Esta reducción no altera la definición del problema, sino que elimina duplicaciones estructurales inevitables en el espacio completo.

6.9 Evaluación de particiones e integración con la capa de evaluación

Las particiones generadas por el Método 2 se evalúan utilizando la misma capa de evaluación común al framework GeoMIP. Para cada partición se calculan las distribuciones marginales correspondientes y se mide la pérdida mediante Earth Mover’s Distance, utilizando como base la tabla de costos previamente construida.

Este diseño garantiza que, aunque los métodos difieran en la forma de construir los costos y generar candidatos, la decisión final se tome bajo criterios uniformes y comparables.

6.10 Objeto solución y salida del método

El resultado del Método 2 se encapsula en un objeto Solution, que contiene la información necesaria para interpretar y reutilizar el resultado del cálculo. Este objeto incluye la partición mínima identificada, el valor de pérdida asociado y metadatos relevantes del subsistema y de la ejecución.

La existencia de un objeto solución explícito refuerza la integración del método con la arquitectura general del framework y facilita su uso en pipelines de investigación más amplios.

6.11 Requisitos de software específicos del Método 2

El Método 2 está diseñado para ejecutarse eficientemente en entornos CPU-only y no requiere soporte de GPU ni librerías específicas de aceleración. Su dependencia principal es el stack científico estándar de Python, lo que lo hace especialmente adecuado para entornos institucionales con restricciones de hardware.

El principal recurso crítico para este método es la memoria, ya que el tamaño de las estructuras de memoización crece con el número de estados del sistema.

7. Implementación en Python

7.1 Organización del repositorio y estructura del código fuente

La implementación de GeoMIP se distribuye en dos conjuntos de código claramente diferenciados desde el punto de vista organizacional, pero conceptualmente integrados dentro de una misma arquitectura de framework. Esta organización responde a la evolución del software a lo largo del desarrollo de la tesis doctoral y a la necesidad de separar una estrategia computacional especializada de un repositorio base que encapsula el núcleo reutilizable del sistema.

Desde una perspectiva técnica, el repositorio asociado al Método 1 constituye un módulo de estrategia geométrica que se apoya explícitamente en la infraestructura provista por el repositorio del Método 2, el cual contiene el núcleo computacional, los modelos fundamentales y los mecanismos de ejecución comunes. Por esta razón, el análisis de la estructura del código comienza con el módulo del Método 1 y continúa con el repositorio base.

7.1.1 Estructura del repositorio y organización de directorios del Método 1

El Método 1 se distribuye como un conjunto acotado de archivos que implementan la estrategia geométrico–topológica acelerada. Este repositorio no define un framework completo por sí mismo, sino que introduce una estrategia computacional adicional que reutiliza el núcleo de modelos, utilidades y contratos definidos en el repositorio base de GeoMIP.

La estructura del repositorio del Método 1 es deliberadamente compacta, ya que su función principal es encapsular la lógica específica del método y delegar el resto de responsabilidades al núcleo común del sistema.

GeoMip_Metodo1/

geometry.py

ncube.py

diagrama de clases.png

El archivo geometry.py contiene la implementación principal de la estrategia geométrica, incluyendo el punto de entrada del método, la construcción de la tabla de costos y la generación de particiones candidatas. Este módulo importa explícitamente componentes ubicados en el espacio de nombres src.*, lo que refleja su dependencia directa del repositorio base.

El archivo ncube.py incluido en este repositorio implementa una versión especializada de la representación del hipercubo utilizada por la estrategia geométrica. Su presencia responde a necesidades específicas del método y no reemplaza la implementación del núcleo común, sino que la complementa en contextos concretos de cálculo.

Desde el punto de vista de la arquitectura del sistema, este repositorio debe interpretarse como un módulo de extensión de la capa de estrategias computacionales, y no como una aplicación independiente.

7.1.2 Estructura del repositorio y organización de directorios del Método 2

El repositorio del Método 2 constituye el repositorio base de GeoMIP y contiene la implementación del núcleo computacional del framework, así como los mecanismos de ejecución, control y encapsulación de resultados. En este repositorio se definen las abstracciones fundamentales que permiten la integración coherente de múltiples estrategias de resolución del problema de la MIP.

La organización del código sigue una estructura modular clara, separando los modelos centrales, las estrategias computacionales, los controladores de ejecución y los servicios auxiliares.

GeoMIPMetodo2/

exec.py

README.md

LICENSE

requirements.txt

pyproject.toml

pyphi_config.yml

.docs/

application.md

.diagrams/

classes.md

components.md

src/

main.py

constants/

base.py

error.py

models.py

controllers/

manager.py

strategies/

force.py

geometric.py

phi.py

q_nodes.py

funcs/

base.py

format.py

system.py

middlewares/

profile.py

slogger.py

models/

base/

application.py

sia.py

core/

ncube.py

solution.py

system.py

enums/

distance.py

notation.py

.samples/

N3A.csv

N3B.csv

N4A.csv

...

N20A.csv

video/

hyper-v0.py

...

hyper-v8.py

En esta estructura, src/ contiene el núcleo reusable del framework, mientras que exec.py y src/main.py actúan como entrypoints para ejecución.

En esta estructura, la carpeta src/ representa el núcleo lógico del framework, y contiene tanto los modelos fundamentales como las estrategias computacionales disponibles. El subdirectorio models/core/ implementa las abstracciones centrales del sistema, mientras que models/base/ define los contratos comunes que deben respetar todas las estrategias.

El directorio controllers/strategies/ alberga las distintas estrategias computacionales implementadas en el repositorio base, incluida la reformulación basada en programación dinámica. Estas estrategias se integran con el núcleo mediante interfaces bien definidas y comparten el mismo modelo de entrada y salida.

Los archivos exec.py y src/main.py actúan como puntos de entrada para la ejecución del software, permitiendo lanzar análisis controlados y experimentales sin acoplar la lógica de ejecución a una estrategia específica.

Desde el punto de vista de la documentación técnica, este repositorio define la estructura física y lógica principal de GeoMIP, sobre la cual se integran extensiones y métodos adicionales.

7.1.3 Relación estructural entre ambos repositorios

La coexistencia de ambos repositorios refleja una decisión de diseño orientada a la reutilización y a la extensibilidad. El repositorio del Método 2 define el núcleo estable del framework, mientras que el repositorio del Método 1 introduce una estrategia adicional que se acopla a dicho núcleo sin duplicar funcionalidades.

Esta relación estructural implica que, para una instalación y ejecución consistentes, ambos conjuntos de código deben coexistir dentro de un mismo entorno de ejecución o integrarse en un único árbol de proyecto. Esta consideración se aborda de manera explícita en las secciones posteriores dedicadas a instalación y configuración.

7.2 Convenciones internas y contrato de representación

GeoMIP impone convenciones internas estrictas para garantizar que todas las estrategias operen sobre una representación común del subsistema IIT. En la implementación, la unidad fundamental de especificación del subsistema se expresa mediante cadenas binarias de igual longitud: condicion, alcance y mecanismo. Estas cadenas se interpretan como máscaras sobre las variables del sistema, y su longitud debe ser consistente con la dimensión inferida del espacio de estados. La validación de esta consistencia se centraliza en el contrato de preparación del subsistema, de manera que ninguna estrategia opere con entradas ambiguas.

El framework adopta explícitamente una notación configurable para mapear estados binarios a índices enteros. Esta convención está formalizada mediante el enumerado src/models/enums/notation.py y se utiliza al construir el objeto System. En la práctica, esta decisión gobierna el orden en el que se interpretan los bits (por ejemplo, little-endian) y, por tanto, determina la correspondencia entre un estado binario y su ubicación en los tensores o tablas internas. Las utilidades de bajo nivel que soportan esta convención aparecen en src/funcs/base.py, destacándose lil_endian(...), así como funciones auxiliares para obtener etiquetas y combinaciones restringidas (por ejemplo, get_labels(...), get_restricted_combinations(...)), que se usan para formateo y generación controlada de combinaciones.

La TPM se representa internamente como np.ndarray y se transforma a una estructura orientada a n-cubos para facilitar operaciones de condicionamiento y marginalización sin reescribir lógica tensorial en cada estrategia. Este contrato se materializa en la clase System (src/models/core/system.py) y en la clase NCube (src/models/core/ncube.py). En particular, la preparación del subsistema crea un System con parámetros tpm, estado_inicio y notacion, y desde allí todas las estrategias utilizan las mismas operaciones: System.condicionar(...), System.substraer(...), System.bipartir(...) y System.distribucion_marginal().

7.3 Inventario de módulos y responsabilidades

La organización del código fuente (establecida en la Sección 7.1) se traduce, en ejecución, en un flujo donde el núcleo (models/core) define la semántica del sistema, la base (models/base) define el contrato de estrategia y las estrategias (controllers/strategies) implementan métodos concretos. Esta separación es visible en las rutinas principales y en la forma en que se encadena la ejecución.

En el núcleo del framework, System (src/models/core/system.py) actúa como contenedor de la representación interna del subsistema. Sus métodos condicionar(...) y substraer(...) implementan la creación de candidatos y subsistemas mediante reducción controlada de dimensiones, mientras que bipartir(alcance, mecanismo) implementa la transformación a un sistema particionado. La rutina distribucion_marginal() produce la distribución marginal del sistema para el estado inicial, que es el objeto que finalmente se contrasta contra la partición durante la evaluación (por ejemplo, vía EMD).

La clase NCube (src/models/core/ncube.py) representa cada n-cubo asociado a un nodo futuro y encapsula operaciones locales como condicionar(indices_condicionados, estado_inicial) y marginalizar(ejes). En el Método 1 existe además una implementación ampliada de NCube en GeoMip_Metodo1/ncube.py con utilidades adicionales de rendimiento y copia (copy(...), contiguous_data(...), _numpy_condicionar(...)), destinada a soportar el cálculo geométrico con estructuras de costos de mayor tamaño.

En la base de estrategias, la clase SIA (src/models/base/sia.py) define el contrato funcional de todo método. La rutina más crítica es sia_preparar_subsistema(condicion, alcance, mecanismo, tpm), que valida parámetros, construye el System, deriva subsistema/candidato y fija distribuciones marginales utilizadas por la estrategia. La función chequear_parametros(candidato, futuro, presente) consolida validaciones estructurales y sirve como guardia contra configuraciones inválidas. Adicionalmente, sia_cargar_tpm() define un mecanismo estándar de carga cuando se trabaja por archivo.

En la capa de estrategias, el Método 2 se implementa como GeometricSIA en src/controllers/strategies/geometric.py. Su punto de entrada aplicar_estrategia(condicion, alcance, mecanismo, tpm) prepara el subsistema y luego ejecuta el corazón del método mediante find_mip(), apoyándose en rutinas de costo y recorrido como hamming(a, b), calcular_costos_nivel(estado_final, nivel) y calcular_costo(estado_inicial, estado_final, ncubos), para finalmente consolidar candidatos en identificar_particiones_optimas().

El Método 1 se implementa como clase Geometry en GeoMip_Metodo1/geometry.py. Esta estrategia integra el núcleo y añade construcción explícita de tabla de costos y exploración de biparticiones con métodos como create_table_cost(...), exhaustive_search(), calculate_partition_cost(...), find_optimal_bipartitions(num_vars) y estrategias de enumeración como strategy1_partitions(), strategy2_partitions() y cost_based_partitions(). La selección final se consolida mediante process_partitions(partitions).

Finalmente, el módulo src/funcs/system.py contiene generadores y utilidades de exploración combinatoria del espacio de subsistemas y biparticiones, destacándose generar_candidatos(n_vars), generar_biparticiones(alcances, mecanismos, total) y subconjuntos(arr), que sirven como soporte transversal cuando se requiere enumeración sistemática. El módulo src/funcs/format.py contiene rutinas de formateo de biparticiones (fmt_biparticion(...), fmt_biparte_q(...)) utilizadas para salida estructurada y trazabilidad.

7.4 API interna y subrutinas principales

En GeoMIP, la “API efectiva” para ejecución y extensión no se define como una interfaz pública estilo librería, sino como un conjunto de rutinas internas cuyo contrato debe mantenerse estable. En términos prácticos, la ejecución de cualquier método se apoya en tres contratos: preparación del subsistema, transformación a partición y encapsulación del resultado.

El primer contrato lo define SIA.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm). Esta rutina es el punto donde se fija la coherencia del problema: valida tamaños y consistencia lógica, construye el objeto System(tpm, estado_inicio, notacion), calcula configuraciones internas de dimensión, y fija las distribuciones marginales del subsistema. Cualquier estrategia que omita esta rutina corre el riesgo de romper convenciones de notación o de operar sobre un subsistema mal definido.

El segundo contrato lo implementa System.bipartir(alcance, mecanismo), junto con System.distribucion_marginal(). La evaluación de una partición requiere construir el sistema particionado y obtener su distribución marginal asociada; por ello, aunque cada estrategia explore candidatos de forma distinta, todas convergen en estas operaciones del núcleo para producir objetos comparables.

El tercer contrato es el encapsulamiento del resultado mediante Solution (src/models/core/solution.py). La clase Solution se construye con parámetros que registran estrategia, pérdida, distribuciones y partición, y además incorpora capacidades de representación (__str__, __repr__) y notificación opcional (__anunciar_solucion, __obtener_voz_espanol) para escenarios de ejecución interactiva o demostrativa.

Para dejarlo explícito a nivel de manual técnico, a continuación se documentan las subrutinas “ancla” con su firma as-built (en términos de argumentos) y su rol:

Base (contrato común):

SIA.sia_preparar_subsistema(self, condicion, alcance, mecanismo, tpm) establece el System y fija invariantes.

SIA.chequear_parametros(self, candidato, futuro, presente) valida consistencia interna de variables y dimensiones.

Core (transformaciones del sistema):

System.condicionar(self, indices) genera un candidato condicionado.

System.substraer(self, alcance_dims, mecanismo_dims) deriva subsistema reduciendo dimensiones.

System.bipartir(self, alcance, mecanismo) construye el sistema particionado.

System.distribucion_marginal(self) retorna la distribución marginal del sistema.

NCube.condicionar(self, indices_condicionados, estado_inicial) y NCube.marginalizar(self, ejes) realizan operaciones locales sobre tensores.

Método 2 (estrategia DP por niveles):

GeometricSIA.aplicar_estrategia(self, condicion, alcance, mecanismo, tpm) orquesta el método.

GeometricSIA.find_mip(self) ejecuta el núcleo de programación dinámica.

GeometricSIA.calcular_costos_nivel(self, estado_final, nivel) construye costos por nivel.

GeometricSIA.calcular_costo(self, estado_inicial, estado_final, ncubos) calcula el costo de transición.

GeometricSIA.identificar_particiones_optimas(self) consolida candidatos y selecciona óptimo.

GeometricSIA.hamming(self, a, b) define distancia topológica.

GeometricSIA.nodes_complement(self, nodes) opera complementos para particiones.

Método 1 (estrategia geométrica):

Geometry.aplicar_estrategia(self, condiciones, alcance, mecanismo, initial_state) orquesta el método.

Geometry.create_table_cost(self, num_mecanismo_vars, num_alcance_vars, cubos, initial_state_index) construye tabla de costos.

Geometry.exhaustive_search(self) explora particiones exhaustivamente cuando aplica.

Geometry.find_optimal_bipartitions(self, num_vars) identifica biparticiones óptimas.

Geometry.calculate_partition_cost(self, left_alcance, left_mecanismo, right_alcance, right_mecanismo) evalúa el costo de una partición concreta.

Geometry.strategy1_partitions / strategy2_partitions / cost_based_partitions implementan políticas de enumeración.

Geometry.process_partitions(self, partitions) unifica evaluación y selección final.

7.5 Diagramas de implementación

La documentación de implementación requiere diagramas diferentes a los de arquitectura macro. Aquí se incluyen tres vistas: dependencia de módulos, flujo de control (call-flow) y estructuras de datos internas. Estas vistas complementan la arquitectura por capas mostrando cómo está construido el software.

7.5.1 Dependencias entre núcleo y estrategias:

La figura 5 ilustra las dependencias entre el núcleo común a ambos métodos y los métodos.

Figura 5.Diagrama de dependencias

7.5.2 Flujo de control común de ejecución

Figura 6. Flujo del control de ejecución de los métodos

7.5.3 Estructuras  internas

Figura 7. Esquema de relaciones entre las estructuras internas

7.6 Delimitación de la API efectiva del framework

En el estado actual, la API efectiva puede definirse como el conjunto mínimo de rutinas y clases que materializan el contrato entre entrada, cálculo y salida. En concreto, GeoMIP considera estables: a) el contrato de preparación del subsistema definido por SIA.sia_preparar_subsistema(...), b) las transformaciones fundamentales del sistema implementadas por System y NCube —especialmente bipartir(...) y distribucion_marginal()—, c) el punto de entrada de cada estrategia mediante aplicar_estrategia(...), y d) el objeto de salida Solution. En cambio, las heurísticas de enumeración, las políticas de búsqueda y los detalles internos de cálculo de costos (por ejemplo, el modo exacto de construir costos por nivel o la estrategia seleccionada para generar biparticiones) se consideran parte de la implementación interna y pueden evolucionar sin romper el contrato del framework, siempre que las rutinas estables preserven su semántica.

7.7 Consideraciones de integración, extensión y mantenimiento

La extensibilidad de GeoMIP se apoya en que las estrategias son clases que implementan aplicar_estrategia(...) y reutilizan de manera obligatoria la preparación del subsistema. Por ello, incorporar un nuevo método implica crear una nueva estrategia que respete el contrato SIA y consuma el núcleo System/NCube sin duplicar operaciones de condicionamiento y marginalización. En la práctica, una nueva estrategia debe: preparar subsistema con sia_preparar_subsistema, construir su estructura interna de costos o búsqueda, generar candidatos en la forma que considere, y finalmente construir el resultado como Solution.

Para mantenimiento, la recomendación técnica es preservar el aislamiento del núcleo (models/core) y evitar introducir lógica de estrategia dentro de System o NCube, ya que eso acoplaría el framework a un método particular. Los cambios que afecten convenciones de notación deben concentrarse en models/enums/notation.py y en las utilidades relacionadas (por ejemplo, en funcs/base.py), y deben validarse de manera estricta debido a su impacto transversal. Finalmente, cualquier refactor de estrategias debe conservar el contrato: si aplicar_estrategia retorna un Solution consistente y utiliza las mismas operaciones del núcleo para construir y evaluar particiones, la evolución será compatible con la arquitectura.

8. Instalación y configuración

GeoMIP se ejecuta sobre un entorno Python científico estándar y no impone restricciones específicas sobre el sistema operativo, siempre que se disponga de un intérprete Python compatible y de las bibliotecas científicas requeridas. Se recomienda el uso de Python versión 3.8 o superior, dado que el código fuente emplea características del lenguaje y de bibliotecas que no están disponibles en versiones anteriores.

Para garantizar aislamiento de dependencias y reproducibilidad de los experimentos, se recomienda ejecutar el framework dentro de un entorno virtual. Esta práctica evita conflictos con otros proyectos y asegura que las versiones de las bibliotecas utilizadas correspondan exactamente a las declaradas por el framework.

GeoMIP puede ejecutarse bajo dos perfiles principales. El primero corresponde a un perfil CPU-only, adecuado para el Método 2 basado en programación dinámica y para la ejecución funcional del Método 1 cuando no se dispone de hardware especializado. El segundo corresponde a un perfil acelerado, en el cual el Método 1 puede aprovechar paralelización multinúcleo y, de forma opcional, aceleración por GPU compatible con CUDA. En ausencia de GPU, el método geométrico mantiene corrección funcional degradando su ejecución a CPU.

Las dependencias de software necesarias para la ejecución del framework se encuentran declaradas en los archivos de configuración del repositorio base y deben instalarse previamente a la ejecución. Los detalles específicos sobre la instalación de dependencias y la configuración del entorno de ejecución se describen de manera exhaustiva en el Manual de Usuario.


---

# Criterios de Evaluacion_Documentación


Universidad de Caldas

ESPECIFICACIONES DE ENTREGABLES

Proyecto K-QGMIP:

Criterios de evaluación de la documentación

Análisis y Diseño de Algoritmos

Facultad de Inteligencia Artificial e Ingenierías

2026-1

# Criterios de Evaluación de la Documentación

La documentación (Manual Técnico y Manual de Usuario) representa una porción significativa de la evaluación del proyecto. A continuación se detallan los criterios específicos que se utilizarán para evaluar cada manual.

## 1 Evaluación del Manual Técnico

Rigor matemático y claridad conceptual: Precisión en definiciones, corrección de formulaciones matemáticas, claridad en explicaciones de conceptos complejos.

Calidad de arquitectura y diagramas: Completitud de diagramas UML, corrección en notación, claridad visual, y utilidad para comprender la estructura del código.

Calidad de la descripción algorítmica: Completitud del pseudocódigo, claridad en explicación de decisiones de diseño, facilidad de reproducción del algoritmo.

Análisis de complejidad: Corrección del análisis teórico, identificación precisa de cuellos de botella, validación empírica del análisis.

Resultados experimentales: Comprehensividad de experimentos, calidad de visualizaciones, profundidad del análisis e interpretación.

Reflexión crítica: Honestidad sobre limitaciones, identificación de mejoras potenciales, demostración de comprensión profunda.

## 2 Evaluación del Manual de Usuario

Claridad y accesibilidad: Lenguaje apropiado y sencillo, explicaciones intuitivas de conceptos complejos, evita jerga innecesaria.

Completitud de instrucciones: Cobertura de todos los pasos necesarios, detalle suficiente para reproducir operaciones, anticipación de problemas comunes.

Calidad del video tutorial: Claridad de grabación, completitud del contenido, calidad de subtítulos (si aplica).

Calidad de ejemplos y tutoriales : Casos de ejemplo relevantes, claridad en presentación paso a paso.

Material de soporte: Calidad y cantidad de capturas de pantalla, diagramas de flujo útiles (si es del caso), sección de “Solución de problemas” efectiva.

Usabilidad del documento: Organización lógica, facilidad de navegación, índice y tabla de contenidos útiles.

## 3 Aspectos Transversales

Criterios que aplican a ambos manuales:

Calidad de redacción : Gramática y ortografía, coherencia y fluidez en la argumentación, estructura lógica de ideas.

Calidad de presentación: Formato claro y consistente, figuras y tablas de buena calidad, cumplimiento de especificaciones de formato.

Completitud: Cobertura de todos los aspectos requeridos, ausencia de secciones incompletas.

Profesionalismo: Nivel de detalle apropiado, citación apropiada de fuentes.

# Recomendaciones Finales

## 1 Proceso de Desarrollo de la Documentación

Se recomienda fuertemente desarrollar la documentación de manera iterativa y paralela al código, no como una actividad de última hora. Escribir explicaciones de algoritmos y decisiones de diseño mientras se está implementando ayuda a clarificar el propio pensamiento y a detectar problemas tempranamente.

Dedicar tiempo específico cada que se avanza en el proyecto a la documentación. Una buena regla empírica es que por cada hora de codificación, se debe invertir al menos 30 minutos en documentación, es solo una regla que les pongo para que lo tengan en cuenta. Esto resulta en mejor código y documentación de mayor calidad con menor esfuerzo total al final del proyecto.

## 2 Revisión y Refinamiento

Antes de la entrega final, realizar revisiones en todos los aspectos.

## 3 Recursos y Herramientas

Para facilitar la creación de documentación de calidad, se recomiendan las siguientes herramientas:

Para ecuaciones: LaTeX (Overleaf online), MathType, o editor de ecuaciones de Word.

Para diagramas UML: Draw.io, Lucidchart, PlantUML, Visual Paradigm, o StarUML.

Para gráficas: Matplotlib/Seaborn (Python), ggplot2 (R), o herramientas de visualización interactiva.

Para capturas de pantalla: Lightshot, Snagit, Greenshot, o herramientas nativas del sistema operativo con capacidades de anotación.

Para video: OBS Studio (gratuito), Camtasia, ScreenFlow, o Loom. Para edición: DaVinci Resolve (gratuito), Adobe Premiere, o iMovie.

Para subtítulos: YouTube Studio (automático), Subtitle Edit, Aegisub, o herramientas online como Kapwing.

Para control de versiones: Usar Git no solo para código sino también para documentación, permitiendo rastrear cambios y colaborar efectivamente.

Les aclaro que he usado varias de estas herramientas pero otras  han sido sugeridas por la IA como las de subtitulos y capturas de pantalla.

## 4 Convenciones de Nomenclatura en la Documentación

Asegurarse de usar consistentemente los nombres KGeoMIP y KQNodes a lo largo de toda la documentación, diagramas, código, y video tutorial. Esta consistencia facilita la comprensión y navegación del proyecto.

## 5 Contacto y Consultas

Si durante el desarrollo de la documentación surgen dudas sobre qué incluir, nivel de detalle apropiado, o interpretación de estos requisitos, pueden consultarme. Es preferible aclarar dudas tempranamente que entregar documentación que no cumple con las expectativas.

Estas especificaciones son detalladas pero no rígidas. Se valora la iniciativa y creatividad en la presentación de la información, siempre que se cubran todos los aspectos requeridos y se mantenga claridad y rigor apropiados.

Recuerden que:

La documentación de calidad es una habilidad profesional fundamental. El esfuerzo invertido en desarrollar estos manuales no solo contribuye a la evaluación del proyecto, sino que representa práctica valiosa en comunicación técnica que será esencial en la carrera profesional futura.


---

# Manual_Técnico_KQMIP


Universidad de Caldas

ESPECIFICACIONES DE ENTREGABLES

Proyecto K-QGMIP: Manual Técnico

Análisis y Diseño de Algoritmos

Facultad de Inteligencia Artificial e Ingenierías

2026-1

# Introducción

Como parte integral del proyecto K-QGMIP, cada equipo debe entregar documentación técnica completa que permita comprender el trabajo desarrollado. Esta documentación se refiere al Manual Técnico, que trata los aspectos algorítmicos y de implementación del proyecto.

La calidad de la documentación es un criterio de evaluación fundamental, ya que refleja la profundidad de comprensión del problema, la capacidad de comunicar las estrategias complejas de manera efectiva, y la claridad con la que se aborda el desarrollo de software. Un buen proyecto se refuerza con documentación clara, completa y efectiva que potencia significativamente el impacto del trabajo realizado.

Este documento especifica en detalle los requisitos, estructura y contenido que deben tener este manual.

# Convenciones de Nomenclatura

Para mantener consistencia y facilitar la organización del código, se establecen las siguientes convenciones de nomenclatura para los repositorios y carpetas del proyecto:

Estas convenciones deben aplicarse consistentemente en:

Nombre del repositorio Git

Carpeta principal del proyecto

Nombre de la clase principal que implementa la estrategia

Referencias en documentación y presentaciones

La 'K' inicial hace referencia a 'k-particiones', distinguiendo claramente estas extensiones de las implementaciones originales de bi-particiones (GeoMIP y QNodes).

# Manual Técnico

## 1 Propósito

El Manual Técnico está orientado a la comprension  de los aspectos algorítmicos, matemáticos e implementación del proyecto. Este documento debe permitir tener un panorama claro del software desarrollado y/o modificado, asi como la estructura del mismo.

## 2 Estructura y Contenido Requerido

### 2.1 Resumen Ejecutivo

Aqui se debe incluir:

Descripción concisa del problema abordado y su relevancia

Enfoque algorítmico implementado en términos generales

Principales resultados obtenidos y contribuciones del proyecto

Limitaciones encontradas y recomendaciones de uso

### 2.2 Fundamentos Teóricos

Esta sección debe proporcionar la base matemática y conceptual necesaria para comprender el proyecto. Contenido requerido:

Definición formal de k-particiones: Notación matemática precisa, propiedades fundamentales, y ejemplos ilustrativos para casos pequeños (n=3 o n=4).

Formulación del problema de optimización: Función o funciones objetivo a optimizar , restricciones del problema.

Extensión del marco teórico: Explicación clara de cómo se extiende el marco de GeoMIP y/o QNodes de bi-particiones a k-particiones. Justificación deque sus estrategias son aplicables y que obtienen una “buena” respuesta.

Análisis de complejidad del espacio de soluciones: Análisis del crecimiento del problema  y comparación con el caso de bi-particiones.

### 2.3 Arquitectura del Software

Descripción comprehensiva de la arquitectura del sistema implementado. Esta sección es fundamental para comprender la organización del código y facilitar futuras extensiones. Debe incluir:

Diagrama de Arquitectura General: Representación visual de los componentes principales del sistema y sus interrelaciones. Mostrar cómo se integra la extensión k-particiones con la infraestructura existente del proyecto.

Diagrama de Clases: Diagrama UML mostrando:

Clase base SIA y su relación de herencia con KGeoMIP y KQNodes

Clases auxiliares y estructuras de datos (N-Cubos, gestores de particiones, etc.)

Atributos principales de cada clase con sus tipos

Métodos públicos y privados más importantes

Relaciones de composición, agregación y dependencia

Diagrama de Paquetes: Organización modular del código mostrando:

Estructura de directorios del proyecto (src/controllers/strategies/, src/models/, src/utils/, etc.)

Dependencias entre paquetes y módulos

Ubicación de archivos de configuración, tests, y documentación

Diagrama de Secuencia: Uno o más diagramas UML de secuencia mostrando el flujo de ejecución para casos de uso principales:

Inicialización del sistema y carga de datos

Búsqueda de k-MIP para un valor específico de k

Evaluación de una k-partición candidata

Interacción entre componentes principales durante la ejecución

Patrones de Diseño Aplicados: Identificación y justificación de patrones de diseño utilizados (Strategy, Template Method, Factory, etc.) y cómo facilitan la extensibilidad y mantenibilidad del código.

Decisiones Arquitectónicas Clave: Explicación de decisiones importantes de diseño tomadas, como por ejemplo: Estrategia de reutilización de componentes existentes (o si se reimplementaron), trade-offs considerados entre flexibilidad y rendimiento, separación de responsabilidades entre componentes etc.

Observación: Todos los diagramas deben ser claros, legibles y seguir notación UML estándar.

### 2.4 Diseño Algorítmico

Descripción detallada del enfoque algorítmico implementado. Esta es la sección central del manual técnico y debe permitir reproducir el algoritmo. Debe incluir:

Visión general del algoritmo: Descripción en alto nivel del enfoque, filosofía de diseño, y cómo se relaciona con las estrategias GeoMIP y QNodes originales.

Pseudocódigo detallado: Algoritmos principales y subrutinas clave presentados en pseudocódigo claro y bien comentado. Usar notación consistente con la sección de fundamentos teóricos.

Estructuras de datos: Descripción de las estructuras de datos utilizadas (N-Cubos, tabla de costos, representación de particiones, etc.), justificación de elecciones de diseño, y diagramas cuando sea apropiado.

Estrategia de búsqueda: Explicación detallada de cómo se genera y explora el espacio de k-particiones candidatas. Técnicas de diseño empleadas (PD, DyV, voraz, B&B, aproximados, etc).Si se utilizan  heurísticas, describir su funcionamiento y justificación.

Evaluación de particiones: Procedimiento para calcular la pérdida de información de una k-partición candidata.

Optimizaciones implementadas: Técnicas específicas para mejorar eficiencia (caching, paralelización, etc.)

### 2.5 Análisis de Complejidad

Análisis teórico riguroso de la complejidad computacional del algoritmo:

Complejidad temporal: Expresión usando cotas asintóticas fuertes usando  la notación asintótica en función de n (número de variables) y k (número de particiones). Identificar operaciones dominantes y cuellos de botella.

Complejidad espacial: Análisis del uso de memoria, considerando estructuras de datos permanentes y temporales.

Análisis de casos: Mejor caso y peor caso. Identificar qué características del sistema o valor de k conducen a cada caso.

Comparación con alternativas: Contrastar la complejidad con búsqueda exhaustiva, o la fuerza bruta y con las estrategias originales para bi-particiones.

### 2.6 Detalles de Implementación

Aspectos específicos de la implementación en el lenguaje de programación utilizado (Python):

Métodos principales: Descripción de la funcionalidad de cada método público importante, incluyendo firmas de función, parámetros, valores de retorno y excepciones.

Dependencias externas: Bibliotecas utilizadas (NumPy, SciPy, etc.), versiones requeridas, y para que su uso.

Aspectos de ingeniería de software: Manejo de errores, logging, validación de inputs, y estrategias para debugging.

Tests implementados: Descripción de tests unitarios y de integración, casos de prueba específicos, y estrategia de validación.

### 2.7 Resultados Experimentales

Presentación  de resultados obtenidos en evaluación experimental:

Datasets utilizados: Descripción de sistemas de prueba, características relevantes (tamaño, origen, etc.).

Métricas de evaluación: Definición clara de métricas utilizadas (tiempo de ejecución, tasa de acierto, error relativo, speedup, etc.).

Tablas de resultados: Tablas bien formateadas con resultados numéricos para diferentes combinaciones de n y k. Incluir desviaciones estándar donde sea apropiado.

Gráficas y visualizaciones: Gráficos de escalabilidad (tiempo vs n, tiempo vs k), curvas de precisión, visualizaciones de k-particiones encontradas sobre hipercubos, y comparaciones con métodos baseline.

Análisis de resultados: Interpretación de patrones observados, discusión de casos donde el algoritmo funciona mejor/peor, y comparación entre estrategias KGeoMIP y KQNodes.

Validación de correctitud: Evidencia de que los resultados son correctos, incluyendo comparación con búsqueda exhaustiva para casos pequeños y verificación de consistencia para k=2.

### 2.8 Limitaciones y Trabajo Futuro

Reflexión crítica sobre el trabajo realizado:

Limitaciones conocidas: Restricciones del enfoque actual, casos donde no funciona óptimamente, y limitaciones de escalabilidad.

Supuestos y restricciones: Suposiciones hechas durante el desarrollo que podrían no cumplirse en todos los contextos.

Mejoras potenciales: Ideas específicas para optimizar el algoritmo, extender funcionalidad, o mejorar robustez.

Direcciones de investigación futura: Preguntas abiertas y extensiones interesantes del trabajo actual.

### 2.9 Apéndices Técnicos

Material complementario que apoya el documento principal:

Demostracioness: Pruebas detalladas de proposiciones mencionadas en el texto principal pero cuyo desarrollo completo interrumpiría el flujo.

Detalles algorítmicos adicionales: Pseudocódigo de funciones auxiliares, optimizaciones menores, o variantes exploradas.

Resultados experimentales de las pruebas: Tablas completas de resultados, experimentos adicionales no incluidos en el cuerpo principal, y análisis de sensibilidad de parámetros.

Referencias y bibliografía: Lista completa de artículos, libros y recursos consultados, con formato académico apropiado.

## 3 Características de Formato y Presentación

El Manual Técnico debe cumplir con los siguientes estándares de formato:

Formato: Documento PDF o Word, tamaño carta,  fuente Arial o Times New Roman de 11 puntos.

Ecuaciones y notación matemática: Por faaaaavor usar editores de ecuaciones apropiados (LaTeX, MathType, o el editor de ecuaciones de Word). Mantener notación consistente en todo el documento.

Diagramas UML: Todos los diagramas deben seguir notación UML 2.x estándar. Usar colores moderadamente para mejorar legibilidad. Cada diagrama o figura en el documento  debe estar numerado y tener título descriptivo.

Figuras y tablas: Todas numeradas secuencialmente, con títulos descriptivos. Incluir referencias en el texto. Verificar la calidad de la imagen, que sea  apropiada para su revisión.

Código y pseudocódigo: Usar fuente monoespaciada (Courier New, Consolas), con sangrado consistente y resaltado de sintaxis cuando sea posible.

Organización: Tabla de contenidos al inicio, numeración de secciones clara, encabezados distintivos, y páginas numeradas.

Calidad de redacción: Lenguaje técnico preciso, gramática y ortografía correctas, argumentación lógica, coherente, y claridad expositiva.

## 4 Uso de Inteligencia Artificial Generativa

# Es importante documentar de manera transparente el uso de herramientas de IA generativa (ChatGPT, Claude, GitHub Copilot, etc.) durante el desarrollo del proyecto. Si se utilizaron estas herramientas, se debe incluir una subsección que especifique: qué herramientas se utilizaron y en qué etapas del proyecto (diseño de algoritmos, implementación, debugging, optimización, documentación), ejemplos específicos de prompts o consultas realizadas y cómo influyeron en decisiones de diseño, qué partes del código o pseudocódigo fueron generadas o significativamente influenciadas por IA, y una reflexión crítica sobre las ventajas y limitaciones encontradas al usar estas herramientas. Esta documentación no afecta negativamente la evaluación; por el contrario, demuestra profesionalismo, honestidad académica y capacidad de usar herramientas modernas de manera efectiva. Lo que se evalúa es la comprensión profunda del trabajo realizado y la capacidad de justificar decisiones algorítmicas, independientemente de las herramientas utilizadas para llegar a ellas.


---

# Manual_Usuario_KQMIP


Universidad de Caldas

ESPECIFICACIONES DE ENTREGABLES

Proyecto K-QGMIP: Manual de Usuario

Análisis y Diseño de Algoritmos

Facultad de Inteligencia Artificial e Ingenierías

2026-1

# Introducción

Como parte integral del proyecto K-QGMIP, cada equipo debe entregar documentación técnica completa que permita comprender el trabajo desarrollado. En particular  el Manual de Usuario, está orientado a usuarios finales que necesitan operar el software de forma rápida siguiendo un orden en la ejecución.

La calidad de la documentación es un criterio de evaluación fundamental, ya que refleja la profundidad de comprensión del problema, la capacidad de comunicar las estrategias complejas de manera efectiva, y la claridad con la que se aborda el desarrollo de software. Un buen proyecto se refuerza con documentación clara, completa y efectiva que potencia significativamente el impacto del trabajo realizado.

Este documento especifica en detalle los requisitos, estructura y contenido que deben tener el manual de usuario.

# Convenciones de Nomenclatura

Para mantener consistencia y facilitar la organización del código, se establecen las siguientes convenciones de nomenclatura para los repositorios y carpetas del proyecto:

Estas convenciones deben aplicarse consistentemente en:

Nombre del repositorio Git

Carpeta principal del proyecto

Nombre de la clase principal que implementa la estrategia

Referencias en documentación y presentaciones

La 'K' inicial hace referencia a 'k-particiones', distinguiendo claramente estas extensiones de las implementaciones originales de bi-particiones (GeoMIP y QNodes).

# Manual de Usuario

## 1. Propósito

El Manual de Usuario está dirigido a usuarios finales que necesitan utilizar el software desarrollado sin entrar en los detalles algorítmicos internos. Este documento debe permitir a un usuario  instalar, configurar y utilizar el software exitosamente para analizar los sistemas propios.

## 2. Estructura y Contenido Requerido

### 2.1 Introducción y Visión General

Presentación accesible del software y sus capacidades:

Qué hace el software: Explicación en lenguaje sencillo cual es la funcionalidad principal (encontrar k-particiones óptimas de sistemas).

Para qué sirve: Aplicaciones prácticas y casos de uso típicos.

Conceptos básicos: Explicación intuitiva de qué es una k-partición y qué significa 'partición de mínima información', sin matemáticas avanzadas.

Capacidades y limitaciones: Qué puede y qué no puede hacer el software, tamaños de sistema que puede manejar razonablemente.

### 2.2 Requisitos del Sistema

Especificaciones técnicas mínimas y recomendadas:

Sistema operativo: Versiones de Windows, macOS o Linux soportadas.

Hardware: Procesador (velocidad y núcleos recomendados), memoria RAM (mínima y recomendada según tamaño de sistema a analizar), y espacio en disco.

Software: Versión de Python requerida, bibliotecas necesarias con versiones específicas, y herramientas adicionales si las hay.

### 2.3 Instalación Paso a Paso

Guía detallada y secuencial para instalar el software:

Descarga del proyecto: Dónde obtener el código fuente (repositorio Git, archivo comprimido, etc.), instrucciones específicas de descarga.

Instalación de dependencias: Comandos exactos para instalar Python y bibliotecas necesarias, manejo de entornos virtuales, y solución a problemas comunes de instalación.

Configuración inicial: Archivos de configuración que deben modificarse, variables de entorno necesarias, y verificación de instalación correcta.

Capturas de pantalla: Imágenes mostrando cada paso del proceso de instalación, especialmente en puntos donde usuarios suelen tener dudas.

### 2.4 Video Tutorial de Instalación y Uso

Cada equipo debe producir un video demostrativo que facilite la comprensión del proceso de instalación y uso básico del software.

Características del video:

Duración: Entre 8 y 15 minutos. Debe ser suficientemente detallado pero conciso.

Contenido obligatorio:

Proceso completo de instalación desde cero en un sistema limpio

Configuración inicial del entorno

Ejecución de al menos un ejemplo completo mostrando:

- Preparación de datos de entrada

- Ejecución del programa con diferentes valores de k

- Interpretación de los resultados obtenidos

Visualización de resultados

Calidad técnica:

Captura de pantalla clara y legible (les dejo esta que es una buena resolución, ojalá mínimo 1280x720)

Audio claro si se incluye narración en vivo, o

Subtítulos en español y deben sincronizarse correctamente con el contenido (si no hay narración)

Zoom apropiado en secciones donde se muestra código o comandos

Edición básica para eliminar tiempos muertos o errores

Formato de entrega:

Entregar el archivo de video en formato MP4

Herramientas sugeridas:  OBS Studio (gratuito), Camtasia, ScreenFlow, o herramientas similares de captura y edición de pantalla. Para subtítulos: YouTube Studio o herramientas de subtitulado como Subtitle Edit. Esas son algunas algunas herramientas que les sugiero, pero ustedes pueden usar las herramientas  que mejor les parezcan.

OJO: El video es un complemento esencial al manual escrito. Muchos usuarios aprenden mejor viendo el proceso en acción que leyendo instrucciones. Un video bien producido es una gran ayuda para lograr usar el software exitosamente de forma rápida.

### 2.5 Guía de Uso Básico

Instrucciones para realizar las operaciones más comunes:

Preparación de datos de entrada: Formato exacto requerido para especificar sistemas (archivos de texto, JSON, matrices, etc.), ejemplos de archivos de entrada válidos, y herramientas para generar o convertir datos.

Ejecución básica: Comando o interfaz para ejecutar el análisis, parámetros básicos necesarios (valor de k, sistema a analizar), y ejemplo completo de ejecución desde inicio hasta fin.

Interpretación de resultados: Qué información produce el software, cómo leer la salida (k-partición encontrada, valor de pérdida, etc.), y ejemplos de salidas típicas explicadas.

Casos de uso típicos: Escenarios comunes paso a paso (encontrar 3-partición de sistema pequeño, comparar particiones para diferentes k, etc.).

### 2.6 Opciones y Parámetros Avanzados

Configuraciones opcionales para usuarios experimentados:

Parámetros de configuración: Lista completa de parámetros ajustables, descripción de qué controla cada parámetro, valores por defecto y rangos recomendados.

Modos de operación: Si el software tiene múltiples modos (búsqueda exhaustiva, heurística, modo debug, etc.), explicar cada uno y cuándo usarlo.

Opciones de salida: Formatos de salida disponibles, nivel de detalle configurable, y opciones de visualización.

Optimización de rendimiento: Consejos para ajustar parámetros según recursos disponibles, trade-offs entre precisión y velocidad.

### 2.7 Solución de Problemas

Diagnóstico y resolución de problemas comunes:

Errores comunes: Lista de mensajes de error frecuentes, qué significa cada error, y cómo solucionarlo.

Problemas de instalación: Dependencias faltantes, conflictos de versiones, y problemas específicos por sistema operativo.

Problemas de ejecución: El programa no inicia, se cuelga durante ejecución, consume memoria excesiva, produce resultados inesperados.

Datos de entrada problemáticos: Validación de formato, detección de errores en especificación del sistema, y ejemplos de corrección.

### 2.8 Ejemplos y Tutoriales

Casos prácticos completos que ilustran el uso del software:

Tutorial básico: Análisis paso a paso de un sistema simple (3-4 nodos), incluyendo preparación de datos, ejecución, e interpretación de resultados.

Caso de estudio intermedio: Sistema de tamaño moderado (8-10 nodos), explorando diferentes valores de k y comparando resultados.

Ejemplo avanzado: Uso de parámetros avanzados, optimización de rendimiento para sistema grande, y análisis detallado de resultados.

### 2.9 Referencia Rápida

Material de consulta rápida, si es del caso:

Comandos principales: Lista de comandos con sintaxis y breve descripción.

Tabla de parámetros: Referencia tabular de todos los parámetros con valores por defecto y rangos válidos.

Formato de archivos: Especificación técnica concisa de formatos de entrada y salida.

Glosario: Definiciones breves de términos técnicos utilizados en el manual.

## 2.10 Características de Formato y Presentación

El Manual de Usuario debe cumplir con los siguientes estándares de formato:

Extensión: Debe ser suficientemente completo pero conciso.

Formato: Documento  word, tamaño carta,  fuente Arial o Calibri de 11puntos.

Lenguaje: Claro y accesible, evitando jerga técnica innecesaria. Cuando se usen términos técnicos, definirlos la primera vez.

Capturas de pantalla: Abundantes y de alta calidad. Marcar elementos relevantes con anotaciones cuando sea necesario.

Ejemplos de código: Usar fuente monoespaciada, con comentarios explicativos. Limitar longitud de ejemplos a lo esencial.

Organización visual: Uso de cajas de texto, íconos, o colores para destacar advertencias, notas importantes, o tips.

Navegación: Tabla de contenidos con hipervínculos, índice si es extenso, y referencias cruzadas claras entre secciones.

Video tutorial: Enlace prominente al video en las primeras páginas del manual, idealmente en la sección de instalación.

Usabilidad: El manual debe ser completamente auto-contenido. La idea es que no debo necesitar buscar información adicional para operaciones básicas.

# Criterios de Evaluación de la Documentación

La documentación (Manual Técnico y Manual de Usuario) representa una porción significativa de la evaluación del proyecto. A continuación se detallan los criterios específicos que se utilizarán para evaluar cada manual.

## 3.1 Evaluación del Manual Técnico (40% de la nota de documentación)

Rigor matemático y claridad conceptual: Precisión en definiciones, corrección de formulaciones matemáticas, claridad en explicaciones de conceptos complejos.

Calidad de arquitectura y diagramas: Completitud de diagramas UML, corrección en notación, claridad visual, y utilidad para comprender la estructura del código.

Calidad de la descripción algorítmica: Completitud del pseudocódigo, claridad en explicación de decisiones de diseño, facilidad de reproducción del algoritmo.

Análisis de complejidad: Corrección del análisis teórico, identificación precisa de cuellos de botella, validación empírica del análisis.

Resultados experimentales: Comprehensividad de experimentos, calidad de visualizaciones, profundidad del análisis e interpretación.

Reflexión crítica: Honestidad sobre limitaciones, identificación de mejoras potenciales, demostración de comprensión profunda.

## 3.2 Evaluación del Manual de Usuario (30% de la nota de documentación)

Claridad y accesibilidad (25%): Lenguaje apropiado para audiencia no técnica, explicaciones intuitivas de conceptos complejos, evita jerga innecesaria.

Completitud de instrucciones (25%): Cobertura de todos los pasos necesarios, detalle suficiente para reproducir operaciones, anticipación de problemas comunes.

Calidad del video tutorial (20%): Claridad de grabación, completitud del contenido, efectividad pedagógica, calidad de subtítulos (si aplica).

Calidad de ejemplos y tutoriales (15%): Casos de uso realistas y relevantes, claridad en presentación paso a paso, utilidad pedagógica.

Material de soporte (10%): Calidad y cantidad de capturas de pantalla, diagramas de flujo útiles, sección de troubleshooting efectiva.

Usabilidad del documento (5%): Organización lógica, facilidad de navegación, índice y tabla de contenidos útiles.

## 3.3 Aspectos Transversales (30% de la nota de documentación)

Criterios que aplican a ambos manuales:

Calidad de redacción (40%): Gramática y ortografía impecables, coherencia y fluidez en la argumentación, estructura lógica de ideas.

Calidad de presentación (30%): Formato profesional y consistente, figuras y tablas de alta calidad, cumplimiento de especificaciones de formato.

Completitud (20%): Cobertura de todos los aspectos requeridos, ausencia de secciones incompletas o placeholder text.

Profesionalismo (10%): Nivel de detalle apropiado, balance entre exhaustividad y concisión, citación apropiada de fuentes.

# 4. Recomendaciones Finales

## 4.1 Proceso de Desarrollo de la Documentación

Se recomienda fuertemente desarrollar la documentación de manera iterativa y paralela al código, no como una actividad de última hora. Escribir explicaciones de algoritmos y decisiones de diseño mientras se está implementando ayuda a clarificar el propio pensamiento y a detectar problemas tempranamente.

Dedicar tiempo específico cada semana a documentación. Una buena regla empírica es que por cada hora de codificación, se debe invertir al menos 30 minutos en documentación. Esto resulta en mejor código y documentación de mayor calidad con menor esfuerzo total al final del proyecto.

## 4.2 Revisión y Refinamiento

Antes de la entrega final, realizar múltiples rondas de revisión:

Revisión técnica: Verificar corrección de todas las afirmaciones matemáticas y algorítmicas. Validar que pseudocódigo sea reproducible.

Revisión de usabilidad: Idealmente, pedir a alguien ajeno al equipo que siga el Manual de Usuario para validar que las instrucciones son claras y completas.

Revisión de diagramas: Verificar que todos los diagramas UML sigan notación estándar, sean legibles, y correspondan fielmente al código implementado.

Revisión del video: Ver el video completo varias veces, verificar sincronización de subtítulos, y asegurar que todos los pasos sean claros y reproducibles.

Revisión de estilo: Corrección exhaustiva de gramática, ortografía y estilo. Verificar consistencia en terminología a lo largo de todo el documento.

Revisión de formato: Verificar que figuras estén numeradas correctamente, referencias cruzadas funcionen, tabla de contenidos esté actualizada.

## 4.3 Recursos y Herramientas

Para facilitar la creación de documentación de alta calidad, se recomiendan las siguientes herramientas:

Para ecuaciones: LaTeX (Overleaf online), MathType, o editor de ecuaciones de Word.

Para diagramas UML: Draw.io, Lucidchart, PlantUML, Visual Paradigm, o StarUML.

Para gráficas: Matplotlib/Seaborn (Python), ggplot2 (R), o herramientas de visualización interactiva.

Para capturas de pantalla: Lightshot, Snagit, Greenshot, o herramientas nativas del sistema operativo con capacidades de anotación.

Para video: OBS Studio (gratuito), Camtasia, ScreenFlow, o Loom. Para edición: DaVinci Resolve (gratuito), Adobe Premiere, o iMovie.

Para subtítulos: YouTube Studio (automático), Subtitle Edit, Aegisub, o herramientas online como Kapwing.

Para control de versiones: Usar Git no solo para código sino también para documentación, permitiendo rastrear cambios y colaborar efectivamente.

## 4.4 Convenciones de Nomenclatura en la Documentación

Asegurarse de usar consistentemente los nombres KGeoMIP y KQNodes a lo largo de toda la documentación, diagramas, código, y video tutorial. Esta consistencia facilita la comprensión y navegación del proyecto.

## 4.5 Contacto y Consultas

Si durante el desarrollo de la documentación surgen dudas sobre qué incluir, nivel de detalle apropiado, o interpretación de estos requisitos, los equipos deben consultar con el profesor de la asignatura. Es preferible aclarar dudas tempranamente que entregar documentación que no cumple con las expectativas.

Estas especificaciones son detalladas pero no rígidas. Se valora la iniciativa y creatividad en la presentación de la información, siempre que se cubran todos los aspectos requeridos y se mantenga claridad y rigor apropiados.

La documentación de calidad es una habilidad profesional fundamental. El esfuerzo invertido en desarrollar estos manuales no solo contribuye a la evaluación del proyecto, sino que representa práctica valiosa en comunicación técnica que será esencial en la carrera profesional futura.


---


# Algoritmo Geométrico K_QGMIP

## Análisis y Diseño de Algoritmos
### Proyecto 2026-1

---

# Proyecto_KQMIP

## Tabla de Contenido

1. Introducción  
1.1 Contexto del Proyecto  

2. Fundamentos Teóricos de k-Particiones  
2.1 Definición Formal de k-Particiones  
2.2 Complejidad del Espacio de k-Particiones  
2.3 Interpretación Geométrica de k-Particiones  

3. Planteamiento del Problema  
3.1 Formulación Matemática del Problema  
3.2 Restricciones y Consideraciones  
3.3 Alcance del Proyecto  

4. Entregables del Proyecto  
4.1 Componentes de Software  
4.2 Documentación Técnica  
4.3 Resultados Experimentales  
4.4 Presentación Final  
4.5 Criterios de Evaluación  

5. Observaciones Finales

---

# 1. Introducción

En trabajos anteriores se ha desarrollado la implementación de algoritmos eficientes para resolver el problema de la Partición de Mínima Información (MIP) en el contexto de la Teoría de la Información Integrada (IIT). Específicamente, se trabajó con el algoritmo QNodes, basado en la minimización de funciones submodulares mediante el algoritmo de Queyranne, y posteriormente se desarrolló la estrategia geométrica GeoMIP, que reformula el problema aprovechando la correspondencia natural entre estados binarios del sistema y vértices de un hipercubo n-dimensional.

Ambas estrategias han demostrado reducciones significativas en la complejidad computacional respecto a los métodos exhaustivos tradicionales, permitiendo el análisis de sistemas con hasta 20-23 nodos en tiempos razonables. Sin embargo, estas implementaciones se han centrado exclusivamente en el caso de bi-particiones, donde el sistema se divide en exactamente dos partes independientes.

El presente proyecto propone extender tanto las estrategias geométrica GeoMIP como QNodes al caso general de k-particiones, donde el sistema puede dividirse en k partes independientes con k ≥ 2.

## 1.1 Contexto del Proyecto

La Teoría de la Información Integrada (IIT) proporciona un marco matemático riguroso para cuantificar la conciencia en sistemas físicos. Un componente fundamental de esta teoría es el concepto de Partición de Mínima Información (MIP), que identifica cómo debe dividirse un sistema para minimizar la pérdida de información integrada.

La estrategia QNodes logra reducir la complejidad de O(2ⁿ) a O(N³) mediante el algoritmo de Queyranne. Por su parte, GeoMIP reformula el problema utilizando una representación del espacio de estados como un hipercubo n-dimensional.

---

# 2. Fundamentos Teóricos de k-Particiones

## 2.1 Definición Formal de k-Particiones

Consideremos un sistema V compuesto por n variables binarias. Una k-partición del sistema es una división de V en k subconjuntos disjuntos S₁, S₂, ..., Sₖ tales que:

- La unión de todos los subconjuntos es igual a V.
- La intersección entre subconjuntos es vacía.
- Cada subconjunto es no vacío.

La discrepancia entre el sistema original y el sistema reconstruido se cuantifica mediante Earth Mover’s Distance (EMD).

## 2.2 Complejidad del Espacio de k-Particiones

El número de posibles k-particiones está dado por los números de Stirling del segundo tipo S(n,k).

Para un sistema de 10 variables:

- k = 3 → 9,330 particiones posibles.

Para 15 variables:

- Más de 2.3 millones de tri-particiones posibles.

## 2.3 Interpretación Geométrica de k-Particiones

La estrategia GeoMIP representa el espacio de estados como un hipercubo n-dimensional. Una k-partición puede interpretarse como la división del hipercubo mediante k−1 hiperplanos.

La tabla de costos de transiciones entre estados captura información sobre la estructura causal del sistema y puede reutilizarse para diferentes valores de k.

---

# 3. Planteamiento del Problema

El objetivo del proyecto es diseñar e implementar una extensión de GeoMIP y QNodes para identificar la k-Partición de Mínima Información (k-MIP) para 3 ≤ k ≤ 5.

## 3.1 Formulación Matemática del Problema

Dado un sistema V con n variables binarias y una Matriz de Probabilidad de Transición:

P(Vₜ₊₁ | Vₜ)

Se busca encontrar la k-partición óptima que minimice la Earth Mover’s Distance entre la distribución original y la reconstruida.

## 3.2 Restricciones y Consideraciones

La implementación debe:

- Mantener compatibilidad con la arquitectura existente.
- Heredar de la clase base SIA.
- Reutilizar la tabla de costos.
- Mantener interoperabilidad con PyPhi y QNodes.

## 3.3 Alcance del Proyecto

El sistema debe:

- Resolver k-particiones para 2 ≤ k ≤ 5.
- Encontrar soluciones óptimas para sistemas pequeños.
- Encontrar soluciones aproximadas eficientes para sistemas grandes.

---

# 4. Entregables del Proyecto

## 4.1 Componentes de Software

Se debe entregar:

- Implementación funcional de KGeoMIP y KQNodes.
- Métodos de búsqueda de k-MIP.
- Evaluación de k-particiones.
- Tests unitarios y documentación.

## 4.2 Documentación Técnica

El reporte debe incluir:

- Fundamentos matemáticos.
- Explicación algorítmica.
- Complejidad computacional.
- Limitaciones y mejoras futuras.

## 4.3 Resultados Experimentales

Los resultados deben incluir:

- Tiempos de ejecución.
- Tasas de acierto.
- Comparaciones con métodos base.
- Gráficas de escalabilidad.

## 4.4 Presentación Final

La presentación debe:

- Explicar el problema.
- Mostrar resultados.
- Incluir demostración funcional.
- Tener duración máxima de 15 minutos.

## 4.5 Criterios de Evaluación

La evaluación considerará:

- Correctitud.
- Eficiencia.
- Calidad del código.
- Calidad de documentación.
- Calidad de presentación.

---

# 5. Observaciones Finales

Este proyecto busca extender las capacidades de análisis de sistemas complejos más allá de las bi-particiones tradicionales.

El principal desafío consiste en equilibrar precisión y eficiencia computacional, explotando propiedades geométricas y estructurales del espacio de soluciones.

Los métodos desarrollados tendrán aplicación en:

- Teoría de la Información Integrada.
- Clustering.
- Detección de comunidades.
- Optimización combinatoria.
- Análisis de redes complejas.

---
