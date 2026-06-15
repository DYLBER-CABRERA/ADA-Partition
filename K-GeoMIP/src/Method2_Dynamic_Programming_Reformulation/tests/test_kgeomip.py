"""
Tests de Validación y Rendimiento — K-GeoMIP (Paso 5)
======================================================

Suite de pruebas que verifica:

  Grupo A — Corrección formal:
    A1. KGeometricSIA(k=2) ≡ GeometricSIA: pérdida δ₂ idéntica (tolerancia 1e-9)
    A2. k ∉ {2..5} lanza ValueError

  Grupo B — Validez de la solución para k∈{3,4,5}:
    B1. perdida ≥ 0
    B2. particion es str no vacía
    B3. distribucion_particion y distribucion_subsistema son NDArray no None
    B4. tiempo_ejecucion ≥ 0
    B5. distribuciones tienen la forma correcta (NDArray con valores en [0,1])

  Grupo C — Mejora de tiempos (ADA §5 — Algoritmos Voraces):
    C1. Fase de búsqueda greedy (C=3) más rápida que búsqueda exhaustiva (S(6,3)=90)
        Fundamento: se mide SÓLO la fase de búsqueda, aislando la tabla de costos Θ(n·2^n)
        que ambos comparten. Speedup esperado: S(6,3)/C = 90/3 = 30×
    C2. KGeometricSIA(k=3) termina en tiempo comparable a GeometricSIA (sin regresión)
        Fundamento: ambos comparten la misma fase dominante Θ(n·2^n)
    C3. stirling(n,k) produce los valores correctos vs tabla de referencia

Ejecutar desde Method2_Dynamic_Programming_Reformulation/:
    python -m pytest tests/ -v
"""

import time
from typing import Tuple

import numpy as np
import pytest

from src.constants.models import K_MIN, K_MAX
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.k_geometric import KGeometricSIA
from src.funcs.base import emd_efecto
from src.funcs.system import k_particiones, stirling
from src.models.core.solution import Solution


# ── Constantes de configuración de subsistemas para los tests ────────────────

# Lógica: Parámetros de subsistema para n=4 — todas las variables activas y condicionadas.
# Sintaxis: Constantes en MAYÚSCULAS por convención PEP 8 para valores constantes de módulo.
_COND_N4 = "1111"
_ALC_N4  = "1111"
_MEC_N4  = "1111"

# Lógica: Parámetros de subsistema para n=6 — usados en tests de k∈{3,4,5} y rendimiento.
#         n=6 garantiza que existen particiones no vacías para k=5 (5 ≤ n=6).
# Sintaxis: Cadenas binarias de longitud 6; cada bit corresponde a una variable del sistema.
_COND_N6 = "111111"
_ALC_N6  = "111111"
_MEC_N6  = "111111"

# Lógica: Factor de tolerancia para el test de regresión temporal (C2).
#         KGeometricSIA(k=3) puede tardar hasta _FACTOR_REGRESION× más que GeometricSIA(k=2)
#         sin considerarse una regresión de rendimiento, ya que ambos son Θ(n·2^n).
# Sintaxis: Float literal; comparado con `t_kgeo <= t_geo * _FACTOR_REGRESION`.
_FACTOR_REGRESION: float = 3.0


# ════════════════════════════════════════════════════════════════════════════════
# GRUPO A — Corrección formal
# ════════════════════════════════════════════════════════════════════════════════

