"""Testes da roteirização com matrizes pequenas e casos com resposta conhecida."""

import numpy as np
import pytest

from logistica_rotas.roteirizacao.rotas import (
    TEMPO_PARADA_MIN,
    avaliar_rotas,
    comparar_metodos,
    matriz_distancias_km,
    rotas_individuais,
    rotas_ortools,
    rotas_vizinho_mais_proximo,
)


def matriz_em_linha(posicoes_km: list[float]) -> np.ndarray:
    """Hub em 0 km e pedidos em pontos de uma reta (distância = diferença)."""
    pos = np.array([0.0, *posicoes_km])
    return np.abs(pos[:, None] - pos[None, :])


def test_individual_e_ida_e_volta():
    m = matriz_em_linha([1, 2, 3])
    r = rotas_individuais(m, pico=False)
    assert r.km_total == pytest.approx(2 * (1 + 2 + 3))


def test_vizinho_mais_proximo_em_linha():
    m = matriz_em_linha([3, 1, 2])
    r = rotas_vizinho_mais_proximo(m, pico=False, capacidade=4)
    assert r.rotas == [[2, 3, 1]]        # 1 km -> 2 km -> 3 km
    assert r.km_total == pytest.approx(6)  # vai até 3 e volta


def test_capacidade_respeitada_e_todos_visitados():
    m = matriz_em_linha([1, 2, 3, 4, 5, 6, 7])
    for r in (rotas_vizinho_mais_proximo(m, False, 3), rotas_ortools(m, False, 3)):
        assert all(len(rota) <= 3 for rota in r.rotas)
        assert sorted(no for rota in r.rotas for no in rota) == list(range(1, 8))


def test_ortools_nao_e_pior_que_heuristica():
    rng = np.random.default_rng(0)
    pts = rng.uniform(-0.05, 0.05, size=(9, 2)) + [-23.68, -46.55]
    m = matriz_distancias_km(pts[:, 0], pts[:, 1])
    vmp = rotas_vizinho_mais_proximo(m, False, 4)
    ort = rotas_ortools(m, False, 4, tempo_limite_s=0.5)
    assert ort.km_total <= vmp.km_total + 1e-6


def test_tempo_de_chegada_inclui_paradas():
    m = matriz_em_linha([7, 14])  # 7 km a 28 km/h = 15 min
    km, chegada = avaliar_rotas([[1, 2]], m, pico=False)
    assert km == pytest.approx(28)
    assert chegada[0] == pytest.approx(15)
    assert chegada[1] == pytest.approx(30 + TEMPO_PARADA_MIN)


def test_prazo_reduz_atraso():
    # Considerar o prazo nunca pode gerar mais atraso total que ignorá-lo.
    m = matriz_em_linha([5, 5.5])
    prazos = np.array([60.0, 5.0])
    sem_prazo = rotas_ortools(m, False, 2)
    com_prazo = rotas_ortools(m, False, 2, prazos_min=prazos)
    atraso = lambda r: np.clip(r.chegada_min - prazos, 0, None).sum()  # noqa: E731
    assert atraso(com_prazo) <= atraso(sem_prazo)


def test_comparar_metodos_retorna_quatro():
    lats = np.array([-23.67, -23.66, -23.65])
    lons = np.array([-46.54, -46.53, -46.55])
    resultados = comparar_metodos((-23.664, -46.538), lats, lons, np.array([30, 30, 30]), pico=False)
    assert [r.metodo for r in resultados] == ["individual", "vizinho mais próximo", "OR-Tools", "OR-Tools com prazo"]
