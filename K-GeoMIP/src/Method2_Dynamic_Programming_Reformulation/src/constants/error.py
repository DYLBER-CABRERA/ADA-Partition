# Lógica: Constante de mensaje de error para validación de incompatibilidad de tamaños entre
#         estado_inicial, condiciones, alcance y mecanismo. Centraliza el texto para que
#         modificaciones del mensaje requieran cambiar solo este archivo.
# Sintaxis: `str` como anotación de tipo en la asignación de módulo confirma el tipo de la constante;
#           la convención ALL_CAPS indica constante de módulo inmutable a lo largo del proyecto.
ERROR_INCOMPATIBLE_SIZES: str = "El estado inicial tiene una dimensión diferente con las condiciones, alcance o mecanismo."