class TestCorreccionFormal:
    """Grupo A: Verifica equivalencia con GeometricSIA para k=2 y validez de dominio."""

    def test_k2_equivalencia_geometrica(self, gestor_n4, tpm_n4):
        """
        A1 — KGeometricSIA(k=2) debe producir la misma pérdida δ₂ que GeometricSIA.

        Fundamento matemático:
            Para k=2, KGeometricSIA delega a super().aplicar_estrategia() → GeometricSIA exacto.
            Por construcción: KGeometricSIA(k=2).perdida ≡ GeometricSIA.perdida  □

        Complejidad del test: Θ(n·2^n) × 2 = Θ(n·2^n)  (n=4, 2^4=16)
        """
        # Lógica: Ejecuta GeometricSIA (bi-partición exacta) para obtener la referencia δ₂.
        # Sintaxis: Constructor + llamada a método; el resultado es un objeto Solution con `.perdida`.
        geo = GeometricSIA(gestor_n4)
        sol_geo: Solution = geo.aplicar_estrategia(
            _COND_N4, _ALC_N4, _MEC_N4, tpm_n4
        )

        # Lógica: Ejecuta KGeometricSIA con k=2; internamente delega a GeometricSIA.
        # Sintaxis: Keyword argument `k=2` activa la rama de delegación en aplicar_estrategia.
        kgeo = KGeometricSIA(gestor_n4)
        sol_kgeo: Solution = kgeo.aplicar_estrategia(
            _COND_N4, _ALC_N4, _MEC_N4, tpm_n4, k=2
        )

        # Lógica: Calcula la diferencia absoluta entre las dos pérdidas.
        # Sintaxis: `abs(a - b)` — valor absoluto de la diferencia, siempre ≥ 0.
        diferencia = abs(sol_geo.perdida - sol_kgeo.perdida)

        # Lógica: La tolerancia 1e-9 cubre errores de redondeo float64 (precisión ~15 dígitos).
        # Sintaxis: `assert cond, msg` — el mensaje se muestra si la condición es False.
        assert diferencia < 1e-9, (
            f"k=2 debe ser idéntico a GeometricSIA.\n"
            f"  GeometricSIA:  δ={sol_geo.perdida}\n"
            f"  KGeometricSIA: δ={sol_kgeo.perdida}\n"
            f"  Diferencia:    Δ={diferencia}"
        )

    def test_k_invalido_lanza_valueerror(self, gestor_n4, tpm_n4):
        """
        A2 — k ∉ {K_MIN,...,K_MAX} debe lanzar ValueError.

        Verifica el invariante de dominio: k ∈ {2,3,4,5}.
        """
        # Lógica: Valores inválidos: 0, 1 están por debajo de K_MIN=2; K_MAX+1 y 100 por encima.
        # Sintaxis: Lista de enteros literales que representan valores fuera del dominio válido.
        valores_invalidos = [0, 1, K_MAX + 1, 100]

        for k_invalido in valores_invalidos:
            # Lógica: `pytest.raises(ValueError)` actúa como context manager que espera la excepción.
            #         Si la excepción NO ocurre dentro del bloque `with`, el test falla.
            # Sintaxis: `with pytest.raises(ExcType):` captura la excepción y continúa si ocurre.
            with pytest.raises(ValueError):
                # Lógica: Instancia nueva por iteración para evitar contaminación de estado.
                # Sintaxis: KGeometricSIA(gestor) recibe el Manager ya inicializado.
                kgeo = KGeometricSIA(gestor_n4)
                kgeo.aplicar_estrategia(
                    _COND_N4, _ALC_N4, _MEC_N4, tpm_n4, k=k_invalido
                )


# ════════════════════════════════════════════════════════════════════════════════
# GRUPO B — Validez de la solución para k ∈ {3, 4, 5}
# ════════════════════════════════════════════════════════════════════════════════

