# Proyecto QNodes - Arquitectura, Ejecución y Buenas Prácticas

`QNodes` es el módulo encargado de analizar redes binarias utilizando una versión optimizada del algoritmo de **Queyranne** para resolver la **Partición de Mínima Información (MIP)** en el contexto de **Integrated Information Theory (IIT)**.

## 📌 Propósito del proyecto

- Calcular la partición de menor pérdida de información en un sistema binario modelado por una matriz de transición probabilística (TPM).
- Optimizar el algoritmo de búsqueda de particiones mediante memoización y estructura de datos eficiente.
- Implementar y comparar diversas estrategias de partición: **Biparticiones (QNodes)** y **k-particiones generalizadas (KQNodes)**.

## 📁 Estructura principal

- `exec.py`
  - Punto de entrada principal para ejecución rápida.
  - Lanza una ejecución y guarda resultados en la carpeta `results/`.

- `src/main.py`
  - Orquesta la configuración del experimento: selección de red, estado inicial, condiciones, alcance, mecanismo y **selección de estrategia (QNodes vs KQNodes)**.

- `src/controllers/manager.py`
  - Gestión de carga y generación de datos.
  - Determina la ruta del archivo CSV con la TPM correspondiente a `N{n}{pagina}`.

- `src/strategies/`
  - `q_nodes.py`: Implementa el algoritmo de bipartición (QNodes).
  - `KQNodes.py`: Implementa el algoritmo aglomerativo para k-particiones generalizadas.
  - `force.py`: Estrategia de fuerza bruta (opcional).

- `src/constants/`
  - `base.py`: Constantes de sistema, símbolos y rutas.
  - `error.py`: Funciones de validación de particiones y errores.
  - `models.py`: Etiquetas de estrategias y análisis.

## 🗂️ Estructura de carpetas

```
QNodes/
├── exec.py
├── README.md
├── results/
└── src/
    ├── main.py
    ├── controllers/
    │   └── manager.py
    ├── funcs/
    │   └── ... (iit, particion, format)
    ├── models/
    │   └── ... (base, core)
    ├── strategies/
    │   ├── q_nodes.py
    │   └── KQNodes.py
    └── constants/
        ├── base.py
        ├── error.py
        └── models.py
```

## 🧠 Estrategias de Partición

### 1. QNodes (Bipartición)
Algoritmo original para encontrar la bipartición óptima que minimiza la pérdida de información.

### 2. KQNodes (K-partición)
Estrategia voraz aglomerativa diseñada para encontrar la mejor k-partición definida por el usuario.
- **Diferencia clave**: Mientras que QNodes divide el sistema en dos, KQNodes fusiona nodos progresivamente hasta obtener exactamente `k` bloques.
- **Determinismo**: Utiliza un ordenamiento canónico para garantizar resultados reproducibles.
- **Memoización**: Optimizado para evitar reevaluaciones de particiones equivalentes mediante `clave_canonica`.

## ⚙️ Configuración y Ejecución

### Cómo elegir la estrategia (`src/main.py`)

Al llamar a `iniciar()` en `src/main.py`, puedes seleccionar la estrategia:

```python
# Para QNodes (Bipartición)
iniciar("N10A", usar_kqnodes=False)

# Para KQNodes (k-partición)
iniciar("N10A", usar_kqnodes=True, k=3)
```

### 🏃 Ejecución recomendada

Desde `ADA-Partition\QNodes`:

```powershell
# Usar el script de ejecución rápida
python exec.py
```

## 🧪 Validación y buenas prácticas

- **Constantes y Errores**: Todo el proyecto utiliza definiciones centralizadas en `src/constants/`. Al añadir nuevas estrategias, asegúrate de añadir sus tags en `models.py` y validaciones en `error.py`.
- **Integridad**: `KQNodes` implementa validaciones estrictas para asegurar que la entrada `k` sea válida respecto al número de nodos del subsistema.
- **Resultados**: Los resultados se guardan automáticamente en `results/resultados_qnodes.txt` o `results/resultados_kqnodes.txt` dependiendo de la estrategia utilizada.
