import numpy as np
from numpy.typing import NDArray

from src.funcs.base import reindexar, seleccionar_subestado
from src.models.enums.notation import Notation
from src.models.core.ncube import NCube

from src.models.base.application import aplicacion

from src.constants.base import COLS_IDX


class System:
    """
    La clase sistema es la encargada de realizar las operaciones de condicionamiento, substracción para generación de subsistemas y obtención de las distribuciones marginales
    para realizar eficientemente el cálculo de la EMD en el Efecto.

    Args:
    ----
        - `tpm` (np.ndarray): El la Matriz de Probabilidad de Transición, de la cuál por cada nodo se generará un n-cubo asociado para permitir rápida operación de los datos.
        - `estado_inicial` (np.ndarray): Este asocia cada variable del sistema con un estado, activa o inactiva, de forma que permita al final seleccionar ciertos estados necesarios para el cálculo final de la EMD.
        - `notation` Optional(str): Por defecto Little-Endian. Representa la notación usada para la indexación de los datos, leer la guía del proyecto para conocer más notaciones.
    """

    def __init__(
        self,
        tpm: np.ndarray,
        estado_inicio: np.ndarray,
        notacion: str = aplicacion.notacion,
    ):
        # Valida que el tamaño del estado inicial coincida con la cantidad de nodos formados por las columnas de la TPM
        # (usando el operador walrus := para asignar "n_nodes").
        if estado_inicio.size != (n_nodes := tpm.shape[COLS_IDX]):
            raise ValueError(f"Estado inicial debe tener longitud {n_nodes}") # Lanza excepción si las longitudes no coinciden.
        
        # Guarda el estado inicial del sistema en un atributo de la instancia.
        self.estado_inicial = estado_inicio
        
        # Crea y almacena una tupla de objetos NCube (un n-cubo por cada variable/nodo del sistema).
        self.ncubos = tuple(
            NCube(
                indice=i, # Asigna al n-cubo el índice correspondiente a su nodo/columna iterada.
                dims=np.array(range(n_nodes), dtype=np.int8), # Define las dimensiones asignando un arreglo del 0 hasta n_nodes-1.
                
                # Extrae los datos (probabilidades) de la columna 'i' y les da una forma de 2x2x...x2 (n_nodes veces)
                data=tpm[:, i].reshape((2,) * n_nodes)
                if notacion == Notation.LIL_ENDIAN.value # Realiza el formato directo si la notación es LIL_ENDIAN predeterminada.
                else tpm[:, i][reindexar(tpm[COLS_IDX])].reshape((2,) * n_nodes), # Caso contrario, reordena/reindexa la fila completa antes de redimensionar.
            )
            for i in range(n_nodes) # Itera a través de todos los nodos/columnas creados.
        )

    @property
    def indices_ncubos(self):
        """
        La TPM tiene asociados una cantidad n-ésima de n-cubos, es por esto que es necesario tenerlos indexados puesto
        representa el comportamiento de un nodo en todos sus posibles estados dentro de un espacio de probabilidad determinista o estocástica.
        El método ofrece dinámicamente el valor del atributo en función al índice de cada n-cubo.

        Returns:
        -------
            - `np.array`: El listado con los índices con los n-cubos remanentes a la inicialización del sistema,
            condicionamiento para sistemas candidatos, generación de subsistemas y particiones.
        """
        return np.array([cube.indice for cube in self.ncubos], dtype=np.int8)

    @property
    def dims_ncubos(self):
        """
        Retorna las dimensiones que se preserven en los n-cubos del sistema. No es un método aplicable tras generación de particiones 
        puesto no necesariamente todos los n-cubos mantendrán las mismas dimensiones.

        Returns:
            - `np.ndarray`: El arreglo con las dimensiones únicas de los n-cubos del sistema a cualquier nivel, idealmente superior a una partición.
        """
        return self.ncubos[0].dims if len(self.ncubos) > 0 else np.array([])

    def condicionar(self, indices: NDArray[np.int8]) -> "System":
        """
        A partir de un sistema origina, esta operación se aplica para todo n-cubo, también llamada como aplicar condiciones de fondo, hace que este se 
        vea seleccionado el cubo en su totalidad, pero delimitando en las dimensiones o indices especificados para hacer selección según el estado inicial asociado.
        Primeramente se intersecan los indices enviados con los actuales de cada n-cubo para evitar elementos inexistentes, 
        luego las dimensiones intersecadas serán las que se definan para cada n-cubo.

        Args:
        ----
            - `indices` (NDArray[np.int8]): Dimensiones que idealmente están asociadas a cada n-cubo y harán selección según el usuario.

        Returns:
        -------
            `System`: El sistema candidato con sus n-cubos condicionados a las variables indicadas y su valor binario específico.
            Este sistema condicionado recibe el nombre de sistema candidato y servirá para procesos de substracción para generación de subsistemas.

        Examples:
        --------
        >>> dimensiones = np.array([2])
        >>> estados = np.array([1,0,0])
        >>> sistema = System(tpm, estados)
        System(indices=[0 1 2], sub_dims=[0 1 2])
            Initial state: [1 0 0]
            NCubes:
                NCube(index=0):
                    dims=[0 1 2]
                    shape=(2, 2, 2)
                    data=
                        [[[0. 0.]
                        [1. 1.]],
                        [[1. 1.]
                        [1. 1.]]]
                NCube(index=1):
                    dims=[0 1 2]
                    shape=(2, 2, 2)
                    data=
                        [[[0. 0.]
                        [0. 0.]],
                        [[0. 1.]
                        [0. 1.]]]
                NCube(index=2):
                    dims=[0 1 2]
                    shape=(2, 2, 2)
                    data=
                        [[[0. 1.]
                        [1. 0.]],
                        [[0. 1.]
                        [1. 0.]]]
        >>> sistema.condicionar(dimensiones)
        System(indices=[0 1], sub_dims=[0 1])
            Initial state: [1 0 0]
            NCubes:
                NCube(index=0):
                    dims=[0 1]
                    shape=(2, 2)
                    data=
                        [[0. 0.]
                        [1. 1.]]
                NCube(index=1):
                    dims=[0 1]
                    shape=(2, 2)
                    data=
                        [[0. 0.]
                        [0. 0.]]

        Como se aprecia se hizo reducción en la dimensión más significativa y prevaleció las dimensiones donde C=0 (agrupamiento más externo, primera posición).
        """
        # 1. Calcula la intersección entre los índices que el usuario quiere condicionar y los índices de los n-cubos que realmente existen en el sistema.
        # Esto evita errores si se pide condicionar sobre un índice que no forma parte de este sistema.
        indices_validos = np.intersect1d(self.indices_ncubos, indices)
        
        # 2. Si resulta que la intersección está vacía (no hay índices válidos para condicionar):
        if not indices_validos.size:
            return self # Devuelve el sistema tal cual, sin modificar nada ni gastar memoria.
        
        # 3. Crea una "cáscara" vacía de un nuevo objeto System SIN llamar a su método __init__ (así evitamos cálculos innecesarios).
        nuevo_sis = System.__new__(System)
        
        # 4. Copia el estado inicial tal cual del sistema viejo al nuevo.
        nuevo_sis.estado_inicial = self.estado_inicial
        
        # 5. Crea la nueva tupla de n-cubos para el sistema candidato.
        nuevo_sis.ncubos = tuple(
            # 5a. Llama a la función 'condicionar' de cada NCube para que rebanen/filtren su información interna.
            cube.condicionar(indices_validos, self.estado_inicial)
            for cube in self.ncubos # 5b. Itera sobre todos los cubos del sistema actual.
            # 5c. Solo conserva los cubos cuyo índice NO esté dentro de los que fueron condicionados 
            # (es decir, elimina los cubos que formaban las condiciones de fondo).
            if cube.indice not in indices_validos
        )
        
        # 6. Retorna el nuevo sistema (ahora llamado sistema candidato) listo para ser usado y sin haber alterado el original.
        return nuevo_sis

    def substraer(
        self,
        alcance_dims: NDArray[np.int8],
        mecanismo_dims: NDArray[np.int8],
    ) -> "System":
        """
        Permite substraer una serie de elementos a partir de un sistema completo o sun sisteam candidato tanto en el futuro/alcance
        como el presente/mecanismo, logrando así la generación de un subsistema.

        Args:
        ----
            - `alcance_dims` (NDArray[np.int8]): En este arreglo se encuentran las variables que van a ser eliminadas, puesto es el alcance/futuro significa que los cubos que pertenezcan a estos índices serán descartados.
            - `mecanismo_dims` (NDArray[np.int8]): Acá preceden las dimensiones asociadas a cada n-cubo, donde para cada uno se aplicará la operación de agrupación por promedio, solapando múltiples caras del n-cubo.

        Returns:
        -------
            System: Este subsistema servirá para procesos posteriores de particionamiento.

        Examples:
        --------
        >>> alcances = np.array([0])
        >>> mecanismos = np.array([2])
        >>> mi_sistema
        System(indices=[0 1 2], sub_dims=[0 1 2])
            Initial state: [1 0 0]
            NCubes:
                NCube(index=0):
                    dims=[0 1 2]
                    shape=(2, 2, 2)
                    data=
                        [[[0. 0.]
                        [1. 1.]],
                        [[1. 1.]
                        [1. 1.]]]
                NCube(index=1):
                    dims=[0 1 2]
                    shape=(2, 2, 2)
                    data=
                        [[[0. 0.]
                        [0. 0.]],
                        [[0. 1.]
                        [0. 1.]]]
                NCube(index=2):
                    dims=[0 1 2]
                    shape=(2, 2, 2)
                    data=
                        [[[0. 1.]
                        [1. 0.]],
                        [[0. 1.]
                        [1. 0.]]]
        >>> mi_sistema.substraer(alcances, mecanismos)
        System(indices=[1 2], sub_dims=[0 1])
            Initial state: [1 0 0]
            NCubes:
                NCube(index=1):
                    dims=[0 1]
                    shape=(2, 2)
                    data=
                        [[0.  0.5]
                        [0.  0.5]]
                NCube(index=2):
                    dims=[0 1]
                    shape=(2, 2)
                    data=
                        [[0. 1.]
                        [1. 0.]]

        Los indices asociados a los literales o variables independiente al tiempo son `0:(A|a), 1:(B|b), 2:(C|c)`.
        En el ejemplo se aprecia lo que puede representarse como que el sistema `V={A_abc,B_abc,C_abc}` sufrió una martinalización en `A in (t+1)`, dejando `B` y `C`, sobre los que se aplicó luego una marginalización en `c in (t)`.
        """
        # np.setdiff1d(A, B) devuelve los elementos de A que NO están en B. 
        # Aquí filtra (substrae) qué índices de n-cubos van a sobrevivir tras descartar los indicados en 'alcance_dims'.
        valid_futures = np.setdiff1d(self.indices_ncubos, alcance_dims)

        # Crea un nuevo objeto System en memoria saltándose su constructor (__init__) para máxima velocidad computacional.
        new_sys = System.__new__(System)

        # Hereda/copia exactamente el mismo array de estado inicial binario del sistema padre.
        new_sys.estado_inicial = self.estado_inicial

        # Se recorre y crea una nueva tupla (inmutable y rápida) para almacenar los n-cubos del nuevo subsistema.
        new_sys.ncubos = tuple(
            # Ejecuta la función marginalizar (promedia/solapa dimensiones) usando el array de 'mecanismo_dims'
            cube.marginalizar(mecanismo_dims)
            
            # Bucle iterando sobre cada NCube existente en el sistema padre.
            for cube in self.ncubos
            
            # Condicional: solo agrega este cubo si su índice no fue descartado (si existe en valid_futures).
            if cube.indice in valid_futures
        )

        # Retorna la nueva instancia (subsistema) completamente generada.
        return new_sys

    def bipartir(
        self,
        alcance: NDArray[np.int8],
        mecanismo: NDArray[np.int8],
    ) -> "System":
        """
        Es en este método donde generamos a partir de un subsistema, una bipartición.

        Args:
            alcance (NDArray[np.int8]): Variables futuras que idedalmente hacen parte del subsistema, estas seleccionan un subconjunto dentro del mismo el cuál será marginalizado en las dimensiones excluídas.
            mecanismo (NDArray[np.int8]): Acá está el conjunto de dimensiones primales dadas, donde marginalizarán todos los n-cubos cuyo índice no haga parte del alcance.

        Returns:
            System: Se retorna una bipartición, acá es importante tener muy claro que puede o no haber pérdida con respecto al sub-sistema original y por ende, se analizará mediante una distancia métrica cono la EMD-Effect la diferencia entre las distribuciones marginales de estos dos "sistemas", apreciando si hay diferencia como una "pérdida" en la información respecto al sub-sistema original.
        """
        # Crea un nuevo sistema "cáscara" en memoria, eludiendo el constructor __init__ para mayor rendimiento.
        new_sys = System.__new__(System)
        
        # Copia la referencia del estado inicial (array binario) del sistema original al nuevo sistema bipartido.
        new_sys.estado_inicial = self.estado_inicial

        # Genera una nueva tupla inmutable que contendrá los n-cubos resultantes de la partición.
        new_sys.ncubos = tuple(
            # Si el cubo está en el 'alcance', se marginaliza lo que NO es el mecanismo (simulando un corte).
            # np.setdiff1d(A, B) devuelve lo que está en dims pero no en mecanismo.
            cube.marginalizar(np.setdiff1d(cube.dims, mecanismo))
            
            # (Condición del operador ternario) Evalúa si el índice del cubo actual pertenece al 'alcance'.
            if cube.indice in alcance
            
            # En caso contrario, se marginaliza directamente el 'mecanismo' (como si perteneciera a la otra mitad del corte).
            else cube.marginalizar(mecanismo)
            
            # El bucle que recorre todos los n-cubos del sistema actual uno por uno.
            for cube in self.ncubos
        )
        
        # Retorna el sistema particionado.
        return new_sys

    def k_partir(
        self,
        particion: "list[tuple[NDArray[np.int8], NDArray[np.int8]]]",
    ) -> "System":
        """
        Generalización de bipartir() al caso k-partito con k ≥ 2.

        Sea P = {(A₁,M₁), ..., (Aₖ,Mₖ)} una k-partición donde:
            - Aᵢ ⊆ indices_ncubos  (variables futuras de la parte i)
            - Mᵢ ⊆ dims_ncubos     (variables presentes de la parte i)
            - ∪ᵢ Aᵢ = indices_ncubos   y   Aᵢ ∩ Aⱼ = ∅  para i ≠ j
            - ∪ᵢ Mᵢ = dims_ncubos    y   Mᵢ ∩ Mⱼ = ∅  para i ≠ j

        Transformación por n-cubo:
            ∀ c ∈ ncubos tal que c.indice ∈ Aᵢ:
                c' ← c.marginalizar(c.dims ∖ Mᵢ)

        Cada parte Sᵢ opera de forma independiente conservando únicamente
        las dependencias causales internas a esa parte.

        Equivalencia con bipartir() para k=2:
            k_partir([(A₁,M₁),(A₂,M₂)]) ≡ bipartir(A₁,M₁)
            cuando A₂ = indices_ncubos ∖ A₁  y  M₂ = dims_ncubos ∖ M₁

        Args:
            particion: Lista de k tuplas (alcance_i, mecanismo_i) como NDArray[np.int8].
                       Cada tupla define los índices futuros y presentes de una parte.

        Returns:
            System: Sistema k-partido. Cada n-cubo marginalizado según su parte.

        Complejidad temporal:  Θ(Σᵢ|Aᵢ|) construcción del mapa + O(n·2^d) marginalizaciones.
                               n = |ncubos|, d = dimensionalidad máxima del subsistema.
        Complejidad espacial:  O(n·2^d) para el sistema resultante.

        Precondición:  ∪ᵢ Aᵢ = indices_ncubos (todo ncubo debe pertenecer a exactamente una parte).
        Postcondición: dist_marginal(resultado) ≡ ⊗ᵢ dist_marginal(Sᵢ).
        """
        # Lógica: Crea una instancia "cáscara" de System sin invocar __init__, evitando la costosa reconstrucción desde la TPM.
        # Sintaxis: `Class.__new__(Class)` es el protocolo de bajo nivel de Python para crear un objeto sin inicializar — solo reserva memoria.
        new_sys = System.__new__(System)

        # Lógica: Transfiere el estado inicial (vector binario) del sistema original al nuevo sistema k-partido para mantener coherencia.
        # Sintaxis: Asignación directa de atributo de instancia; al ser un ndarray, se copia la referencia (no el contenido).
        new_sys.estado_inicial = self.estado_inicial

        # Lógica: Crea el diccionario de lookup vacío que mapeará cada índice de n-cubo a su mecanismo_i correspondiente.
        #         Usar un dict permite consulta O(1) por cubo en lugar de recorrer O(k) pares por cada cubo.
        # Sintaxis: `dict[int, NDArray[np.int8]]` es una type annotation explícita (PEP 526); no afecta la ejecución.
        indice_a_mecanismo: dict[int, NDArray[np.int8]] = {}

        # Lógica: Recorre cada par (alcance_i, mecanismo_i) de la k-partición para poblar el diccionario de lookup.
        # Sintaxis: `for a, b in lista_de_tuplas` es desempaquetado de tuplas (tuple unpacking) en el encabezado del for.
        for alcance_i, mecanismo_i in particion:
            # Lógica: Para cada índice de cubo dentro del alcance_i, registra su mecanismo asociado en el diccionario.
            #         Al terminar el doble bucle, indice_a_mecanismo[idx] = Mᵢ donde c.indice ∈ Aᵢ.
            # Sintaxis: `int(idx)` convierte el elemento np.int8 a int nativo de Python para usarlo como clave del dict.
            for idx in alcance_i:
                indice_a_mecanismo[int(idx)] = mecanismo_i

        # Lógica: Construye la tupla inmutable de n-cubos del sistema k-partido.
        #         Cada cubo se marginaliza descartando dims ∖ Mᵢ — así la parte i solo ve sus propias variables presentes.
        # Sintaxis: `tuple(expr for x in iterable)` es una generator expression pasada directamente al constructor tuple().
        new_sys.ncubos = tuple(
            # Lógica: Marginaliza el cubo eliminando las dimensiones que NO pertenecen a su Mᵢ, aislando la influencia de esa parte.
            # Sintaxis: `np.setdiff1d(A, B)` devuelve elementos de A que no están en B — calcula dims ∖ Mᵢ en O(n log n).
            cube.marginalizar(
                np.setdiff1d(cube.dims, indice_a_mecanismo[int(cube.indice)])
            )
            # Lógica: Condición del operador ternario — aplica la marginalización solo si el cubo pertenece a alguna parte válida de P.
            # Sintaxis: `expr_si_true if condicion else expr_si_false` es el operador ternario (conditional expression) de Python.
            if int(cube.indice) in indice_a_mecanismo
            # Lógica: Si el cubo no aparece en ningún alcance (partición incompleta), lo devuelve intacto como salvaguarda defensiva.
            # Sintaxis: `else cube` retorna el objeto NCube sin modificar; `in dict` verifica existencia de clave en O(1).
            else cube
            # Lógica: Itera sobre todos los n-cubos del sistema para transformarlos según su parte correspondiente.
            # Sintaxis: `for cube in self.ncubos` recorre la tupla inmutable de NCube; cada iteración expone el objeto completo.
            for cube in self.ncubos
        )

        # Lógica: Devuelve el sistema completamente k-partido, listo para calcular su distribución marginal y comparar con el original.
        # Sintaxis: `return objeto` finaliza la ejecución del método y entrega el nuevo System al llamador.
        return new_sys
    

    def distribucion_marginal(self):
        """
        Partiendo de idealmente un subsistema o una bipartición como entrada, se seleccionana los nodos/elementos cuando su estado es OFF o inactivo para cada uno de ellos, 
        mediante la propiedad de las distribuciones marginales, esto nos permite calcular más eficientemente la EMD-Effect, logrando así determinar un coste para dar
        comparación entre idealmente, un sub-sistema y una bipartición.
        Hemos de aplicar una reversión en la selección del estado inicial puesto

        Returns:
            NDArray[np.float32]: Este arreglo contiene cada elemento/variable de forma ordenada y consecutiva seleccionado específicamente en la clave formada por el estado inicial.
        """
        # Type Hinting: Solo le dice al editor y a Python que esta variable almacenará un decimal (float).
        probabilidad: float
        
        # Crea un arreglo de memoria sin inicializar (basura) muy rápido, 
        # reservando el espacio exacto igual a la cantidad de n-cubos mediante 'dtype=np.float32' (decimales ligeros).
        distribuciones = np.empty(self.indices_ncubos.size, dtype=np.float32)

        # enumerate() desempaqueta 2 cosas mágicamente por ciclo: 'i' (el índice 0, 1, 2...) y 'ncubo' (el objeto).
        for i, ncubo in enumerate(self.ncubos):
            # Carga por defecto todos los datos del cubo (puede ser matriz entera o un simple número)
            probabilidad = ncubo.data
            
            # Si el tamaño de las dimensiones es mayor a cero (.size > 0 se evalúa como True)
            if ncubo.dims.size:
                # Comprensión de tupla que extrae del arreglo 'estado_inicial' solo los valores 'j' presentes en las dimensiones del cubo.
                sub_estado_inicial = tuple(self.estado_inicial[j] for j in ncubo.dims)
                
                # Usa func 'seleccionar_subestado' para generar coordenadas.
                # Al pasarlas entre corchetes [...], extraemos un valor decimal exacto de la matriz n-dimensional 'ncubo.data'
                probabilidad = ncubo.data[seleccionar_subestado(sub_estado_inicial)]
                
            # Calcula la probabilidad complementaria (probabilidad de estado OFF / estar apagado) y la guarda en la ranura 'i'
            distribuciones[i] = 1 - probabilidad
            
        # Retorna el numpy array completado.
        return distribuciones

    def __str__(self) -> str:
        # Recupera las dimensiones base llamando a la propiedad @property 'dims_ncubos'
        sub_dims = self.dims_ncubos
        
        # 'List Comprehension' (Comprensión de listas) aplicando F-Strings (f"{c}") 
        # Esto auto-llama al método mágico __str__ de cada NCube y lo almacena como texto en la lista.
        cubes_info = [f"{c}" for c in self.ncubos]
        
        # Devuelve un bloque de texto formateado. 
        # "\n".join(cubes_info) fusiona la lista de textos separándolos por saltos de línea (\n).
        return (
            f"\nSystem(indices={self.indices_ncubos}, dims={sub_dims})"
            f"\nInitial state: {self.estado_inicial}"
            f"\nNCubes:\n" + "\n".join(cubes_info)
        )
