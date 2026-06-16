# Proyecto-20261

Este repositorio contiene tres implementaciones principales para el análisis de MIP/IIT (Partición de Mínima Información en la Teoría de la Información Integrada):

1. **QNodes** - Framework base clásico para análisis MIP/IIT
2. **GeoMIP** - Método 2 con Programación Dinámica
3. **K-GeoMIP** - Extensión a k-Particiones (k=2,3,4,5)

---

## 📋 Software Requerido

### Requisitos del Sistema

#### Sistema Operativo
- **Windows 10/11** (probado y verificado)
- **Linux** (Ubuntu 20.04+)
- **macOS** (versiones recientes)

#### Procesador y Memoria
- **Procesador**: Intel Core i5 (2.5 GHz) o superior / AMD Ryzen 5 o superior
- **Memoria RAM**: 
  - Mínima: 8 GB
  - Recomendada: 16 GB o superior
  - Para sistemas con 20+ nodos: 32 GB

#### Espacio en Disco
- Mínimo: 2 GB
- Recomendado: 5 GB (para datos de prueba y resultados)

### Software Base Obligatorio

#### Python
- **Versión**: Python **3.11+** (recomendado 3.12)
- **Mínimo soportado**: Python 3.9.13 (para ciertos módulos)
- **Descarga**: https://www.python.org/downloads/

Verificar instalación:
```bash
python --version
```

#### Gestor de Dependencias

**Opción 1: `uv` (Recomendado - Más rápido)**
```bash
pip install uv
```

**Opción 2: `pip` (Gestor estándar)**
```bash
# Viene incluido con Python
```

#### Compilador C++ (Solo Windows)
Si PyPhi genera errores de compilación, instalar:
- **Microsoft Visual C++ Build Tools**
- https://visualstudio.microsoft.com/es/visual-cpp-build-tools/
- Seleccionar: "Desarrollo de C++" + "MSVC v142 - VS 2019 C++ x64/x86"

### Dependencias Python Principales

Todas se instalan automáticamente al ejecutar `uv sync` o `pip install -e .`

| Librería | Versión | Propósito |
|----------|---------|----------|
| **NumPy** | ≥2.0.2 | Cálculos numéricos y matrices |
| **SciPy** | ≥1.17.0 | Algoritmos científicos |
| **PyPhi** | ≥1.2.0 | Cálculo de Información Integrada (IIT) |
| **Pandas** | ≥2.3.3 | Manipulación de datos en Excel/CSV |
| **OpenPyXL** | ≥3.1.3/3.1.5 | Lectura/escritura de archivos Excel |
| **PyInstrument** | ≥5.1.2 | Profiling y análisis de rendimiento |
| **pyttsx3** | ≥2.98/2.99 | Síntesis de voz en español |
| **Colorama** | ≥0.4.5/0.4.6 | Colores en terminal (Windows) |
| **Manim** | ≥0.19.0 | Animaciones matemáticas (K-GeoMIP) |
| **pytest** | ≥9.0.0 | Framework de testing (K-GeoMIP) |

### Herramientas Opcionales (Recomendadas)

**Para Desarrollo**
- Visual Studio Code (IDE recomendado)
  - Extensiones: Python, PyLance, Jupyter

**Para Análisis de Resultados**
- Microsoft Excel 2019+ o LibreOffice Calc
- Jupyter Notebook: `pip install jupyter`

**Para Generación de Documentación**
- OBS Studio (captura de pantalla)
- Herramientas de subtitulado: Subtitle Edit

---

## ⚙️ Configuración de Entorno Virtual

### Con `uv` (Recomendado)

Para **QNodes**:
```bash
cd QNodes
uv sync
```

Para **K-GeoMIP**:
```bash
cd K-GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync
```

Para **GeoMIP**:
```bash
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync
```

### Con `pip` (Alternativa)

```bash
cd QNodes  # o la carpeta del módulo que desees
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -e .
```

### Verificación de Instalación

```bash
# Verificar Python
python --version  # Debe ser 3.11+

# Verificar dependencias
python -c "import numpy, scipy, pyphi, pandas; print('✓ OK')"

# Ejecutar prueba rápida
cd QNodes
uv run exec.py
```

## 📂 Estructura del Proyecto

