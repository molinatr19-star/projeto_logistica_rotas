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


def test_sem_espera_no_pico(base):
    e = simular_despacho(base, 10, capacidade=4, espera_max_pico_min=0)
    sozinhos = e.groupby("viagem").filter(lambda v: len(v) == 1)
    # pedido de pico que abriu viagem sozinho sai na hora
    assert (sozinhos.loc[sozinhos["pico"], "espera_min"].abs() < 1e-9).all()


def test_coleta_por_bairro_so_agrupa_mesmo_bairro(base):
    e = simular_despacho(base, 10, capacidade=4, ponto_coleta="bairro")
    assert (e.groupby("viagem")["ponto_coleta"].nunique() == 1).all()


def test_fator_osrm_aumenta_km():
    from logistica_rotas.roteirizacao.despacho import fator_por_distancia

    assert fator_por_distancia(1.0) > fator_por_distancia(10.0) > 1.3
    b = gerar_entregas(n=800)
    km_13 = resumo_despacho(simular_despacho(b, 0, capacidade=1))["km"]
    km_osrm = resumo_despacho(simular_despacho(b, 0, capacidade=1, fator="osrm"))["km"]
    assert km_osrm > km_13
