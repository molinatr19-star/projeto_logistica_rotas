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