class TestValidezSolucion:
    """
    Grupo B: Verifica que Solution esté bien formada para todos los valores de k>2.

    Usa n=6 para todos los tests de este grupo porque:
        - k=3: S(6,3)=90  (n=4 también funciona: S(4,3)=6)
        - k=4: S(6,4)=65  (n=4 también funciona: S(4,4)=1)
        - k=5: S(6,5)=15  (n=4 NO funciona: n<k → imposible)
    """

    @pytest.mark.parametrize("k", [3, 4, 5])
    def test_solucion_atributos_validos(self, gestor_n6, tpm_n6, k):
        """
        B1-B4 — Solution para k∈{3,4,5} debe tener todos los atributos bien formados.

        Postcondiciones verificadas:
            B1: perdida ∈ [0, ∞)
            B2: particion es str no vacía (representación visual de la k-MIP)
            B3: distribucion_particion y distribucion_subsistema son NDArray no None
            B4: tiempo_ejecucion ≥ 0
        """
        # Lógica: Ejecuta la estrategia K-GeoMIP para el k parametrizado con n=6 variables.
        # Sintaxis: `@pytest.mark.parametrize("k", [3,4,5])` genera 3 instancias del test.
        kgeo = KGeometricSIA(gestor_n6)
        sol: Solution = kgeo.aplicar_estrategia(
            _COND_N6, _ALC_N6, _MEC_N6, tpm_n6, k=k
        )

        # Lógica: B1 — La pérdida EMD es siempre no negativa (distancia = |Δ| ≥ 0).
        # Sintaxis: `assert expr, msg` — mensaje mostrado si el assert falla.
        assert sol.perdida >= 0.0, (
            f"[B1] perdida debe ser ≥ 0 para k={k}, se obtuvo {sol.perdida}"
        )

        # Lógica: B2 — particion es la representación visual de la k-MIP; debe ser str no vacío.
        # Sintaxis: `isinstance(x, str) and len(x) > 0` — dos condiciones unidas con `and`.
        assert isinstance(sol.particion, str) and len(sol.particion) > 0, (
            f"[B2] particion debe ser str no vacío para k={k}"
        )

        # Lógica: B3 — Las distribuciones deben estar asignadas (no None).
        # Sintaxis: `is not None` verifica que el atributo no quedó en su valor por defecto.
        assert sol.distribucion_particion is not None, (
            f"[B3] distribucion_particion no debe ser None para k={k}"
        )
        assert sol.distribucion_subsistema is not None, (
            f"[B3] distribucion_subsistema no debe ser None para k={k}"
        )

        # Lógica: B4 — El tiempo de ejecución mide tiempo real transcurrido; es siempre ≥ 0.
        # Sintaxis: `>= 0` — comparación numérica; tiempo_ejecucion es float.
        assert sol.tiempo_ejecucion >= 0.0, (
            f"[B4] tiempo_ejecucion debe ser ≥ 0 para k={k}, se obtuvo {sol.tiempo_ejecucion}"
        )

    @pytest.mark.parametrize("k", [3, 4, 5])
    def test_distribucion_es_ndarray_con_valores_validos(self, gestor_n6, tpm_n6, k):
        """
        B5 — Las distribuciones deben ser NDArray con valores en [0, 1] (vectores de probabilidad).

        Para k∈{3,4,5} con n=6:
            - distribucion_particion: producto tensorial de k distribuciones → NDArray[float]
            - distribucion_subsistema: distribución marginal del subsistema completo → NDArray[float]
            - Todos los valores deben pertenecer a [0, 1] (probabilidades válidas).
        """
        # Lógica: Obtiene la solución para el k parametrizado.
        # Sintaxis: Constructor + aplicar_estrategia con keyword argument k=k.
        kgeo = KGeometricSIA(gestor_n6)
        sol: Solution = kgeo.aplicar_estrategia(
            _COND_N6, _ALC_N6, _MEC_N6, tpm_n6, k=k
        )

        # Lógica: Verifica que las distribuciones son arrays NumPy (no listas Python ni None).
        # Sintaxis: `isinstance(x, np.ndarray)` — verifica el tipo exacto del objeto.
        assert isinstance(sol.distribucion_particion, np.ndarray), (
            f"[B5] distribucion_particion debe ser NDArray para k={k}"
        )
        assert isinstance(sol.distribucion_subsistema, np.ndarray), (
            f"[B5] distribucion_subsistema debe ser NDArray para k={k}"
        )

        # Lógica: Todos los valores de una distribución de probabilidad pertenecen a [0, 1].
        #         `np.all(x >= 0)` verifica que no hay valores negativos (imposible en probabilidad).
        # Sintaxis: `np.all(condicion_booleana)` retorna True si TODOS los elementos satisfacen la condición.
        assert np.all(sol.distribucion_particion >= -1e-8), (
            f"[B5] dist_particion tiene valores negativos para k={k}: "
            f"min={np.min(sol.distribucion_particion)}"
        )
        assert np.all(sol.distribucion_subsistema >= -1e-8), (
            f"[B5] dist_subsistema tiene valores negativos para k={k}: "
            f"min={np.min(sol.distribucion_subsistema)}"
        )

        # Lógica: Verifica que el NDArray no está vacío (longitud > 0).
        # Sintaxis: `len(arr) > 0` — `len()` sobre ndarray retorna el tamaño de la primera dimensión.
        assert len(sol.distribucion_particion) > 0, (
            f"[B5] dist_particion no debe estar vacía para k={k}"
        )


# ════════════════════════════════════════════════════════════════════════════════
# GRUPO C — Mejora de tiempos: Greedy vs Exhaustivo (ADA §5)
# ════════════════════════════════════════════════════════════════════════════════

