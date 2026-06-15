from enum import Enum


# Lógica: Enumera las métricas de distancia disponibles para el cálculo EMD entre distribuciones;
#         centraliza el despacho en `seleccionar_metrica` (funcs/base.py) como tipo seguro
#         en lugar de strings literales dispersos que pueden sufrir typos silenciosos.
# Sintaxis: `class Name(Enum)` declara una enumeración de Python; cada atributo de clase se
#           convierte en un miembro Enum con `.name` (nombre Python) y `.value` (el string literal).
class MetricDistance(Enum):
    """La clase notaciones recopila diferentes notaciones binarias. Al definir el tipo se accede por `.value`."""

    EMD_EFECTO = "emd-effect"
    EMD_CAUSA = "emd-cause"
    MANHATTAN = "distancia-manhattan"
    EUCLIDIANA = "distancia-euclidiana"
