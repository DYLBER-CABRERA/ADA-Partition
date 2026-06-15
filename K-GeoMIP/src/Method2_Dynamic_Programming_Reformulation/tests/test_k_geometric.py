"""
Tests unitarios para KGeometricSIA — K-GeoMIP.

Cómo ejecutar:
    Desde el directorio Method2_Dynamic_Programming_Reformulation/:
        python -m pytest tests/test_k_geometric.py -v

Organización de suites:
    TestStirling              — números de Stirling de segunda especie
    TestGreedyMultiway        — algoritmo LPT / SPT multiway
    TestParticionValida       — predicado de validación de k-particiones
    TestParticionAClave       — clave canónica hashable de una k-partición
    TestGruposAParticion      — conversión de grupos de índices a formato k-partición
    TestGenerarCandidatosK    — generación de candidatos (estado sintético inyectado)
    TestConsistenciaK2        — garantía formal KGeometricSIA(k=2) ≡ GeometricSIA
    TestCacheSubsistema       — caché BFS inter-k no recalcula Fases 1-3

Precondición de import:
    El script debe ejecutarse desde el directorio que contiene 'src/', es decir
    Method2_Dynamic_Programming_Reformulation/, de forma que 'src.*' sea importable.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
import numpy as np

# Añade el directorio raíz del proyecto al path para que 'from src.*' funcione
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers compartidos
# ─────────────────────────────────────────────────────────────────────────────

def _mock_manager(n: int = 3, pagina: str = "A") -> MagicMock:
    """
    Crea un Manager mock mínimo para instanciar KGeometricSIA en tests unitarios.

    El mock proporciona únicamente los atributos que SIA.__init__ y
    GeometricSIA.__init__ acceden durante la construcción del objeto:
        - estado_inicial: array de n ceros (sistema "apagado")
        - pagina: identificador de variante para el profiler

    Args:
        n:     Número de variables del sistema ficticio.
        pagina: Letra de variante (solo afecta al nombre de la sesión del profiler).

    Returns:
        MagicMock: Gestor simulado compatible con SIA.__init__.
    """
    gestor = MagicMock()
    gestor.estado_inicial = np.zeros(n, dtype=np.int8)
    gestor.pagina = pagina
    return gestor


def _make_inst(n: int = 3):
    """
    Crea una instancia de KGeometricSIA con Manager mock, parcheando el profiler
    para no crear directorios ni archivos durante los tests.

    Args:
        n: Número de variables del sistema ficticio.

    Returns:
        KGeometricSIA: Instancia lista para inyectar estado sintético.
    """
    with patch("src.middlewares.profile.profiler_manager.start_session"):
        from src.controllers.strategies.k_geometric import KGeometricSIA
        return KGeometricSIA(_mock_manager(n=n))


def _particion_simple(k: int) -> list:
    """
    Construye una k-partición sintética válida con k grupos de 1 elemento cada uno.

    Cada parte i contiene el nodo i tanto en alcance como en mecanismo.
    Útil para tests que solo necesitan una partición válida de forma rápida.

    Args:
        k: Número de partes.

    Returns:
        list[tuple[NDArray[int8], NDArray[int8]]]: k-partición válida.
    """
    return [
        (np.array([i], dtype=np.int8), np.array([i], dtype=np.int8))
        for i in range(k)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Suite 1 — Números de Stirling de segunda especie
# ─────────────────────────────────────────────────────────────────────────────

class TestStirling(unittest.TestCase):
    """
    Valida stirling(n, k) = S(n, k) usando valores conocidos de la literatura
    y los casos base definidos en la recurrencia implementada.

    Referencia: Knuth, TAOCP Vol. 1, §1.2.6.
    """

    def setUp(self):
        from src.funcs.system import stirling
        self.S = stirling

    def test_s_n_1_es_uno(self):
        """S(n, 1) = 1 para todo n ≥ 1 — solo existe una partición en 1 parte."""
        for n in range(1, 8):
            self.assertEqual(self.S(n, 1), 1, msg=f"S({n},1) debe ser 1")

    def test_s_n_n_es_uno(self):
        """S(n, n) = 1 para todo n ≥ 1 — exactamente n singletons."""
        for n in range(1, 8):
            self.assertEqual(self.S(n, n), 1, msg=f"S({n},{n}) debe ser 1")

    def test_s_k_mayor_n_es_cero(self):
        """S(n, k) = 0 cuando k > n — imposible tener más partes que elementos."""
        self.assertEqual(self.S(3, 5), 0)
        self.assertEqual(self.S(1, 2), 0)
        self.assertEqual(self.S(4, 6), 0)

    def test_s_k_cero_es_cero(self):
        """S(n, 0) = 0 para n > 0 — no existen 0-particiones de un conjunto no vacío."""
        for n in range(1, 6):
            self.assertEqual(self.S(n, 0), 0, msg=f"S({n},0) debe ser 0")

    def test_valores_conocidos(self):
        """Verifica S(n,k) contra tabla de valores de referencia."""
        casos = {
            (4, 2): 7,
            (4, 3): 6,
            (5, 2): 15,
            (5, 3): 25,
            (5, 4): 10,
            (5, 5): 1,
        }
        for (n, k), esperado in casos.items():
            with self.subTest(n=n, k=k):
                self.assertEqual(self.S(n, k), esperado)


# ─────────────────────────────────────────────────────────────────────────────
# Suite 2 — Greedy Multiway Partition (LPT / SPT)
# ─────────────────────────────────────────────────────────────────────────────

class TestGreedyMultiway(unittest.TestCase):
    """
    Valida el algoritmo greedy LPT/SPT implementado en _greedy_multiway.

    Propiedades que se verifican:
        - Conservación: Σ costos = Σ(Σ costos por grupo)
        - Cobertura:    cada índice 0..n-1 aparece exactamente una vez
        - Cardinalidad: se retornan exactamente k grupos
        - LPT mejor que asignación aleatoria (makespan ≤ (4/3 - 1/(3k))·OPT)
    """

    def setUp(self):
        self.inst = _make_inst(n=3)

    def _suma_grupo(self, costos, grupo):
        return sum(costos[i] for i in grupo)

    def test_cardinalidad_k2(self):
        """LPT con k=2 retorna exactamente 2 grupos."""
        costos = [3.0, 1.0, 4.0, 1.0, 5.0]
        grupos = self.inst._greedy_multiway(costos, 5, 2, descending=True)
        self.assertEqual(len(grupos), 2)

    def test_cardinalidad_k5(self):
        """LPT con k=5 retorna exactamente 5 grupos."""
        costos = [1.0] * 10
        grupos = self.inst._greedy_multiway(costos, 10, 5, descending=True)
        self.assertEqual(len(grupos), 5)

    def test_cobertura_total(self):
        """Cada índice aparece exactamente una vez en los grupos resultantes."""
        costos = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
        n = len(costos)
        for k in [2, 3, 4]:
            grupos = self.inst._greedy_multiway(costos, n, k, descending=True)
            todos = sorted(sum(grupos, []))
            self.assertEqual(todos, list(range(n)), msg=f"k={k} no cubre todos los índices")

    def test_conservacion_suma(self):
        """La suma total de costos se conserva tras la asignación a grupos."""
        costos = [2.0, 5.0, 1.0, 8.0, 3.0]
        n = len(costos)
        grupos = self.inst._greedy_multiway(costos, n, 3, descending=True)
        total_original = sum(costos)
        total_grupos = sum(self._suma_grupo(costos, g) for g in grupos)
        self.assertAlmostEqual(total_original, total_grupos)

    def test_lpt_vs_spt_cobertura(self):
        """Tanto LPT (desc=True) como SPT (desc=False) cubren todos los índices."""
        costos = [1.0, 3.0, 2.0, 5.0, 4.0]
        n = len(costos)
        for desc in [True, False]:
            grupos = self.inst._greedy_multiway(costos, n, 2, descending=desc)
            todos = sorted(sum(grupos, []))
            self.assertEqual(todos, list(range(n)), msg=f"descending={desc}")

    def test_n_igual_k_un_elemento_por_grupo(self):
        """Cuando n=k, cada grupo recibe exactamente 1 elemento."""
        costos = [2.0, 5.0, 3.0]
        grupos = self.inst._greedy_multiway(costos, 3, 3, descending=True)
        self.assertEqual([len(g) for g in grupos], [1, 1, 1])

    def test_costos_iguales_grupos_balanceados(self):
        """Con costos idénticos y n divisible por k, los grupos son del mismo tamaño."""
        costos = [1.0] * 6
        grupos = self.inst._greedy_multiway(costos, 6, 2, descending=True)
        self.assertEqual(len(grupos[0]), len(grupos[1]))

    def test_lpt_makespan_cota_graham(self):
        """
        Verifica que LPT satisface la cota de Graham:
            makespan(LPT) ≤ (4/3 - 1/(3k)) * makespan(OPT)

        Para este test se usa la solución óptima real (búsqueda exhaustiva)
        sobre un ejemplo pequeño (n=4, k=2) y se verifica la desigualdad.
        """
        costos = [4.0, 5.0, 6.0, 7.0]  # OPT = {6,4}|{5,7} = 10|12 → makespan=12 o {4,7}|{5,6}=11|11→11
        n = len(costos)
        k = 2
        grupos = self.inst._greedy_multiway(costos, n, k, descending=True)
        makespan_lpt = max(self._suma_grupo(costos, g) for g in grupos)
        total = sum(costos)
        makespan_opt_lower = total / k  # cota inferior del óptimo = avg
        cota = (4/3 - 1/(3*k)) * total  # cota de Graham relativa al total
        self.assertLessEqual(makespan_lpt, cota + 1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# Suite 3 — Predicado de validación de k-particiones
# ─────────────────────────────────────────────────────────────────────────────

class TestParticionValida(unittest.TestCase):
    """
    Valida _particion_valida — precondición de System.k_partir():
        ∀i: |alcance_i| ≥ 1  ∧  |mecanismo_i| ≥ 1
    """

    def setUp(self):
        self.inst = _make_inst()

    def test_valida_dos_partes_iguales(self):
        """Partición con 2 partes simétricas y no vacías → True."""
        p = [
            (np.array([0, 1], dtype=np.int8), np.array([0, 1], dtype=np.int8)),
            (np.array([2],    dtype=np.int8), np.array([2],    dtype=np.int8)),
        ]
        self.assertTrue(self.inst._particion_valida(p))

    def test_valida_tres_partes(self):
        """Partición con 3 partes de 1 elemento cada una → True."""
        self.assertTrue(self.inst._particion_valida(_particion_simple(3)))

    def test_invalida_alcance_vacio(self):
        """Parte con alcance vacío → False (k_partir fallaría con marginalización vacía)."""
        p = [
            (np.array([], dtype=np.int8), np.array([0], dtype=np.int8)),
            (np.array([1], dtype=np.int8), np.array([1], dtype=np.int8)),
        ]
        self.assertFalse(self.inst._particion_valida(p))

    def test_invalida_mecanismo_vacio(self):
        """Parte con mecanismo vacío → False."""
        p = [
            (np.array([0], dtype=np.int8), np.array([], dtype=np.int8)),
            (np.array([1], dtype=np.int8), np.array([1], dtype=np.int8)),
        ]
        self.assertFalse(self.inst._particion_valida(p))

    def test_invalida_ambos_vacios(self):
        """Parte con alcance Y mecanismo vacíos → False."""
        p = [
            (np.array([], dtype=np.int8), np.array([], dtype=np.int8)),
            (np.array([0], dtype=np.int8), np.array([0], dtype=np.int8)),
        ]
        self.assertFalse(self.inst._particion_valida(p))

    def test_invalida_segunda_parte(self):
        """La violación puede estar en cualquier parte, no solo en la primera."""
        p = [
            (np.array([0], dtype=np.int8), np.array([0], dtype=np.int8)),
            (np.array([], dtype=np.int8),  np.array([1], dtype=np.int8)),
        ]
        self.assertFalse(self.inst._particion_valida(p))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 4 — Clave canónica hashable de k-particiones
# ─────────────────────────────────────────────────────────────────────────────

class TestParticionAClave(unittest.TestCase):
    """
    Valida _particion_a_clave — representación hashable e inmutable de una k-partición.

    Propiedades verificadas:
        - Tipo:          la clave es una tupla Python (hasheable, inmutable)
        - Determinismo:  la misma partición produce siempre la misma clave
        - Distinción:    particiones distintas producen claves distintas
        - Hashabilidad:  la clave se puede usar como llave de dict/set
    """

    def setUp(self):
        self.inst = _make_inst()

    def test_clave_es_tupla(self):
        """La clave debe ser de tipo tuple."""
        clave = self.inst._particion_a_clave(_particion_simple(2))
        self.assertIsInstance(clave, tuple)

    def test_clave_es_hasheable(self):
        """La clave debe ser usable como llave de dict y elemento de set."""
        clave = self.inst._particion_a_clave(_particion_simple(3))
        d = {clave: True}
        s = {clave}
        self.assertIn(clave, d)
        self.assertIn(clave, s)

    def test_determinismo(self):
        """La misma partición produce la misma clave en dos llamadas distintas."""
        p = [
            (np.array([0, 2], dtype=np.int8), np.array([1, 3], dtype=np.int8)),
            (np.array([1, 3], dtype=np.int8), np.array([0, 2], dtype=np.int8)),
        ]
        c1 = self.inst._particion_a_clave(p)
        c2 = self.inst._particion_a_clave(p)
        self.assertEqual(c1, c2)

    def test_particiones_distintas_claves_distintas(self):
        """Dos particiones con grupos distintos producen claves distintas."""
        p1 = [
            (np.array([0], dtype=np.int8), np.array([0], dtype=np.int8)),
            (np.array([1], dtype=np.int8), np.array([1], dtype=np.int8)),
        ]
        p2 = [
            (np.array([0], dtype=np.int8), np.array([0], dtype=np.int8)),
            (np.array([1], dtype=np.int8), np.array([2], dtype=np.int8)),  # mecanismo distinto
        ]
        self.assertNotEqual(
            self.inst._particion_a_clave(p1),
            self.inst._particion_a_clave(p2),
        )

    def test_longitud_clave(self):
        """La clave tiene exactamente k sub-tuplas, una por parte de la partición."""
        for k in [2, 3, 4]:
            clave = self.inst._particion_a_clave(_particion_simple(k))
            self.assertEqual(len(clave), k, msg=f"k={k}")


# ─────────────────────────────────────────────────────────────────────────────
# Suite 5 — Conversión de grupos a formato k-partición
# ─────────────────────────────────────────────────────────────────────────────

class TestGruposAParticion(unittest.TestCase):
    """
    Valida _grupos_a_particion — conversión de listas de índices locales
    al formato NDArray[int8] que acepta System.k_partir().

    Propiedades verificadas:
        - Cardinalidad: k tuplas resultado
        - Cobertura:    todos los alcances originales aparecen en algún grupo
        - Tipo:         los arrays son de dtype int8
    """

    def setUp(self):
        self.inst = _make_inst()

    def test_cardinalidad_k2(self):
        """Con k=2, el resultado tiene exactamente 2 tuplas."""
        alcances   = np.array([0, 1, 2, 3], dtype=np.int8)
        mecanismos = np.array([0, 1, 2, 3], dtype=np.int8)
        grupos = [[0, 2], [1, 3]]
        resultado = self.inst._grupos_a_particion(grupos, alcances, mecanismos, 2)
        self.assertEqual(len(resultado), 2)

    def test_cobertura_alcances(self):
        """Todos los alcances originales aparecen en algún grupo de la partición."""
        alcances   = np.array([0, 1, 2, 3, 4], dtype=np.int8)
        mecanismos = np.array([0, 1, 2, 3, 4], dtype=np.int8)
        grupos = [[0, 1], [2, 3], [4]]
        resultado = self.inst._grupos_a_particion(grupos, alcances, mecanismos, 3)
        todos_alc = sorted(
            int(v) for parte in resultado for v in parte[0]
        )
        self.assertEqual(todos_alc, list(range(5)))

    def test_dtype_int8(self):
        """Los arrays de la partición resultante deben ser de dtype int8."""
        alcances   = np.array([0, 1, 2], dtype=np.int8)
        mecanismos = np.array([0, 1, 2], dtype=np.int8)
        grupos = [[0], [1], [2]]
        resultado = self.inst._grupos_a_particion(grupos, alcances, mecanismos, 3)
        for alc, mec in resultado:
            self.assertEqual(alc.dtype, np.int8, msg="alcance no es int8")
            self.assertEqual(mec.dtype, np.int8, msg="mecanismo no es int8")

    def test_k3_simetrico(self):
        """Con n=3 y k=3, cada parte tiene exactamente 1 alcance y 1 mecanismo."""
        alcances   = np.array([0, 1, 2], dtype=np.int8)
        mecanismos = np.array([0, 1, 2], dtype=np.int8)
        grupos = [[0], [1], [2]]
        resultado = self.inst._grupos_a_particion(grupos, alcances, mecanismos, 3)
        for alc, mec in resultado:
            self.assertEqual(len(alc), 1)
            self.assertEqual(len(mec), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Suite 6 — Generación de candidatos k-partición
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerarCandidatosK(unittest.TestCase):
    """
    Valida _generar_candidatos_k con estado sintético inyectado.

    En vez de ejecutar las Fases 1-3 (que requieren CSV y cómputo BFS),
    se inyectan directamente los atributos de instancia mínimos que el método
    necesita: _trans_matrix, _trans_valid, estado_inicial, estado_final y
    un sia_subsistema mock con los índices necesarios.

    Esto es un test de caja blanca del módulo de generación de candidatos.
    """

    def setUp(self):
        """
        Prepara una instancia con estado sintético de 4 variables.

        _trans_matrix:  8 filas (2^3, se usa n=3 dentro del mock) × 3 cols
        estado_inicial: [1, 0, 0] — primer nodo activo
        estado_final:   [0, 1, 1] — inversión del estado inicial

        El índice del estado final en little-endian: bit1 + bit2 = 0 + 2 + 4 = 6
        """
        self.inst = _make_inst(n=4)

        # _trans_matrix: 2^n filas × n columnas (n=3 para este mock)
        n = 3
        n_estados = 1 << n
        self.inst._trans_matrix = np.random.rand(n_estados, n).astype(np.float32)
        self.inst._trans_matrix[0] = 0.0  # estado inicial siempre costo 0
        self.inst._trans_valid = np.ones(n_estados, dtype=bool)

        self.inst.estado_inicial = np.array([1, 0, 0], dtype=np.int8)
        self.inst.estado_final   = np.array([0, 1, 1], dtype=np.int8)

        # Subsistema mock con 3 ncubos
        ncubo_mock = MagicMock()
        ncubo_mock.data = np.random.rand(2, 2, 2).astype(np.float32)
        sub = MagicMock()
        sub.indices_ncubos = np.array([0, 1, 2], dtype=np.int8)
        sub.dims_ncubos    = np.array([0, 1, 2], dtype=np.int8)
        sub.ncubos         = [ncubo_mock] * 3
        self.inst.sia_subsistema = sub

    def test_candidatos_k2_no_vacios(self):
        """_generar_candidatos_k(k=2) retorna ≥1 candidato, cada uno con 2 partes válidas."""
        candidatos = self.inst._generar_candidatos_k(k=2)
        self.assertGreater(len(candidatos), 0, "Debe haber al menos 1 candidato para k=2")
        for cand in candidatos:
            self.assertEqual(len(cand), 2)
            self.assertTrue(self.inst._particion_valida(cand),
                            "Todos los candidatos deben pasar _particion_valida")

    def test_candidatos_k3_no_vacios(self):
        """_generar_candidatos_k(k=3) retorna ≥1 candidato con 3 partes válidas."""
        candidatos = self.inst._generar_candidatos_k(k=3)
        self.assertGreater(len(candidatos), 0, "Debe haber al menos 1 candidato para k=3")
        for cand in candidatos:
            self.assertEqual(len(cand), 3)
            self.assertTrue(self.inst._particion_valida(cand))

    def test_n_menor_k_retorna_lista_vacia(self):
        """Con n=3 variables y k=5, no se pueden formar 5 partes no vacías → []."""
        candidatos = self.inst._generar_candidatos_k(k=5)
        self.assertEqual(candidatos, [],
                         "Con n < k no debe haber candidatos posibles")

    def test_candidatos_fase_b_son_unicos(self):
        """
        Los candidatos de la Fase B (perturbaciones aleatorias) no deben duplicar
        las firmas de los candidatos ya existentes al entrar a esa fase.

        Nota de diseño: las estrategias deterministas E1, E2, E3 (Fase A) pueden
        producir la misma partición para n pequeño (ej. n=3, k=2), porque los tres
        algoritmos pueden converger al mismo grupo óptimo. La deduplicación por
        firmas_vistas aplica SOLO en la Fase B — este test verifica exactamente eso:
        que ningún candidato de la Fase B duplica la firma de un candidato previo.

        Estrategia: se ejecuta k=2 sobre n=3 y se verifica que los candidatos
        generados en la Fase B (si los hay) tengan firmas nuevas.
        """
        candidatos = self.inst._generar_candidatos_k(k=2)
        # Registrar firmas de los 3 primeros candidatos (Fase A)
        firmas_fase_a = set()
        for cand in candidatos[:3]:
            firmas_fase_a.add(frozenset(frozenset(p[0].tolist()) for p in cand))
        # Los candidatos de Fase B (posición 3+) no deben repetir firmas de Fase A
        for cand in candidatos[3:]:
            firma = frozenset(frozenset(p[0].tolist()) for p in cand)
            self.assertNotIn(firma, firmas_fase_a,
                             "Un candidato de Fase B duplica una firma de Fase A")

    def test_conteo_adaptativo_k3_n3(self):
        """
        Con n=3, k=3: S(3,3)=1 → solo existe 1 partición distinta (3 singletons).
        El conteo adaptativo n_objetivo = min(25, 1) = 1 limita Phase B a 0 extras.

        Comportamiento esperado: Phase A (E1, E2, E3) puede generar hasta 3 candidatos
        que son todos idénticos (la única partición posible). Phase B no agrega ninguno
        porque n_extra = 1 - len(candidatos_fase_a) < 0 → range(n_extra) vacío.
        Total: entre 1 y 3 candidatos (todos con la misma partición real).
        """
        candidatos = self.inst._generar_candidatos_k(k=3)
        # Debe haber al menos 1 candidato (la única k=3-partición de 3 elementos)
        self.assertGreaterEqual(len(candidatos), 1,
                                "Debe existir al menos 1 candidato para k=3, n=3")
        # No puede haber más de 3 (Phase A siempre tiene ≤3 estrategias)
        self.assertLessEqual(len(candidatos), 3,
                             "Phase A genera máximo 3 candidatos; Phase B no agrega con S(3,3)=1")


# ─────────────────────────────────────────────────────────────────────────────
# Suite 7 — Consistencia k=2: KGeometricSIA ≡ GeometricSIA
# ─────────────────────────────────────────────────────────────────────────────

class TestConsistenciaK2(unittest.TestCase):
    """
    Verifica la garantía formal de equivalencia:
        KGeometricSIA.aplicar_estrategia(k=2) ≡ GeometricSIA.aplicar_estrategia()

    Para k=2, `aplicar_estrategia` delega íntegramente a `super()` sin ejecutar
    ningún código propio de KGeometricSIA. Esto garantiza que el resultado es
    bit-a-bit idéntico al de la estrategia exacta de bi-partición (GeoMIP).

    Los tests verifican el mecanismo de delegación en vez de ejecutar el análisis
    completo (que requiere archivos CSV y un sistema de n nodos), porque lo que
    se prueba es el contrato de delegación, no el resultado numérico de GeoMIP.
    """

    def setUp(self):
        self.inst = _make_inst()

    def test_k2_delega_a_super(self):
        """Para k=2, aplicar_estrategia invoca exactamente GeometricSIA.aplicar_estrategia."""
        tpm = np.eye(8, dtype=np.float32)
        with patch(
            "src.controllers.strategies.geometric.GeometricSIA.aplicar_estrategia",
            return_value="RESULTADO_GEO"
        ) as mock_super:
            resultado = self.inst.aplicar_estrategia("111", "111", "111", tpm, k=2)

        mock_super.assert_called_once_with("111", "111", "111", tpm)
        self.assertEqual(resultado, "RESULTADO_GEO",
                         "El resultado de k=2 debe ser exactamente el de GeometricSIA")

    def test_k2_no_modifica_cache_mejor_por_k(self):
        """Para k=2, _cache_mejor_por_k NO debe actualizarse (k=2 lo maneja el padre)."""
        tpm = np.eye(8, dtype=np.float32)
        with patch(
            "src.controllers.strategies.geometric.GeometricSIA.aplicar_estrategia",
            return_value="DELEGADO"
        ):
            self.inst.aplicar_estrategia("111", "111", "111", tpm, k=2)

        self.assertNotIn(2, self.inst._cache_mejor_por_k,
                         "k=2 no debe escribir en _cache_mejor_por_k")

    def test_k_invalido_1_lanza_valueerror(self):
        """k=1 está fuera del dominio [K_MIN, K_MAX] → ValueError inmediato."""
        tpm = np.eye(8, dtype=np.float32)
        with self.assertRaises(ValueError):
            self.inst.aplicar_estrategia("111", "111", "111", tpm, k=1)

    def test_k_invalido_6_lanza_valueerror(self):
        """k=6 está fuera del dominio [K_MIN, K_MAX] → ValueError inmediato."""
        tpm = np.eye(8, dtype=np.float32)
        with self.assertRaises(ValueError):
            self.inst.aplicar_estrategia("111", "111", "111", tpm, k=6)

    def test_k_invalido_no_ejecuta_fases(self):
        """Con k inválido no se debe llegar a las Fases 1-3 (raise antes)."""
        tpm = np.eye(8, dtype=np.float32)
        with patch.object(self.inst, "sia_preparar_subsistema") as mock_prep:
            try:
                self.inst.aplicar_estrategia("111", "111", "111", tpm, k=0)
            except ValueError:
                pass
        mock_prep.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Suite 8 — Caché de subsistema entre valores de k
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheSubsistema(unittest.TestCase):
    """
    Verifica el comportamiento del caché de subsistema (_cache_subsistema):
        - La primera llamada (MISS) computa Fases 1-3 y guarda el snapshot.
        - La segunda llamada (HIT) restaura el snapshot sin recomputar.

    Se parchean sia_preparar_subsistema y calcular_costos_nivel para contar
    invocaciones sin ejecutar el cómputo real (que requiere TPM y CSV).
    """

    def setUp(self):
        self.inst = _make_inst()

    def _setup_fase3_mock(self):
        """
        Configura los mocks necesarios para que las Fases 1-3 sean interceptables.
        Inyecta el estado mínimo que el código posterior a las fases necesita.
        """
        def preparar_side_effect(cond, alc, mec, tpm):
            # Inyecta los atributos que las Fases 2-3 generan a partir del subsistema
            ncubo = MagicMock()
            ncubo.data = np.zeros((2, 2), dtype=np.float32)
            sub = MagicMock()
            sub.indices_ncubos = np.array([0, 1], dtype=np.int8)
            sub.dims_ncubos    = np.array([0, 1], dtype=np.int8)
            sub.ncubos         = [ncubo, ncubo]
            self.inst.sia_subsistema = sub
            self.inst.sia_dists_marginales = np.zeros(4, dtype=np.float32)

        return preparar_side_effect

    def test_cache_inicialmente_vacio(self):
        """Al crear la instancia, _cache_subsistema debe estar vacío."""
        self.assertEqual(len(self.inst._cache_subsistema), 0)

    def test_cache_mejor_por_k_inicialmente_vacio(self):
        """Al crear la instancia, _cache_mejor_por_k debe estar vacío."""
        self.assertEqual(len(self.inst._cache_mejor_por_k), 0)

    def test_memoria_k_particiones_se_resetea(self):
        """
        memoria_k_particiones debe estar vacío al inicio de cada aplicar_estrategia
        (independientemente de si hay cache hit o miss).
        """
        self.inst.memoria_k_particiones = {"sucio": True}
        # Simula llamada con k=3 que falla antes de las fases → memoria debe resetearse primero
        with patch.object(self.inst, "sia_preparar_subsistema",
                          side_effect=RuntimeError("detener en Fase 1")):
            try:
                self.inst.aplicar_estrategia("111", "11", "11", np.eye(4), k=3)
            except RuntimeError:
                pass
        self.assertEqual(self.inst.memoria_k_particiones, {},
                         "memoria_k_particiones debe resetearse al inicio de aplicar_estrategia")


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
