"""Testes da regra de outlier e da limpeza."""

import numpy as np
import pandas as pd
import pytest

import logistica_rotas.ingestao.simulacao as simulacao
from logistica_rotas.limpeza.tratamento import limpar_entregas, marcar_outliers_tempo


def base_faixa_unica(tempos: list[float], distancia: float = 3.0) -> pd.DataFrame:
    """Entregas na mesma faixa de distância, com os tempos informados."""
    return pd.DataFrame({
        "distancia_km": [distancia] * len(tempos),
        "tempo_transito_min": tempos,
    })


def test_marca_tempo_muito_acima_da_mediana():
    df = base_faixa_unica([10, 11, 12, 13, 60])  # mediana 12; 60 > 3 x 12
    assert marcar_outliers_tempo(df).tolist() == [False, False, False, False, True]


def test_nao_marca_tempo_dentro_do_limite():
    df = base_faixa_unica([10, 11, 12, 13, 35])  # 35 < 3 x 12
    assert not marcar_outliers_tempo(df).any()


def test_marca_velocidade_impossivel():
    df = base_faixa_unica([10, 11, 12, 13, 1], distancia=3.0)  # 3 km em 1 min = 180 km/h
    assert marcar_outliers_tempo(df).iloc[-1]


def test_cancelado_sem_tempo_nao_e_outlier():
    df = base_faixa_unica([10, 11, np.nan])
    assert not marcar_outliers_tempo(df).iloc[-1]


@pytest.fixture(scope="module")
def bases_simuladas() -> tuple[pd.DataFrame, pd.Series]:
    """Base simulada pequena + gabarito dos erros propositais (mesma seed sem outliers)."""
    df = simulacao.gerar_entregas(n=2000)
    original = simulacao.PROB_OUTLIER_TEMPO
    simulacao.PROB_OUTLIER_TEMPO = 0.0
    try:
        sem_erros = simulacao.gerar_entregas(n=2000)
    finally:
        simulacao.PROB_OUTLIER_TEMPO = original
    gabarito = (df["tempo_transito_min"] != sem_erros["tempo_transito_min"]) & df["tempo_transito_min"].notna()
    return df, gabarito


def test_regra_encontra_os_erros_propositais(bases_simuladas):
    df, gabarito = bases_simuladas
    marcados = marcar_outliers_tempo(df)
    assert gabarito.sum() > 0
    assert (marcados & gabarito).sum() == gabarito.sum()       # nenhum erro perdido
    assert (marcados & ~gabarito).sum() <= 0.002 * len(df)     # no máximo 0,2% de falsos positivos


def test_limpeza_preserva_linhas_e_valor_original(bases_simuladas):
    df, _ = bases_simuladas
    limpo = limpar_entregas(df)
    assert len(limpo) == len(df)
    assert limpo.loc[limpo["outlier_tempo"], "tempo_transito_min"].isna().all()
    pd.testing.assert_series_equal(
        limpo["tempo_transito_min_bruto"], df["tempo_transito_min"], check_names=False
    )


def test_simulacao_reprodutivel():
    a = simulacao.gerar_entregas(n=200)
    b = simulacao.gerar_entregas(n=200)
    pd.testing.assert_frame_equal(a, b)