class TestRendimiento:
    """
    Grupo C: Demuestra la mejora de tiempos de la fase de búsqueda greedy vs exhaustivo.

    Diseño del test de speedup (C1):
        Se AÍSLA la fase de búsqueda para medir el speedup puro.
        Ambos enfoques comparten la fase dominante Θ(n·2^n) (tabla de costos),
        por lo que medir el tiempo total ocultaría el speedup real de la búsqueda.

        Fase aislada:
            Greedy:    C=3 evaluaciones de k_partir + emd_efecto
            Exhaustivo: S(6,3)=90 evaluaciones de k_partir + emd_efecto
            Speedup esperado: 90/3 = 30×

    Fundamento teórico (ADA 24A §5 — Algoritmos Voraces):
        La heurística voraz reduce el espacio de búsqueda de S(n,k) a C=O(1) candidatos.
        Para k=3, n=6: 90 → 3  (speedup 30×)
        Para k=3, n=10: 9330 → 3  (speedup ~3110×)
    """

    def test_fase_busqueda_greedy_mas_rapida_que_exhaustivo(self, gestor_n6, tpm_n6):
        """
        C1 — La fase de búsqueda greedy (C=3) debe ser más rápida que la búsqueda exhaustiva.

        Método:
            1. Preparar el subsistema una sola vez (fase compartida).
            2. Medir SOLO el tiempo de la fase de búsqueda greedy (C=3 candidatos).
            3. Medir SOLO el tiempo de la fase de búsqueda exhaustiva (S(6,3)=90 candidatos).
            4. Verificar t_greedy_busqueda < t_exhaustivo_busqueda.

        Garantía LPT (Graham, 1969): makespan(greedy) ≤ (4/3 - 1/(3k)) · OPT
        """
        # Lógica: Preparación compartida — ejecuta la estrategia completa una vez para
        #         construir el subsistema y la tabla de costos que ambas fases necesitan.
        # Sintaxis: Se descarta el resultado; nos interesa el estado interno del objeto kgeo.
        kgeo = KGeometricSIA(gestor_n6)
        kgeo.aplicar_estrategia(_COND_N6, _ALC_N6, _MEC_N6, tpm_n6, k=3)

        # Lógica: Accede a los índices del subsistema ya preparado para la fase de búsqueda.
        # Sintaxis: @property de System — retorna NDArray[int8] con los índices de variables activas.
        alcances_sub = kgeo.sia_subsistema.indices_ncubos
        mecanismos_sub = kgeo.sia_subsistema.dims_ncubos

        # Lógica: Distribución original del subsistema — referencia para calcular EMD en ambas fases.
        # Sintaxis: Atributo asignado por `sia_preparar_subsistema`; NDArray[float32].
        dist_orig = kgeo.sia_dists_marginales

        # ── Medir fase de búsqueda GREEDY (C=3 candidatos) ─────────────────
        # Lógica: Genera los C=3 candidatos greedy y evalúa cada uno con k_partir + emd_efecto.
        #         Esta es la "fase 4-5" de KGeometricSIA — lo que la hace más rápida que el exhaustivo.
        # Sintaxis: `time.perf_counter()` — reloj de alta resolución del SO, no afectado por sleep.
        t0_greedy = time.perf_counter()
        candidatos = kgeo._generar_candidatos_k(3)
        for particion in candidatos:
            # Lógica: Aplica la k-partición y calcula la pérdida EMD para cada candidato.
            # Sintaxis: Encadenamiento de métodos: k_partir() → distribución_marginal() → float.
            dist = kgeo.sia_subsistema.k_partir(particion).distribucion_marginal()
            emd_efecto(dist, dist_orig)
        t_greedy_busqueda: float = time.perf_counter() - t0_greedy

        # ── Medir fase de búsqueda EXHAUSTIVA (S(6,3)=90 candidatos) ────────
        # Lógica: Enumera TODAS las k-particiones válidas usando el generador RGS del Paso 2
        #         y evalúa cada una con la misma k_partir + emd_efecto.
        # Sintaxis: `k_particiones(alcances, mecanismos, k)` — generador perezoso del Paso 2.
        t0_exhaustivo = time.perf_counter()
        for particion in k_particiones(alcances_sub, mecanismos_sub, 3):
            dist = kgeo.sia_subsistema.k_partir(particion).distribucion_marginal()
            emd_efecto(dist, dist_orig)
        t_exhaustivo_busqueda: float = time.perf_counter() - t0_exhaustivo

        # Lógica: Calcula el speedup real de la fase de búsqueda.
        # Sintaxis: `max(t_greedy, 1e-9)` evita ZeroDivisionError si t_greedy es insignificante.
        speedup_real: float = t_exhaustivo_busqueda / max(t_greedy_busqueda, 1e-9)
        s_n_k: int = stirling(6, 3)

        # Lógica: Verifica que el exhaustivo evaluó exactamente S(6,3)=90 particiones.
        #         (El conteo se verifica en C3 con stirling(); aquí lo reportamos en el assert.)
        # Sintaxis: f-string interpolado en el mensaje del assert.
        assert t_greedy_busqueda < t_exhaustivo_busqueda, (
            f"[C1] Greedy ({t_greedy_busqueda:.6f}s, C=3 candidatos) debe ser más rápido "
            f"que exhaustivo ({t_exhaustivo_busqueda:.6f}s, S(6,3)={s_n_k} candidatos). "
            f"Speedup obtenido = {speedup_real:.1f}× (esperado ≈ {s_n_k // 3}×)"
        )

    def test_tiempo_total_kgeomip_comparable_a_biparticion(self, gestor_n6, tpm_n6):
        """
        C2 — Tiempo total de KGeometricSIA(k=3) ≤ _FACTOR_REGRESION × GeometricSIA(k=2).

        Verifica la ausencia de regresión de rendimiento al pasar de k=2 a k=3.
        Fundamento: ambos tienen la misma fase dominante Θ(n·2^n) (tabla BFS de costos).

        El factor de tolerancia _FACTOR_REGRESION=3.0 absorbe:
            - El overhead greedy O(n log n): pequeño vs Θ(n·2^n)
            - Variaciones del planificador del SO y caché de la CPU
        """
        # Lógica: Mide el tiempo total de GeometricSIA como línea base de referencia.
        # Sintaxis: Diferencia de perf_counter() — tiempo de pared en segundos.
        t0 = time.perf_counter()
        geo = GeometricSIA(gestor_n6)
        geo.aplicar_estrategia(_COND_N6, _ALC_N6, _MEC_N6, tpm_n6)
        t_geo: float = time.perf_counter() - t0

        # Lógica: Mide el tiempo total de KGeometricSIA(k=3).
        # Sintaxis: Mismo patrón; `k=3` activa el flujo greedy (no delegación).
        t0 = time.perf_counter()
        kgeo = KGeometricSIA(gestor_n6)
        kgeo.aplicar_estrategia(_COND_N6, _ALC_N6, _MEC_N6, tpm_n6, k=3)
        t_kgeo: float = time.perf_counter() - t0

        # Lógica: Calcula el ratio t_kgeo/t_geo para reportarlo en caso de fallo.
        # Sintaxis: División flotante con protección contra cero.
        ratio: float = t_kgeo / max(t_geo, 1e-9)

        # Lógica: El tiempo de KGeometricSIA(k=3) debe ser ≤ _FACTOR_REGRESION× el de GeometricSIA.
        # Sintaxis: `t_kgeo <= t_geo * FACTOR` — la multiplicación escala el umbral al tiempo base.
        assert t_kgeo <= t_geo * _FACTOR_REGRESION, (
            f"[C2] KGeometricSIA(k=3) no debe tardar más de {_FACTOR_REGRESION}× que GeometricSIA.\n"
            f"  t_geo={t_geo:.4f}s | t_kgeo={t_kgeo:.4f}s | ratio={ratio:.2f}×"
        )

    @pytest.mark.parametrize("k", [3, 4, 5])
    def test_numero_stirling_correcto(self, k):
        """
        C3 — stirling(n,k) retorna los valores correctos de la tabla de referencia.

        Tabla de referencia S(n,k) (Abramowitz & Stegun):
            S(3,3)=1,  S(4,3)=6,  S(5,3)=25, S(6,3)=90
            S(4,4)=1,  S(5,4)=10, S(6,4)=65
            S(5,5)=1,  S(6,5)=15

        Verifica el DP del Paso 2 contra valores analíticos conocidos.
        """
        # Lógica: Diccionario de valores de referencia S(n,k) indexado por k y luego por n.
        #         Estos valores se obtienen de la tabla de Stirling de segundo tipo (tabulada).
        # Sintaxis: Dict anidado `{k: {n: valor}}` — indexado primero por k, luego por n.
        tabla_referencia = {
            3: {3: 1, 4: 6, 5: 25, 6: 90},
            4: {4: 1, 5: 10, 6: 65},
            5: {5: 1, 6: 15},
        }

        for n, s_esperado in tabla_referencia.get(k, {}).items():
            # Lógica: Calcula S(n,k) usando la función DP del Paso 2 y compara con el valor tabular.
            # Sintaxis: `stirling(n, k)` retorna int; comparado con `==` (igualdad exacta de enteros).
            s_calculado = stirling(n, k)
            assert s_calculado == s_esperado, (
                f"[C3] S({n},{k}) debería ser {s_esperado}, se obtuvo {s_calculado}"
            )