```
ADA-Partition/
├── README.md                           ← Este archivo
├── docs/
│   ├── KGeoMIP_Documentacion_Unificada.md
│   ├── manualTecnico.md
│   └── DatosPruebas2026_1.xlsx
│
├── QNodes/                             ← Framework base clásico
│   ├── src/
│   │   ├── main.py
│   │   ├── constants/
│   │   ├── controllers/
│   │   ├── funcs/
│   │   ├── middlewares/
│   │   ├── models/
│   │   └── strategies/
│   ├── data/samples/                   ← TPMs (N*.csv)
│   ├── results/
│   ├── pyproject.toml
│   └── exec.py
│
├── GeoMIP/                             ← Método 2 (Programación Dinámica)
│   ├── data/samples/                   ← TPMs para GeoMIP
│   ├── results/
│   └── src/
│       └── Method2_Dynamic_Programming_Reformulation/
│           ├── src/
│           ├── pyproject.toml
│           └── exec.py
│
└── K-GeoMIP/                           ← Extensión a k-Particiones
    ├── data/samples/                   ← TPMs para K-GeoMIP
    ├── results/
    ├── README.md
    └── src/
        └── Method2_Dynamic_Programming_Reformulation/
            ├── src/
            ├── tests/
            ├── experiments/
            ├── pyproject.toml
            └── exec.py
```

### Módulos Disponibles

| Módulo | Ubicación | Propósito | Entrada | Salida |
|--------|-----------|----------|---------|--------|
| **QNodes** | `QNodes/` | Análisis MIP/IIT (base clásica) | Configuración en `main.py` | Partición óptima + consola |
| **GeoMIP Método 2** | `GeoMIP/src/Method2_*` | Procesamiento por lotes con DP | Excel: `Pruebas_Metodo2.xlsx` | `resultados_Geometric.xlsx` |
| **K-GeoMIP** | `K-GeoMIP/src/Method2_*` | k-Particiones (k=2,3,4,5) | Excel con TPMs | k-Particiones óptimas |

### Datasets Disponibles (TPMs)

```
Ubicación: K-GeoMIP/data/samples/ o GeoMIP/data/samples/
Formato: CSV (Transition Probability Matrices)

Sistemas disponibles:
├── N3A.csv   - 3 nodos (8 filas)
├── N4A.csv   - 4 nodos (16 filas)
├── N5A.csv   - 5 nodos (32 filas)
├── N6A.csv   - 6 nodos (64 filas)
├── N8A.csv   - 8 nodos (256 filas)
├── N10A.csv  - 10 nodos (1,024 filas)
├── N15A.csv  - 15 nodos (32,768 filas)
└── N15B.csv  - 15 nodos alternativo
```

---

## 🚀 Ejecución Rápida

### 1) Ejecutar QNodes

Análisis MIP/IIT del framework base.

#### Instalación

```bash
cd QNodes
uv sync
```

#### Ejecución

```bash
uv run exec.py
```

#### ¿Qué hace?

- Carga una red desde `QNodes/src/.samples/` (según estado inicial configurado)
- Ejecuta estrategia `BruteForce` desde `QNodes/src/main.py`
- Imprime la solución en consola

#### Ajustes comunes

Edita `QNodes/src/main.py`:

```python
estado_inicial = "1000000000"  # Estado binario inicial
condicion = "1111111111"       # Variables condicionadas
alcance = "1111111111"         # Variables de alcance
mecanismo = "1111111111"       # Variables de mecanismo
```

**Nota**: Si termina muy rápido, no necesariamente es error. Puede ser un caso pequeño o corte temprano cuando φ = 0.

---

### 2) Ejecutar K-GeoMIP

Extensión a k-Particiones (k=2,3,4,5).

#### Instalación

```bash
cd K-GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync
```

#### Ejecución

```bash
uv run exec.py
```

#### Cambiar valor de k

Edita `exec.py`:

```python
# Descomenta el valor de k deseado:
# os.environ["KGEOMIP_K"] = "2"  # Bi-particiones
# os.environ["KGEOMIP_K"] = "3"  # Tri-particiones
# os.environ["KGEOMIP_K"] = "4"  # Tetra-particiones
# os.environ["KGEOMIP_K"] = "5"  # Penta-particiones
```

#### Entrada por defecto

- Excel entrada: `K-GeoMIP/results/Pruebas_Metodo2.xlsx`
- Hoja usada: índice 8
- Columna subsistema: B

#### Salida por defecto

- Excel salida: `K-GeoMIP/results/resultados_Geometric.xlsx`

#### Ejecutar Tests

```bash
pytest tests/
```

---

### 3) Ejecutar GeoMIP - Método 2 (Programación Dinámica)

Procesamiento por lotes desde Excel.

#### Instalación

Desde `GeoMIP/src/Method2_Dynamic_Programming_Reformulation/`:

```bash
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync
```

#### Ejecución

```bash
uv run exec.py
```

#### Entrada por defecto

- Excel entrada: `GeoMIP/results/Pruebas_Metodo2.xlsx`
- Hoja usada actualmente: índice `8`
- Columna subsistema: `B`

#### Salida por defecto

- Excel salida: `GeoMIP/results/resultados_Geometric.xlsx`

---

## 🔧 Solución de Problemas

### Error: "PyPhi no se compila" (Windows)

**Causa**: Falta compilador C++

**Solución**:
1. Instalar [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/es/visual-cpp-build-tools/)
2. Seleccionar: "Desarrollo de C++" + "MSVC v142 - VS 2019"
3. Reiniciar Visual Studio Code
4. Reintentar: `uv sync`

### Error: "Python version not supported"

**Causa**: Versión de Python < 3.9

**Solución**:
```bash
python --version  # Verificar versión actual
# Descargar Python 3.11+ desde https://www.python.org/downloads/
```

### Error: "uv command not found"

**Causa**: `uv` no está instalado

**Solución**:
```bash
pip install uv
uv --version  # Verificar instalación
```

### Error: "Módulo no encontrado" (ImportError)

**Causa**: Dependencias no instaladas

**Solución**:
```bash
cd [carpeta-del-modulo]
uv sync
# O con pip:
pip install -e .
```

### Excel generado está vacío

**Causa**: Archivo Excel de entrada mal configurado

**Solución**:
1. Verificar que `Pruebas_Metodo2.xlsx` existe
2. Verificar índice de hoja (por defecto: 8)
3. Verificar que columna subsistema es `B`
4. Editar `exec.py` si es necesario

---

## 📚 Documentación Adicional

- **Manual Técnico Completo**: Ver `docs/manualTecnico.md`
- **Documentación Unificada**: Ver `docs/KGeoMIP_Documentacion_Unificada.md`
- **Guía K-GeoMIP**: Ver `K-GeoMIP/README.md`
- **Manual QNodes**: Ver `QNodes/.docs/application.md`

---

## ⚡ Rendimiento y Limitaciones

### Memoria Crítica
El recurso más crítico es la **memoria RAM**:
- Sistemas < 10 nodos: 8 GB suficiente
- Sistemas 10-15 nodos: 16 GB recomendado
- Sistemas > 20 nodos: 32+ GB necesario

### Hardware No Necesario
- ❌ GPU (no utilizada)
- ❌ Internet (offline)
- ❌ Servidor web

### Características No Implementadas
- Paralelización automática
- Computación distribuida
- GPU acceleration

---

## 🤝 Referencia de Módulos

### Funcionalidades por Módulo

| Feature | QNodes | GeoMIP | K-GeoMIP |
|---------|--------|--------|----------|
| Bi-particiones (k=2) | ✓ | ✓ | ✓ |
| Tri-particiones (k=3) | ✗ | ✗ | ✓ |
| Tetra-particiones (k=4) | ✗ | ✗ | ✓ |
| Penta-particiones (k=5) | ✗ | ✗ | ✓ |
| Procesamiento Excel | ✗ | ✓ | ✓ |
| Suite de Tests | ✗ | ✗ | ✓ |
| Síntesis de Voz | ✓ | ✓ | ✓ |
| Profiling | ✓ | ✓ | ✓ |

---

## 📝 Requisitos Específicos por Módulo

### QNodes
- Python 3.11+
- Compilador C++ (Windows)
- Memoria: 8+ GB

### GeoMIP Método 2
- Python 3.9.13+
- Manim (para visualizaciones)
- Memoria: 8+ GB

### K-GeoMIP
- Python 3.10+ (recomendado 3.11+)
- Pytest (para tests)
- Memoria: 16+ GB (recomendado)

---

## 📋 Checklist de Verificación

- [ ] Python 3.11+ instalado
- [ ] `uv` instalado (`pip install uv`)
- [ ] Compilador C++ instalado (solo Windows)
- [ ] `uv sync` ejecutado en el módulo deseado
- [ ] `python --version` muestra 3.11+
- [ ] `uv run exec.py` ejecuta sin errores
- [ ] Archivos CSV de datos existen

---
**Link de excel con pruebas**: https://docs.google.com/spreadsheets/d/1UcdvKTAgzm8JUrybFHjEzWrnSG4rzHATAbgcXIfmu0A/edit?pli=1&gid=1582958587#gid=1582958587
**Última actualización**: 2026-06-15  
**Versión del Proyecto**: 0.1.0  
**Estado**: Estable
