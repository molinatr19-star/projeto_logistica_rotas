"""Testes do despacho com várias coletas na mesma viagem."""

import pytest

from logistica_rotas.ingestao.simulacao import gerar_entregas
from logistica_rotas.roteirizacao.coleta_multipla import sequencias_validas, simular_coleta_multipla
from logistica_rotas.roteirizacao.despacho import resumo_despacho


def test_quantidade_de_sequencias():
    # (2k)! / 2^k ordens com coleta antes da entrega
    assert [len(sequencias_validas(k)) for k in (1, 2, 3)] == [1, 6, 90]


def test_coleta_sempre_antes_da_entrega():
    for seq in sequencias_validas(3):
        for j in range(3):
            assert seq.index((j, "c")) < seq.index((j, "e"))


@pytest.fixture(scope="module")
def base():
    return gerar_entregas(n=2000)


def test_individual_uma_viagem_por_pedido(base):
    e = simular_coleta_multipla(base, 0, capacidade=1)
    assert e["viagem"].nunique() == len(e)


def test_capacidade_e_km_nao_aumenta(base):
    ind = resumo_despacho(simular_coleta_multipla(base, 0, capacidade=1))
    e = simular_coleta_multipla(base, 10, capacidade=3, espera_max_pico_min=None)
    assert e.groupby("viagem").size().max() <= 3
    assert resumo_despacho(e)["km"] <= ind["km"] + 1e-6


def test_capacidade_acima_do_limite_gera_erro(base):
    with pytest.raises(ValueError):
        simular_coleta_multipla(base, 5, capacidade=4)
