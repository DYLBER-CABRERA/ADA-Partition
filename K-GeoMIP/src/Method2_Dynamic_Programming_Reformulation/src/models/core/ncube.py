from dataclasses import dataclass
from numpy.typing import NDArray
import numpy as np


@dataclass(frozen=True)
class NCube:
    """
    N-cubo hace referencia a un cubo n-dimensional, donde estarán indexados según la posición de precedencia de los datos, permitiendo el rápido acceso y operación en memoria.
    - `indice`: índice original del n-cubo asociado con un literal (0:A, 1:B, 2:C, ...) que permita representabilidad en su alcance o tiempo futuro.
    - `dims`: dimensiones activas actuales del n-cubo, es aquí donde se conoce la dimensionalidad según su cantidad de elementos, de forma tal que si este en el tiempo es condicionado o marginalizado tendrá una dimensionalidad menor o igual a la original a pesar que haya una alta dimensión específica.
    - `data`: arreglo numpy con los datos indexados según la notación de origen, de ser necesario se aplica una transformación sobre estos que los reindexe si se desea otra notación particular.
    """

    indice: int
    dims: NDArray[np.int8]
    data: np.ndarray

    def __post_init__(self):
        """Validación de tamaño y dimensionalidad tras inicialización.

        Raises:
            ValueError: Se valida que hayan dimensiones y cumpla con las dimensiones de un cubo n-dimensional.
        """
        # Lógica: Solo valida la forma cuando el cubo tiene dimensiones activas (dims no vacío).
        #         Un n-cubo de d dimensiones debe tener shape (2,2,...,2) d veces — cada dimensión
        #         binaria tiene exactamente 2 estados posibles (0 y 1).
        # Sintaxis: `self.dims.size` retorna 0 si el array está vacío (falsy); `(2,) * n`
        #           genera la tupla (2,2,...,2) de longitud n usando repetición de tupla.
        if self.dims.size and self.data.shape != (2,) * self.dims.size:
            raise ValueError(
                f"Forma inválida {self.data.shape} para dimensiones {self.dims}"
            )

    def condicionar(
        self,
        indices_condicionados: NDArray[np.int8],
        estado_inicial: NDArray[np.int8],
    ) -> "NCube":
        """
        Aplicar condiciones de fondo sobre un n-cubo. En estas lo que se hace es seleccionar una serie de caras sobre el n-cubo según las dimensiones escogidas y su estado inicial específico asociado, descartandose así todas las demás que no pertenezcan al indice condicionado.
        En la selección de las dimensiones es importante saber cómo la dimensión más externa es la más significativa, de forma que la selección debe hacerse de afuera hacia adentro.
        Debe tenerse claro también la localidad de las dimensiones puesto aunque se tengan dimensiones muy superiores no hay correspondencia con el total de dimensiones del cubo (dimensiones locales).

        Args:
        ----------
            indices_condicionados (NDArray[np.int8]): Dimensiones o ejes en los cuales se aplicará el condicinamiento.
            estado_inicial (NDArray[np.int8]): El estado inicial asociado al sistema.

        Returns:
        -------

            NCube: El n-cubo seleccionado en todos los ejes, pero se definen para dar selección los cuales se hayan enviado como parámetros.

        Example:
        -------
        El n-cubo original está asociado con el estado inicial

        >>> estado_inicial = np.array([1,0,0])
        >>> mi_ncubo
            NCube(index=(1,)):
                dims=(0, 1, 2)
                shape=(2, 2, 2)
                data=
                    [[[0.1  0.3 ]
                    [0.5  0.7 ]]
                    [[0.9  0.11]
                    [0.13 0.15]]]
        >>> dimensiones = np.array([2])
        >>> mi_ncubo.condicionar(dimensiones, estado_incial)
            NCube(index=(1,)):
                dims=(0, 1)
                shape=(2, 2)
                data=
                    [[0.1 0.3]
                    [0.5 0.7]]
        """
        # Lógica: El número de dimensiones activas determina cuántos ejes de selección
        #         necesitamos construir. Cada dimensión del n-cubo corresponde a un eje
        #         del array NumPy multidimensional.
        # Sintaxis: `.size` en NDArray retorna el número total de elementos (equivale a len
        #           para arrays 1D); es O(1) porque es un atributo del array, no un cómputo.
        numero_dims = self.dims.size

        # Lógica: Inicializa la selección con `slice(None)` en cada eje, lo que equivale
        #         a "tomar todos los valores en esa dimensión" (como `:` en indexing de NumPy).
        #         Las dimensiones condicionadas serán reemplazadas por un índice entero (0 o 1).
        # Sintaxis: `[slice(None)] * n` crea una lista de n objetos slice, cada uno equivalente
        #           a `:` en notación de indexing. Es el equivalente programático de `arr[:,:,:]`.
        seleccion = [slice(None)] * numero_dims

        # Lógica: Para cada dimensión condicionada, calcula su posición local en el array
        #         invirtiendo el índice. La dimensión más externa (más significativa) corresponde
        #         al eje 0 de NumPy, pero en la representación interna es la última del array.
        #         La inversión `numero_dims - (condicion + 1)` mapea dimensión global → eje local.
        # Sintaxis: `for condicion in indices_condicionados` itera el NDArray como iterable Python;
        #           cada elemento es un int8 representando el índice global de la dimensión.
        for condicion in indices_condicionados:
            # Lógica: Invierte el índice dimensional porque la convención del n-cubo tiene la
            #         dimensión más externa como la más significativa (big-endian dimensional),
            #         pero NumPy indexa desde la dimensión más a la izquierda = eje 0.
            # Sintaxis: `numero_dims - (condicion + 1)` es la fórmula de inversión de índice;
            #           el +1 compensa que condicion es 0-based y numero_dims es el tamaño total.
            level_arr = numero_dims - (condicion + 1)

            # Lógica: Fija el eje condicionado al valor que tiene esa dimensión en el estado
            #         inicial. Esto "selecciona una cara" del hipercubo para esa dimensión,
            #         descartando los estados que no corresponden al estado inicial dado.
            # Sintaxis: `seleccion[level_arr] = estado_inicial[condicion]` reemplaza el
            #           slice(None) por un entero (0 o 1) — NumPy lo interpreta como índice fijo.
            seleccion[level_arr] = estado_inicial[condicion]

        # Lógica: Las dimensiones remanentes son las que NO fueron condicionadas. Se filtran
        #         para actualizar el metadata del n-cubo resultante, reflejando que tiene
        #         menor dimensionalidad tras el condicionamiento.
        # Sintaxis: List comprehension con `if dim not in indices_condicionados` usa el operador
        #           `in` sobre NDArray, que hace búsqueda lineal O(k) donde k=len(condicionados).
        #           `dtype=np.int8` mantiene el tipo compacto para arrays de índices pequeños.
        nuevas_dims = np.array(
            [dim for dim in self.dims if dim not in indices_condicionados],
            dtype=np.int8,
        )

        # Lógica: Construye el n-cubo condicionado aplicando la selección al array de datos.
        #         El n-cubo resultante tiene las mismas probabilidades pero reducido a la cara
        #         del hipercubo correspondiente al estado inicial en las dims condicionadas.
        # Sintaxis: `self.data[tuple(seleccion)]` convierte la lista de selecciones a tupla
        #           (requerido por NumPy para advanced indexing multidimensional). El resultado
        #           tiene shape (2,)*len(nuevas_dims) — una dimensión menos por cada condicionada.
        return NCube(
            data=self.data[tuple(seleccion)],
            dims=nuevas_dims,
            indice=self.indice,
        )

    def marginalizar(self, ejes: NDArray[np.int8]) -> "NCube":
        """
        Marginalizar a nivel del n-cubo permite acoplar o colapsar una o más dimensiones manteniendo la probabilidad condicional.
        El n-cubo puede esquematizarse de forma tal que se aprecie el solapamiento y promedio ente caras, donde la dimensión más baja es el primer desplazamiento dimensional sobre el arreglo.
        Es importante validar la intersección de ejes puesto es una rutina llamada en sistema desde marginalizar como particionar.

        Args:
        ----
            ejes (NDArray[np.int8]): Arreglo con las dimensiones a marginalizar o eliminar. Se valida que los ejes o dimensiones dadas estén y finalmente alineamos nuevamente con las dimensiones locales, donde con numpy debemos hacer uso de la dimensión complementaria para alinear la dimensión externa a la más interna.

        Returns:
        -------
            NCube: El n-cubo marginalizado en las dimensiones dadas. Donde es equivalente el marginalizar sobre (a, b,) que primero en (a,) y luego en (b,) o viceversa.

        Example:
        -------
            >>> dimensiones = np.array([2, 3])
            >>> mi_ncubo
            NCube(index=0):
            dims=[0 1 2]
            shape=(2, 2, 2)
            data=
                [[[0. 0.]
                [1. 1.]],
                [[1. 1.]
                [1. 1.]]]

                [[0.5 0.5]
                [1. 1.]]

                [0.75 0.75]

            >>> mi_ncubo.marginalizar(dimensiones)
            NCube(index=0):
                dims=[0]
                shape=(2,)
                data=
                    [0.75 0.75]

            Se han agrupado los valores del n-cubo por promedio, dejando los remanentes en la dimension 0.
        """
        # Lógica: Solo marginaliza los ejes que realmente existen en este n-cubo.
        #         La intersección evita errores cuando se piden marginalizar dimensiones
        #         que ya fueron eliminadas en un condicionamiento o marginalización previa.
        # Sintaxis: `np.intersect1d(a, b)` retorna los elementos comunes entre dos arrays
        #           ordenados; equivale a la intersección de conjuntos pero sobre NDArrays.
        marginable_axis = np.intersect1d(ejes, self.dims)

        # Lógica: Si ninguno de los ejes pedidos existe en este n-cubo, no hay nada que
        #         marginalizar. Retornar `self` evita crear copias innecesarias y mantiene
        #         la inmutabilidad del dataclass (frozen=True).
        # Sintaxis: `not marginable_axis.size` evalúa True cuando el array está vacío (size=0);
        #           es el patrón idiomático de NumPy para chequear array vacío (no usar `not arr`).
        if not marginable_axis.size:
            return self

        # Lógica: El índice máximo local (dims.size - 1) es necesario para la fórmula de
        #         inversión de ejes. Al igual que en condicionar(), la dimensión más significativa
        #         está en el eje 0 de NumPy, pero el orden lógico es el inverso.
        # Sintaxis: `self.dims.size - 1` es el índice del último elemento; `-1` no da índice
        #           negativo aquí porque se usa como operando aritmético, no como índice.
        numero_dims = self.dims.size - 1

        # Lógica: Calcula los ejes reales de NumPy que corresponden a las dimensiones a
        #         marginalizar. La fórmula `numero_dims - dim_idx` invierte el orden para
        #         alinear la representación lógica (dimensión más significativa = última)
        #         con la representación de NumPy (dimensión más significativa = eje 0).
        # Sintaxis: Generator expression dentro de `tuple()` — más eficiente que list comprehension
        #           cuando solo se necesita iterar una vez. `enumerate(self.dims)` produce
        #           pares (posición_local, valor_dimensión) para calcular el eje de NumPy.
        ejes_locales = tuple(
            numero_dims - dim_idx
            for dim_idx, axis in enumerate(self.dims)
            if axis in marginable_axis
        )

        # Lógica: Las dimensiones remanentes son las que sobreviven la marginalización.
        #         Se filtran del array original para actualizar el metadata del n-cubo.
        # Sintaxis: List comprehension con condición `if d not in marginable_axis`;
        #           `dtype=np.int8` mantiene consistencia de tipo con el resto del sistema.
        new_dims = np.array(
            [d for d in self.dims if d not in marginable_axis],
            dtype=np.int8,
        )

        # Lógica: Crea el n-cubo marginalizado promediando sobre los ejes locales calculados.
        #         El promedio (media aritmética) es la operación de marginalización correcta
        #         para distribuciones de probabilidad: P(X) = Σ_y P(X,Y=y) / |Y|.
        # Sintaxis: `np.mean(data, axis=ejes_locales, keepdims=False)` colapsa los ejes
        #           especificados calculando la media; `keepdims=False` elimina esas dimensiones
        #           del shape resultante en lugar de dejarlas con tamaño 1.
        return NCube(
            data=np.mean(self.data, axis=ejes_locales, keepdims=False),
            dims=new_dims,
            indice=self.indice,
        )

    def __str__(self) -> str:
        # Lógica: Genera una representación legible del n-cubo para depuración y visualización,
        #         mostrando su índice, dimensiones activas, forma del array y datos.
        # Sintaxis: f-string multilínea con `\n` + espacios para indentación visual.
        #           `.replace("\n", "\n" + " " * 8)` indenta cada línea del array numpy
        #           para que quede alineado bajo el prefijo `data=`.
        dims_str = f"dims={self.dims}"
        forma_str = f"shape={self.data.shape}"
        datos_str = str(self.data).replace("\n", "\n" + " " * 8)
        return (
            f"NCube(index={self.indice}):\n"
            f"    {dims_str}\n"
            f"    {forma_str}\n"
            f"    data=\n        {datos_str}"
        )
