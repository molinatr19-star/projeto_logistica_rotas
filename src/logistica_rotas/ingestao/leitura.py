"""Leitura padronizada da base de entregas simuladas."""

from pathlib import Path

import pandas as pd

from logistica_rotas.ingestao.simulacao import CAMINHO_PADRAO, FUSO, gerar_e_salvar

COLUNAS_CATEGORICAS = [
    "cidade_origem", "bairro_origem", "cidade_destino", "bairro_destino", "horario_pico", "status",
]

# Siglas para rótulos curtos ("Centro · SBC"): o nome do bairro se repete entre cidades.
SIGLA_CIDADE = {
    "Santo André": "SA",
    "São Bernardo do Campo": "SBC",
    "São Caetano do Sul": "SCS",
    "Diadema": "Diadema",
    "Mauá": "Mauá",
}


def carregar_entregas(caminho: Path = CAMINHO_PADRAO) -> pd.DataFrame:
    """Lê o CSV de entregas com tipos corretos. Gera o arquivo se ele não existir."""
    caminho = Path(caminho)
    if not caminho.exists():
        gerar_e_salvar(caminho)
    df = pd.read_csv(caminho, encoding="utf-8")
    df["data_hora_pedido"] = pd.to_datetime(df["data_hora_pedido"], utc=True).dt.tz_convert(FUSO)
    for coluna in COLUNAS_CATEGORICAS:
        df[coluna] = df[coluna].astype("category")
    return df


def rotulo_local(bairro: pd.Series, cidade: pd.Series) -> pd.Series:
    """Bairro + sigla da cidade, para diferenciar bairros homônimos (ex.: "Centro · SA")."""
    return bairro.astype(str) + " · " + cidade.astype(str).map(SIGLA_CIDADE).fillna(cidade.astype(str))
