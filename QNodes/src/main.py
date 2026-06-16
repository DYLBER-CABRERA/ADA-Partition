import re
from pathlib import Path
from src.controllers.manager import Manager
from src.models.base.application import aplicacion
from src.strategies.q_nodes import QNodes
from src.strategies.KQNodes import KQNodes
from src.funcs.iit import ABECEDARY


def letras_a_bits(letras: str, n_nodos: int) -> str:
    """
    Convierte una cadena de letras como 'ABCDEFGHI' a bits como '1111111110'
    donde cada posición indica si ese nodo está presente (1) o ausente (0).
    """
    letras_set = set(letras.upper())
    return "".join(
        "1" if ABECEDARY[i] in letras_set else "0"
        for i in range(n_nodos)
    )


def iniciar(nombre_red="N10A", usar_kqnodes=False, k=3,
            alcance=None, mecanismo=None, estado_inicio=None):
    """Punto de entrada dinámico automatizado"""

    match = re.match(r"N(\d+)([A-Z])", nombre_red)
    if not match:
        print(f"❌ Error: Formato '{nombre_red}' inválido. Usa 'N10A', 'N15B', etc.")
        return

    n_nodos = int(match.group(1))
    pagina = match.group(2)

    aplicacion.set_pagina_red_muestra(pagina)

    # Estado inicial
    if estado_inicio is None:
        if n_nodos >= 15:
            estado_inicial = "00001" + "0" * (n_nodos - 5)
        else:
            estado_inicial = "1" + "0" * (n_nodos - 1)
    else:
        estado_inicial = estado_inicio

    condiciones = "1" * n_nodos

    # Convertir alcance y mecanismo de letras a bits si es necesario
    if alcance is None:
        alcance_bits = "1" * n_nodos
    elif set(alcance.upper()) <= set("01"):
        # Ya viene en formato de bits
        alcance_bits = alcance
    else:
        # Viene en formato de letras, convertir
        alcance_bits = letras_a_bits(alcance, n_nodos)

    if mecanismo is None:
        mecanismo_bits = "1" * n_nodos
    elif set(mecanismo.upper()) <= set("01"):
        # Ya viene en formato de bits
        mecanismo_bits = mecanismo
    else:
        # Viene en formato de letras, convertir
        mecanismo_bits = letras_a_bits(mecanismo, n_nodos)

    print(f"\n{'='*50}")
    print(f"🚀 PROCESANDO: {nombre_red}")
    print(f"📊 Config: {n_nodos} nodos, página {pagina}")
    print(f"⚙️  ESTRATEGIA: {'KQNodes' if usar_kqnodes else 'QNodes'}")
    if usar_kqnodes:
        print(f"🔢 k={k}")
    print(f"{'='*50}\n")

    gestor_redes = Manager(estado_inicial)
    mpt = gestor_redes.cargar_red()

    if k == 2:
        print(f"⚙️  ESTRATEGIA: QNodes (Bipartición original)")
        analizador = QNodes(mpt)
        sia_cero = analizador.aplicar_estrategia(
            estado_inicial,
            condiciones,
            alcance_bits,
            mecanismo_bits,
        )
    else:
        print(f"⚙️  ESTRATEGIA: KQNodes (k={k})")
        analizador = KQNodes(mpt)
        sia_cero = analizador.aplicar_estrategia(
            estado_inicial,
            condiciones,
            alcance_bits,
            mecanismo_bits,
            k=k,
        )

    print(sia_cero)

    nombre_archivo = "resultados_kqnodes.txt" if usar_kqnodes else "resultados_qnodes.txt"
    ruta_resultados = Path(f"results/{nombre_archivo}")
    ruta_resultados.parent.mkdir(exist_ok=True)

    with open(ruta_resultados, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"RED: {nombre_red}\n")
        f.write(f"ESTRATEGIA: {'KQNodes (k=' + str(k) + ')' if usar_kqnodes else 'QNodes (Bipartición)'}\n")
        f.write(f"PERDIDA (Phi): {sia_cero.perdida:.6f}\n")
        f.write(f"TIEMPO: {sia_cero.tiempo_ejecucion:.4f} seg\n")
        f.write(f"PARTICION:\n{sia_cero.particion}\n")
        f.write(f"{'='*50}\n")

    print(f"✅ Resultado guardado en: {ruta_resultados}")


def run_prueba(alcance, mecanismo, k, estado_inicio, variante):
    """
    Función puente para que el script de pruebas de compañeros pueda ejecutar
    la lógica de este main sin modificaciones externas.
    """
    n_nodos = len(estado_inicio)
    nombre_red = f"N{n_nodos}{variante}"

    iniciar(
        nombre_red=nombre_red,
        usar_kqnodes=True,
        k=k,
        alcance=alcance,
        mecanismo=mecanismo,
        estado_inicio=estado_inicio,
    )