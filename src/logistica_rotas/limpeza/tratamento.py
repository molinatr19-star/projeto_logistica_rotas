"""Validação e limpeza da base de entregas (raw -> interim -> processed).

Regra de outlier de tempo (avaliada no notebook 02):
    tempo_transito_min > FATOR_OUTLIER x mediana do tempo das entregas
    da mesma faixa de distância, OU velocidade média > VELOCIDADE_MAX_KMH.

Tratamento: o registro NÃO é apagado. O valor original fica em
`tempo_transito_min_bruto`, a coluna `outlier_tempo` marca o caso e
`tempo_transito_min` vira vazio (NaN) na base tratada.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from logistica_rotas.ingestao.leitura import rotulo_local
from logistica_rotas.ingestao.simulacao import RAIZ_PROJETO

CAMINHO_INTERIM = RAIZ_PROJETO / "data" / "interim" / "entregas_validadas.parquet"
CAMINHO_PROCESSED = RAIZ_PROJETO / "data" / "processed" / "entregas_limpas.parquet"

FAIXAS_DISTANCIA_KM = [0, 2, 4, 6, 8, 10, 15, np.inf]
ROTULOS_FAIXAS = ["0-2", "2-4", "4-6", "6-8", "8-10", "10-15", "15+"]
FATOR_OUTLIER = 3.0
VELOCIDADE_MAX_KMH = 60.0  # acima disso é impossível para moto em área urbana


def adicionar_colunas_derivadas(df: pd.DataFrame) -> pd.DataFrame:
    """Colunas de apoio: rótulo bairro+cidade, trajeto, hora, dia útil, faixa e velocidade."""
    df = df.copy()
    df["local_origem"] = rotulo_local(df["bairro_origem"], df["cidade_origem"])
    df["local_destino"] = rotulo_local(df["bairro_destino"], df["cidade_destino"])
    mesma = df["cidade_origem"].astype(str) == df["cidade_destino"].astype(str)
    df["trajeto"] = np.where(mesma, "mesma cidade", "entre cidades")
    df["hora"] = df["data_hora_pedido"].dt.hour
    df["dia_util"] = df["data_hora_pedido"].dt.day_of_week < 5
    df["faixa_distancia_km"] = pd.cut(df["distancia_km"], bins=FAIXAS_DISTANCIA_KM,
                                      labels=ROTULOS_FAIXAS, right=False)
    df["velocidade_media_kmh"] = df["distancia_km"] / (df["tempo_transito_min"] / 60)
    return df


def razao_tempo_faixa(df: pd.DataFrame) -> pd.Series:
    """Tempo da entrega dividido pela mediana do tempo na mesma faixa de distância."""
    faixa = pd.cut(df["distancia_km"], bins=FAIXAS_DISTANCIA_KM, right=False)
    mediana = df.groupby(faixa, observed=True)["tempo_transito_min"].transform("median")
    return df["tempo_transito_min"] / mediana


def marcar_outliers_tempo(df: pd.DataFrame, fator: float = FATOR_OUTLIER) -> pd.Series:
    """True quando o tempo é implausível (regra no docstring do módulo). Cancelados = False."""
    velocidade = df["distancia_km"] / (df["tempo_transito_min"] / 60)
    lento_demais = razao_tempo_faixa(df) > fator
    rapido_demais = velocidade > VELOCIDADE_MAX_KMH
    return (lento_demais | rapido_demais).fillna(False).astype(bool)


def validar_entregas(df: pd.DataFrame) -> pd.DataFrame:
    """Base interim: valores originais + colunas derivadas + marcação de outlier."""
    df = adicionar_colunas_derivadas(df)
    df["outlier_tempo"] = marcar_outliers_tempo(df)
    return df


def limpar_entregas(df: pd.DataFrame) -> pd.DataFrame:
    """Base processed: tempo dos outliers vira NaN (original preservado em `_bruto`)."""
    df = validar_entregas(df) if "outlier_tempo" not in df.columns else df.copy()
    df["tempo_transito_min_bruto"] = df["tempo_transito_min"]
    df.loc[df["outlier_tempo"], "tempo_transito_min"] = np.nan
    df["velocidade_media_kmh"] = df["distancia_km"] / (df["tempo_transito_min"] / 60)
    return df


def salvar_parquet(df: pd.DataFrame, caminho: Path) -> Path:
    """Salva em Parquet (preserva tipos, inclusive data com fuso e categorias)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(caminho, index=False)
    return caminho
