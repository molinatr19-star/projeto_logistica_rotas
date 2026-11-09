"""Testes da montagem de lotes e do resumo por método."""

import pandas as pd
import pytest

from logistica_rotas.ingestao.simulacao import gerar_entregas
from logistica_rotas.roteirizacao.lotes import montar_lotes, resumo_metodos


def test_lotes_respeitam_minimo_e_excluem_cancelados():
    df = gerar_entregas(n=1500)
    lotes = montar_lotes(df, janela="2h", minimo=3)
    assert (lotes["status"] != "cancelado").all()
    assert lotes.groupby("lote").size().min() >= 3
    # cada lote tem uma única cidade de origem e uma única janela
    assert (lotes.groupby("lote")["cidade_hub"].nunique() == 1).all()
    assert (lotes.groupby("lote")["janela"].nunique() == 1).all()


def test_resumo_metodos_economia_e_prazo():
    resultados = pd.DataFrame({
        "lote": [0, 0, 1, 1],
        "metodo": ["individual", "OR-Tools", "individual", "OR-Tools"],
        "entregas": [4, 4, 6, 6],
        "km": [20.0, 10.0, 30.0, 15.0],
        "viagens": [4, 1, 6, 2],
        "no_prazo": [4, 3, 6, 5],
        "atraso_total_min": [0.0, 5.0, 0.0, 2.0],
        "pico": [True, True, False, False],
    })
    r = resumo_metodos(resultados)
    assert r.loc["OR-Tools", "economia_km_pct"] == pytest.approx(50.0)
    assert r.loc["OR-Tools", "no_prazo_pct"] == pytest.approx(80.0)
    assert r.loc["OR-Tools", "entregas_por_viagem"] == pytest.approx(10 / 3)

    por_pico = resumo_metodos(resultados, por=["pico"])
    assert por_pico.loc[(True, "OR-Tools"), "economia_km_pct"] == pytest.approx(50.0)
    assert por_pico.loc[(False, "individual"), "economia_km_pct"] == pytest.approx(0.0)


def test_espera_ate_o_fim_da_janela():
    df = gerar_entregas(n=1500)
    lotes = montar_lotes(df, janela="30min", minimo=2)
    assert lotes["espera_min"].between(0, 30).all()
    fim = lotes["janela"] + pd.Timedelta("30min")
    esperado = (fim - lotes["data_hora_pedido"]).dt.total_seconds() / 60
    assert (lotes["espera_min"] - esperado).abs().max() < 1e-9


def test_considerar_espera_nao_melhora_prazo():
    from logistica_rotas.roteirizacao.lotes import amostrar_lotes, avaliar_lotes

    lotes = amostrar_lotes(montar_lotes(gerar_entregas(n=3000), janela="1h", minimo=3), n=15)
    metodos = ["individual", "OR-Tools com prazo"]
    sem = resumo_metodos(avaliar_lotes(lotes, metodos=metodos, considerar_espera=False))
    com = resumo_metodos(avaliar_lotes(lotes, metodos=metodos, considerar_espera=True))
    # o individual sai na hora: não muda; o lote perde prazo ao esperar
    assert com.loc["individual", "no_prazo_pct"] == pytest.approx(sem.loc["individual", "no_prazo_pct"])
    assert com.loc["OR-Tools com prazo", "no_prazo_pct"] <= sem.loc["OR-Tools com prazo", "no_prazo_pct"]


def test_penalidade_maior_nao_reduz_prazo():
    from logistica_rotas.roteirizacao.lotes import amostrar_lotes, avaliar_lotes

    lotes = amostrar_lotes(montar_lotes(gerar_entregas(n=3000)), n=15)
    baixa = resumo_metodos(avaliar_lotes(lotes, penalidade_km_por_min=0.1, metodos=["individual", "OR-Tools com prazo"]))
    alta = resumo_metodos(avaliar_lotes(lotes, penalidade_km_por_min=20, metodos=["individual", "OR-Tools com prazo"]))
    assert alta.loc["OR-Tools com prazo", "no_prazo_pct"] >= baixa.loc["OR-Tools com prazo", "no_prazo_pct"]
    assert alta.loc["OR-Tools com prazo", "km"] >= baixa.loc["OR-Tools com prazo", "km"] - 1e-6
