# K-GeoMIP — Guía de Pruebas

Extensión de GeoMIP para k-particiones (k ∈ {2, 3, 4, 5}).
Implementa la Partición de Mínima Información (k-MIP) mediante heurística greedy (LPT, Graham 1969).

---

## Tabla de contenidos

1. [Instalación rápida](#1-instalación-rápida)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Entender el Excel de pruebas](#3-entender-el-excel-de-pruebas)
4. [Ejecutar una prueba manual](#4-ejecutar-una-prueba-manual)
5. [Cambiar de estrategia (k)](#5-cambiar-de-estrategia-k)
6. [Muestras disponibles y cómo generarlas](#6-muestras-disponibles-y-cómo-generarlas)
7. [Ejecutar por lotes (runner automático)](#7-ejecutar-por-lotes-runner-automático)
8. [Referencia de estrategias](#8-referencia-de-estrategias)
9. [Tests de validación](#9-tests-de-validación)

---

## 1. Instalación rápida

**Requisito:** Python ≥ 3.9.13

Todos los comandos se ejecutan desde la carpeta de trabajo del método:

```
K-GeoMIP/src/Method2_Dynamic_Programming_Reformulation/
```

### Con uv (recomendado)

```powershell
cd "K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation"
uv sync
```

### Con pip

```powershell
cd "K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation"
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Verificar que la instalación funciona:

```powershell
.venv\Scripts\python.exe -c "from src.main import run_prueba; print('OK')"
```

---

## 2. Estructura del proyecto

```
projecto-analisis-20261/
│
├── docs/
│   └── DatosPruebas2026_1.xlsx        ← Excel con los casos de prueba de la profesora
│
└── K-GeoMIP/
    ├── data/
    │   └── samples/                   ← TPMs (archivos CSV por sistema)
    │       ├── N10A.csv               ← Red de 10 nodos (1 024 filas)
    │       ├── N15A.csv               ← Red de 15 nodos (32 768 filas)
    │       ├── N15B.csv               ← Red de 15 nodos alternativa
    │       └── ...                    ← N3A, N4A, N5A, N6A, N8A
    │
    ├── results/                       ← Archivos Excel de salida (se generan al correr)
    │
    └── src/
        └── Method2_Dynamic_Programming_Reformulation/    ← CARPETA DE TRABAJO
            ├── exec.py                ← Punto de entrada para el runner por lotes
            ├── src/
            │   ├── main.py            ← run_prueba() y runners por lotes
            │   └── controllers/
            │       └── strategies/
            │           ├── geometric.py    ← GeometricSIA  (k=2, bi-partición exacta)
            │           └── k_geometric.py  ← KGeometricSIA (k≥2, heurística greedy)
            └── tests/                 ← Suite de pruebas automatizadas (13 tests)
```

---

## 3. Entender el Excel de pruebas

El archivo está en: `docs/DatosPruebas2026_1.xlsx`

Contiene una hoja por tamaño de red:

| Hoja              | Sistema              | n nodos | Estado inicial           | CSV necesario           |
| ----------------- | -------------------- | ------- | ------------------------ | ----------------------- |
| `10A-Elementos` | ABCDEFGHIJ           | 10      | `1000000000`           | `N10A.csv` ✓         |
| `15B-Elementos` | ABCDEFGHIJKLMNO      | 15      | `100000000000000`      | `N15B.csv` ✓         |
| `20A-Elementos` | ABCDEFGHIJKLMNOPQRST | 20      | `10000000000000000000` | `N20A.csv` — generar |
| `22A-Elementos` | 22 nodos             | 22      | `1` + 21 ceros         | `N22A.csv` — generar |
| `25A-Elementos` | 25 nodos             | 25      | `1` + 24 ceros         | `N25A.csv` — generar |

### Columnas de cada hoja

```
Col A  — #Prueba
Col B  — Alcance o Purview (t+1)   ← letras de los nodos futuros,  ej: "ABCDEFGHIJ"
Col C  — Mecanismo(t)              ← letras de los nodos presentes, ej: "ACEGI"
Col D  — Partición    ┐
Col E  — Pérdida      ├ Bipartición QNodes     (llenar con estrategia QNodes, k=2)
Col F  — Tiempo       ┘
Col G  — Partición    ┐
Col H  — Pérdida      ├ Bipartición Geometric  (llenar con run_prueba(..., k=2))
Col I  — Tiempo       ┘
Col J  — Partición    ┐
Col K  — Pérdida      ├ 3-Partición QNodes     (llenar con estrategia QNodes, k=3)
Col L  — Tiempo       ┘
Col M  — Partición    ┐
Col N  — Pérdida      ├ 3-Partición Geometric  (llenar con run_prueba(..., k=3))
Col O  — Tiempo       ┘
... (análogamente para k=4 y k=5)
```

### Qué significan las letras

Cada letra es el nombre de un nodo del sistema. La posición en el alfabeto es su índice:

```
A = nodo 0,  B = nodo 1,  C = nodo 2, ...,  J = nodo 9
```

| Excel (letras) | Bits en el modelo | Nodos activos |
| -------------- | ----------------- | ------------- |
| `ABCDEFGHIJ` | `1111111111`    | Todos (10/10) |
| `ABCDEFGHI`  | `1111111110`    | Sin J         |
| `BCDEFGHIJ`  | `0111111111`    | Sin A         |
| `ACEGI`      | `1010101010`    | Nodos pares   |
| `BDFHJ`      | `0101010101`    | Nodos impares |

Esta conversión la hace automáticamente la función `run_prueba` — no tienes que calcularla a mano.

---

## 4. Ejecutar una prueba manual

La función `run_prueba` toma exactamente las letras que ves en las columnas B y C del Excel.

### Ubicación de trabajo

```powershell
cd "K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation"
```

### Forma 1 — Una línea en la terminal (más rápida)

```powershell
# Bipartición (k=2) — llena las columnas G,H,I del Excel
.venv\Scripts\python.exe -c "
from src.main import run_prueba
run_prueba('ABCDEFGHIJ', 'ABCDEFGHIJ', k=2)
"
```

```powershell
# Tripartición (k=3) — llena las columnas M,N,O del Excel
.venv\Scripts\python.exe -c "
from src.main import run_prueba
run_prueba('ABCDEFGHIJ', 'ACEGI', k=3)
"
```

### Forma 2 — Script de pruebas (recomendada para varias pruebas)

Crea un archivo `mis_pruebas.py` dentro de `Method2_Dynamic_Programming_Reformulation/`:

```python
# mis_pruebas.py
from src.main import run_prueba

# ── Hoja 10A-Elementos ──────────────────────────────────────────────────────
# Indicar siempre el estado_inicio cuando ejecutes manualmente
ESTADO_10A = "1000000000"

# Prueba 1 — Alcance: ABCDEFGHIJ | Mecanismo: ABCDEFGHIJ
run_prueba("ABCDEFGHIJ", "ABCDEFGHIJ", k=2, estado_inicio=ESTADO_10A)
run_prueba("ABCDEFGHIJ", "ABCDEFGHIJ", k=3, estado_inicio=ESTADO_10A)

# Prueba 6 — Alcance: ABCDEFGHIJ | Mecanismo: ACEGI
run_prueba("ABCDEFGHIJ", "ACEGI", k=2, estado_inicio=ESTADO_10A)
run_prueba("ABCDEFGHIJ", "ACEGI", k=3, estado_inicio=ESTADO_10A)

# ── Hoja 15B-Elementos ──────────────────────────────────────────────────────
ESTADO_15B = "100000000000000"

run_prueba("ABCDEFGHIJKLMNO", "ABCDEFGHIJKLMNO", k=2, estado_inicio=ESTADO_15B)
```

Ejecutar:

```powershell
.venv\Scripts\python.exe mis_pruebas.py
```

### Salida esperada

```
==================================================
Sistema:        ABCDEFGHIJ
Estado inicial: 1000000000
Alcance:        ABCDEFGHIJ -> 1111111111
Mecanismo:           ACEGI -> 1010101010
k = 2
==================================================

Estrategia : Geometric
Partición  :
| A,B,C,D,E,F,G,H,I,J ||    ∅    |
|        ∅             || a,b,...  |

Pérdida    : 0.472656
Tiempo     : 0.1682 s
```

Los valores de **Partición**, **Pérdida** y **Tiempo** son los que debes registrar en el Excel.

### Parámetros de `run_prueba`

| Parámetro        | Tipo    | Descripción                                                                | Ejemplo          |
| ----------------- | ------- | --------------------------------------------------------------------------- | ---------------- |
| `alcance`       | `str` | Letras de la columna B del Excel                                            | `"ABCDEFGHIJ"` |
| `mecanismo`     | `str` | Letras de la columna C del Excel                                            | `"ACEGI"`      |
| `k`             | `int` | Número de particiones: 2, 3, 4 o 5                                         | `2`            |
| `estado_inicio` | `str` | Estado inicial del sistema (bits). Si es None se infiere del CSV disponible | `"1000000000"` |
| `condiciones`   | `str` | Sistema candidato en bits. Si es None, se asume el sistema completo         | `None`         |

---

## 5. Cambiar de estrategia (k)

### Desde `run_prueba` (pruebas manuales)

Simplemente cambia el valor de `k`:

```python
# Bipartición exacta (GeoMIP, columnas G-I del Excel)
run_prueba("ABCDEFGHIJ", "ACEGI", k=2)

# Tripartición greedy (K-GeoMIP, columnas M-O del Excel)
run_prueba("ABCDEFGHIJ", "ACEGI", k=3)

# Cuadripartición (columnas S-U del Excel)
run_prueba("ABCDEFGHIJ", "ACEGI", k=4)

# Quintapartición (columnas Y-AA del Excel)
run_prueba("ABCDEFGHIJ", "ACEGI", k=5)
```

### Desde el runner por lotes (`exec.py`)

**Opción A — Variable de entorno (terminal)**

```powershell
# PowerShell — Windows
$env:KGEOMIP_K = "3"
.venv\Scripts\python.exe exec.py

# CMD — Windows
set KGEOMIP_K=3
.venv\Scripts\python.exe exec.py
```

**Opción B — Editar `exec.py` directamente**

Abre `exec.py` y descomenta la línea del k deseado:

```python
# os.environ["KGEOMIP_K"] = "3"   # tri-partición   (k=3)
# os.environ["KGEOMIP_K"] = "4"   # cuad-partición  (k=4)
# os.environ["KGEOMIP_K"] = "5"   # quint-partición (k=5)
iniciar()
```

### Tabla de correspondencia k ↔ columnas del Excel ↔ estrategia

| k | Columnas Excel | Estrategia usada  | Descripción                          |
| - | -------------- | ----------------- | ------------------------------------- |
| 2 | G, H, I        | `GeometricSIA`  | Bipartición exacta (GeoMIP original) |
| 3 | M, N, O        | `KGeometricSIA` | Tripartición heurística greedy      |
| 4 | S, T, U        | `KGeometricSIA` | Cuadripartición heurística greedy   |
| 5 | Y, Z, AA       | `KGeometricSIA` | Quintapartición heurística greedy   |

---

## 6. Muestras disponibles y cómo generarlas

Las TPMs se guardan en `K-GeoMIP/data/samples/`. El modelo las busca automáticamente por nombre `NxA.csv` según la longitud del estado inicial.

### Muestras ya generadas

| Archivo      | Nodos (n) | Filas TPM | Sirve para hoja   |
| ------------ | --------- | --------- | ----------------- |
| `N10A.csv` | 10        | 1 024     | `10A-Elementos` |
| `N15A.csv` | 15        | 32 768    | — (alternativa)  |
| `N15B.csv` | 15        | 32 768    | `15B-Elementos` |
| `N3A.csv`  | 3         | 8         | pruebas pequeñas |
| `N4A.csv`  | 4         | 16        | pruebas pequeñas |
| `N5A.csv`  | 5         | 32        | pruebas pequeñas |
| `N6A.csv`  | 6         | 64        | pruebas pequeñas |
| `N8A.csv`  | 8         | 256       | pruebas medianas  |

### Generar muestras para n=20, 22, 25

Las hojas `20A-Elementos`, `22A-Elementos` y `25A-Elementos` requieren generar sus TPMs primero.
Usa el método `generar_red` del Manager desde `Method2_Dynamic_Programming_Reformulation/`:

```powershell
.venv\Scripts\python.exe -c "
from src.controllers.manager import Manager
m = Manager('10000000000000000000')   # 20 ceros para n=20
m.generar_red(20)                     # genera N20A.csv en data/samples/
"
```

> **Advertencia de tiempo y disco (la RAM ya no es el cuello de botella — ver sección siguiente):**
>
> - n=20 → 2²⁰ × 20 ≈ **20 millones de filas** — tarda varios minutos, ocupa ~200 MB en disco
> - n=22 → 2²² × 22 ≈ **88 millones de filas** — ~1 GB en disco (el script pedirá confirmación)
> - n=25 → 2²⁵ × 25 ≈ **838 millones de filas** — varios GB en disco, el script pedirá confirmación

Ajusta el número de ceros según el n deseado:

| Hoja              | n  | Estado inicial a usar | RAM pico | Tiempo estimado |
| ----------------- | -- | --------------------- | -------- | --------------- |
| `20A-Elementos` | 20 | `"1" + "0"*19`      | ~4 MB    | ~5–10 min      |
| `22A-Elementos` | 22 | `"1" + "0"*21`      | ~4 MB    | ~30–60 min     |
| `25A-Elementos` | 25 | `"1" + "0"*24`      | ~4 MB    | varias horas    |

---

### Generación por chunks — cómo funciona y por qué existe

#### ¿Qué es un chunk?

Un **chunk** (palabra inglesa que significa "trozo" o "pedazo") es una porción o bloque de datos que se procesa de a una vez, en lugar de procesar todo el conjunto de datos de un solo golpe.

La idea se entiende mejor con una analogía cotidiana:

> Imagina que tienes que copiar a mano un libro de 1 000 000 de páginas.
> - **Sin chunks:** intentas memorizar las 1 000 000 páginas completas primero, y luego las escribes. Imposible — tu cabeza no tiene esa capacidad.
> - **Con chunks:** copias 100 páginas, las escribes, las olvidas, copias las siguientes 100, y así sucesivamente. El resultado final es idéntico, pero tu cabeza solo necesita recordar 100 páginas a la vez.

En programación ocurre lo mismo: la RAM de la computadora es la "cabeza" y los datos son el "libro". Procesar en chunks permite manejar volúmenes de datos que no caben en RAM, escribiendo cada porción al disco antes de generar la siguiente.

```
Sin chunks:   [genera 32M filas → 800MB RAM] → [escribe todo al disco]
                ↑ falla con MemoryError para n≥27

Con chunks:   [genera 65536 filas → 4MB RAM] → [escribe al disco]
              [genera 65536 filas → 4MB RAM] → [escribe al disco]   × 512 veces
              ... (mismo resultado final, RAM constante)
```

#### El problema: cuello de botella exponencial en RAM

Una TPM de `n` nodos tiene exactamente **2ⁿ filas** (una por cada combinación binaria posible de estados). La implementación ingenua aloca toda la matriz de una sola vez:

```python
# Implementación ANTERIOR — crea todo en RAM de golpe
states = np.random.randint(2, size=(2**n, n), dtype=np.int8)
```

El costo en RAM crece exponencialmente:

| n  | Filas (2ⁿ)      | RAM requerida    | Resultado            |
| -- | --------------- | ---------------- | -------------------- |
| 20 | 1 048 576       | ~20 MB           | OK                   |
| 22 | 4 194 304       | ~88 MB           | OK (pero ajustado)   |
| 25 | 33 554 432      | ~800 MB          | Riesgo de lentitud   |
| 27 | 134 217 728     | ~3.2 GB          | `MemoryError` típico |
| 30 | 1 073 741 824   | ~30 GB           | Inviable             |

#### La solución: generación por bloques (chunks)

La implementación actual divide la generación en lotes de **`CHUNK_SIZE = 65 536` filas** (2¹⁶), generando y escribiendo cada bloque al archivo antes de pasar al siguiente:

```python
CHUNK_SIZE = 1 << 16  # 65 536 filas por lote

with open(filepath, "w") as f:
    for chunk_start in range(0, num_estados, CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, num_estados)
        chunk = np.random.randint(2, size=(chunk_end - chunk_start, n), dtype=np.int8)
        np.savetxt(f, chunk, delimiter=",", fmt="%d")
```

#### Por qué el resultado es idéntico al método anterior

La clave es el generador pseudoaleatorio (Mersenne Twister) de NumPy. Su estado interno avanza **en el mismo orden secuencial** independientemente del tamaño del array solicitado. Al fijar la semilla con `np.random.seed(semilla)` una sola vez antes del loop, los números generados chunk a chunk son bit-a-bit idénticos a los que se obtendrían con una única llamada `randint(2, size=(2^n, n))`.

#### Impacto en memoria

| n  | RAM (antes)  | RAM (ahora, CHUNK_SIZE=65 536) |
| -- | ------------ | ------------------------------ |
| 20 | ~20 MB       | ~1.3 MB por chunk              |
| 22 | ~88 MB       | ~1.4 MB por chunk              |
| 25 | ~800 MB      | ~1.6 MB por chunk              |
| 27 | ~3.2 GB ⚠️  | ~1.6 MB por chunk ✓            |

El pico de RAM es ahora **O(CHUNK_SIZE × n) ≈ 4 MB** para cualquier valor de `n`. El límite real pasa a ser el espacio en disco, no la RAM.

#### Limitación que persiste

La generación por chunks no elimina el cuello de botella exponencial del **tamaño en disco**: para n=30 el archivo resultante ocuparía ~30 GB, lo que sigue siendo inviable. Ese es exactamente el problema que el algoritmo **GeometricSIA / K-GeoMIP** ataca desde el diseño algorítmico, operando en tiempo polinomial sin necesidad de materializar la TPM completa.

---

## 7. Ejecutar por lotes (runner automático)

El runner automático lee un Excel con subsistemas, ejecuta la estrategia en cada fila y guarda resultados.

> Este runner usa un formato de Excel diferente al de pruebas de la profesora. Para las pruebas del Excel de la profesora, usa `run_prueba` (sección 4) de forma manual.

### Configuración del runner

| Variable de entorno    | Default                          | Descripción                          |
| ---------------------- | -------------------------------- | ------------------------------------- |
| `KGEOMIP_K`          | `2`                            | Número de particiones: 2, 3, 4 o 5   |
| `GEOMIP_INPUT_XLSX`  | `results/Pruebas_Metodo2.xlsx` | Excel de entrada con subsistemas      |
| `GEOMIP_OUTPUT_XLSX` | Auto según k (ver abajo)        | Excel donde se guardan los resultados |

Archivos de salida generados automáticamente en `K-GeoMIP/results/`:

| k | Archivo de salida                 |
| - | --------------------------------- |
| 2 | `resultados_Geometric.xlsx`     |
| 3 | `resultados_KGeometric_k3.xlsx` |
| 4 | `resultados_KGeometric_k4.xlsx` |
| 5 | `resultados_KGeometric_k5.xlsx` |

### Ejecución del runner

```powershell
# Desde K-GeoMIP/src/Method2_Dynamic_Programming_Reformulation/

# k=2 (bipartición exacta)
.venv\Scripts\python.exe exec.py

# k=3 (tripartición greedy)
$env:KGEOMIP_K = "3"
.venv\Scripts\python.exe exec.py

# k=4 o k=5
$env:KGEOMIP_K = "4"
.venv\Scripts\python.exe exec.py
```

---

## 8. Referencia de estrategias

| Estrategia | Clase             | k     | Complejidad           | Descripción                                |
| ---------- | ----------------- | ----- | --------------------- | ------------------------------------------- |
| GeoMIP     | `GeometricSIA`  | 2     | Θ(n·2ⁿ)            | Bipartición exacta — búsqueda exhaustiva |
| K-GeoMIP   | `KGeometricSIA` | 2     | Θ(n·2ⁿ)            | Delega a GeometricSIA (resultado idéntico) |
| K-GeoMIP   | `KGeometricSIA` | 3,4,5 | Θ(n·2ⁿ)+O(n log n) | k-partición heurística greedy (LPT)       |

**Garantía heurística (Graham, 1969):**

```
makespan(LPT) ≤ (4/3 − 1/(3k)) × OPT
```

**Tiempos de referencia (subsistema completo, estado inicial = "1" + ceros):**

| n  | k=2    | k=3    | k=4    | k=5    |
| -- | ------ | ------ | ------ | ------ |
| 6  | 0.04 s | 0.02 s | 0.02 s | 0.02 s |
| 10 | 0.17 s | 0.11 s | 0.13 s | 0.12 s |
| 15 | ~8 s   | ~8 s   | ~8 s   | ~8 s   |

---

## 9. Tests de validación

```powershell
# Desde K-GeoMIP/src/Method2_Dynamic_Programming_Reformulation/
.venv\Scripts\python.exe -m pytest tests/ -v
```

Suite de 13 tests que verifican:

- **Corrección:** KGeometricSIA(k=2) produce el mismo resultado que GeometricSIA
- **Validez:** Solution bien formada para k ∈ {3,4,5}
- **Rendimiento:** heurística greedy 30× más rápida que exhaustivo (n=6, k=3)

---

## 10. Interfaz Interactiva de Terminal

La interfaz interactiva guía al usuario paso a paso para ingresar los parámetros,
muestra qué CSV se está cargando, permite elegir la variante cuando hay varias,
y genera una gráfica de rendimiento comparando k=2,3,4,5.

### Instalación (primera vez)

```powershell
# 1. Ir a la carpeta de trabajo del método
cd "K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation"

# 2. Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias (colorama, matplotlib/manim, numpy, pandas, etc.)
pip install -e .
```

> Si ya tienes el entorno con `uv sync`, salta directamente al paso de ejecución.

### Verificar instalación

```powershell
# Desde Method2_Dynamic_Programming_Reformulation/
.venv\Scripts\python.exe -c "from src.main import run_prueba; print('OK')"
```

### Ejecutar la interfaz interactiva

```powershell
# Desde Method2_Dynamic_Programming_Reformulation/
.venv\Scripts\python.exe interactive.py
```

### Flujo de la interfaz

Al ejecutar `interactive.py` el sistema:

1. **Detecta los CSV disponibles** en `K-GeoMIP/data/samples/` y los muestra en tabla.
2. **PASO 1 — Sistema y variante:** elige n de la lista o escribe el estado inicial en bits;
   si hay múltiples variantes para el mismo n (ej. N15A.csv y N15B.csv), muestra un menú de selección.
3. **PASO 2 — Alcance y Mecanismo:** ingresa las letras de los nodos (ej. `ABCDEFGHIJ`, `ACEGI`);
   valida el rango y muestra la conversión letras→bits en tiempo real.
4. **PASO 3 — k:** elige el número de particiones (2=exacta, 3/4/5=greedy).
5. **PASO 4 — Confirmación:** revisa el resumen y confirma la ejecución.
6. **Ejecución:** muestra `Cargando TPM: N10A.csv ...` e imprime el resultado con partición, δk y tiempo.
7. **Gráfica (opcional):** ejecuta el algoritmo para k=2,3,4,5 y guarda una gráfica PNG en
   `interactive_output/benchmark_N10A_ABCDEFGHIJ_ACEGI_k2a5_<timestamp>.png`.

### Ejemplo de sesión

```
╔══════════════════════════════════════════════════════════════╗
║   K - G e o M I P   I n t e r a c t i v o                   ║
║   K-Partición de Mínima Información (k-MIP)                  ║
╚══════════════════════════════════════════════════════════════╝

── CSV disponibles en disco ──────────────────────────────────────
     n  Variante(s)     Filas TPM  Archivo(s)
    ──  ──────────────  ─────────  ────────────────────
     3  A  B                    8  N3A.csv, N3B.csv
    10  A                    1024  N10A.csv
    15  A  B               32,768  N15A.csv, N15B.csv

── PASO 1 de 4 — Sistema, Estado Inicial y Variante ─────────────
  › Opción [1]: 1
  ...
  ✓  Se cargará: N10A.csv
  ✓  Estado inicial: 1000000000
```

---

## Resumen de comandos

```powershell
# ── Carpeta de trabajo ───────────────────────────────────────────────────────
cd "K-GeoMIP\src\Method2_Dynamic_Programming_Reformulation"

# ── Interfaz interactiva (recomendada para pantallazos del manual) ────────────
.venv\Scripts\python.exe interactive.py

# ── Prueba manual directa (para una prueba puntual) ──────────────────────────
.venv\Scripts\python.exe -c "
from src.main import run_prueba
run_prueba('ABCDEFGHIJ', 'ACEGI', k=2, estado_inicio='1000000000')
"

# ── Cambiar k ────────────────────────────────────────────────────────────────
# En run_prueba: cambia el parámetro k=2, k=3, k=4 o k=5
# En exec.py:    $env:KGEOMIP_K = "3"  antes de ejecutar

# ── Runner por lotes ─────────────────────────────────────────────────────────
.venv\Scripts\python.exe exec.py

# ── Tests ────────────────────────────────────────────────────────────────────
.venv\Scripts\python.exe -m pytest tests/ -v

# ── Benchmark experimental ───────────────────────────────────────────────────
.venv\Scripts\python.exe experiments/benchmark_paso6.py
```


```bash
 python run_10A_k.py | tee salida.txt
```
