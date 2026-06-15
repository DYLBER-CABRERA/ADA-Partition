from enum import Enum


# Lógica: Enumera las notaciones de representación binaria para reindexar() / seleccionar_subestado()
#         en funcs/base.py; permite despacho verificable estáticamente en lugar de depender de
#         strings literales dispersos. LIL_ENDIAN y BIG_ENDIAN son las implementadas actualmente;
#         el resto (GRAY_CODE, SIGN_MAGNITUDE, TWOS_COMPLEMENT) está reservado para extensión futura.
# Sintaxis: `class Name(Enum)` declara la enumeración; cada miembro tiene `.name` (nombre Python)
#           y `.value` (el string de protocolo usado en la convención del proyecto).
class Notation(Enum):
    """La clase notaciones recopila diferentes notaciones binarias. Al definir el tipo se accede por `.value`."""

    LIL_ENDIAN = "little-endian"
    BIG_ENDIAN = "big-endian"
    GRAY_CODE = "gray-code"
    SIGN_MAGNITUDE = "sign-magnitude"
    TWOS_COMPLEMENT = "two's-complement"
