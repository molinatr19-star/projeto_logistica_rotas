"""Testes do despacho dinâmico."""

import pytest

from logistica_rotas.ingestao.simulacao import gerar_entregas
from logistica_rotas.roteirizacao.despacho import resumo_despacho, simular_despacho


@pytest.fixture(scope="module")
def base():
    return gerar_entregas(n=3000)


def test_individual_uma_viagem_por_pedido_sem_espera(base):
    e = simular_despacho(base, 0, capacidade=1)
    assert e["viagem"].nunique() == len(e)
    assert (e["espera_min"] == 0).all()


def test_dinamico_respeita_capacidade_e_espera_maxima(base):
    e = simular_despacho(base, 10, capacidade=3)
    assert e.groupby("viagem").size().max() <= 3
    assert e["espera_min"].max() <= 10 + 1e-9
    assert (e["espera_min"] >= -1e-9).all()


def test_dinamico_nao_piora_prazo_planejado_nem_aumenta_km(base):
    ind = resumo_despacho(simular_despacho(base, 0, capacidade=1))
    din = resumo_despacho(simular_despacho(base, 10, capacidade=4), ind["km"])
    assert din["km"] <= ind["km"] + 1e-6
    assert din["no_prazo_plan_pct"] >= ind["no_prazo_plan_pct"] - 1e-9
    assert din["economia_km_pct"] >= 0


def test_margem_reduz_espera(base):
    sem = resumo_despacho(simular_despacho(base, 15, margem_min=0))
    com = resumo_despacho(simular_despacho(base, 15, margem_min=5))
    assert com["espera_media_min"] <= sem["espera_media_min"] + 1e-9
