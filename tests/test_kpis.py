"""Testes dos KPIs com bases pequenas, montadas à mão (resultado conhecido)."""

import math

import pandas as pd
import pytest

from logistica_rotas.metricas.kpis import (
    mascara_concluidas,
    resumo_operacional,
    taxa_atraso,
    taxa_cancelamento,
    taxa_otd,
)


@pytest.fixture
def base() -> pd.DataFrame:
    """4 pedidos: 2 no prazo, 1 com atraso, 1 cancelado."""
    return pd.DataFrame({
        "status": ["entregue", "entregue", "com_atraso", "cancelado"],
        "distancia_km": [2.0, 4.0, 6.0, 8.0],
        "tempo_transito_min": [10.0, 20.0, 30.0, float("nan")],
        "valor_entrega_brl": [10.0, 12.0, 14.0, 16.0],
    })


def test_otd_ignora_cancelados(base):
    assert taxa_otd(base) == pytest.approx(200 / 3)


def test_atraso_e_complemento_do_otd(base):
    assert taxa_atraso(base) == pytest.approx(100 - taxa_otd(base))


def test_cancelamento_sobre_total(base):
    assert taxa_cancelamento(base) == pytest.approx(25.0)


def test_outlier_sai_do_denominador(base):
    base["outlier_tempo"] = [False, False, True, False]
    assert mascara_concluidas(base).tolist() == [True, True, False, False]
    assert taxa_otd(base) == pytest.approx(100.0)


def test_base_vazia_retorna_nan(base):
    vazia = base.iloc[0:0]
    assert math.isnan(taxa_otd(vazia))
    assert math.isnan(taxa_cancelamento(vazia))


def test_resumo_operacional(base):
    r = resumo_operacional(base)
    assert r["pedidos"] == 4
    assert r["tempo_mediano_min"] == pytest.approx(20.0)
    assert r["distancia_media_km"] == pytest.approx(5.0)
    assert r["valor_medio_brl"] == pytest.approx(13.0)
