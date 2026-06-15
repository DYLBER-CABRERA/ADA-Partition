from src.models.base.application import aplicacion
from src.main import iniciar
import os


def main():
    """Inicializar el aplicativo."""
    # Lógica: Activa el profiler de pyinstrument para registrar tiempos de ejecución por función.
    # Sintaxis: Asignación directa al objeto singleton `aplicacion`; el flag es leído por el decorator @profile.
    aplicacion.profiler_habilitado = True

    # Lógica: Configura el valor de k para el análisis K-GeoMIP.
    #         k=2 (default) → GeometricSIA exacto (bi-partición, comportamiento original).
    #         k∈{3,4,5}    → KGeometricSIA greedy (k-partición, extensión K-GeoMIP).
    #         Para cambiar k, descomenta una de las líneas siguientes o define KGEOMIP_K en el entorno del SO.
    # Sintaxis: `os.environ["KGEOMIP_K"] = "N"` define la variable en el proceso actual; debe ser string.
    # os.environ["KGEOMIP_K"] = "3"   # tri-partición   (k=3)
    # os.environ["KGEOMIP_K"] = "4"   # cuad-partición  (k=4)
    # os.environ["KGEOMIP_K"] = "5"   # quint-partición (k=5)

    # Lógica: Llama al punto de entrada principal que despacha a GeometricSIA o KGeometricSIA según KGEOMIP_K.
    # Sintaxis: `iniciar()` es la función importada de main.py; no recibe argumentos directos (usa os.environ).
    iniciar()


if __name__ == "__main__":
    main()
