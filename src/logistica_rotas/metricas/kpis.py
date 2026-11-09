"""KPIs logísticos de entregas (definições em docs/dicionario_dados.md).

Regras comuns:
- Entregas concluídas = status diferente de "cancelado".
- Se a base tiver a coluna `outlier_tempo` (base limpa), esses registros saem
  do OTD e da taxa de atraso: o status foi calculado com um tempo inválido.
- Tempo de trânsito: usar a mediana nos resumos (menos sensível a extremos).
"""

import pandas as pd

STATUS_NO_PRAZO = "entregue"
STATUS_ATRASO = "com_atraso"
STATUS_CANCELADO = "cancelado"


def mascara_concluidas(df: pd.DataFrame) -> pd.Series:
    """True para entregas concluídas e com tempo válido (quando houver a coluna `outlier_tempo`)."""
    mascara = df["status"] != STATUS_CANCELADO
    if "outlier_tempo" in df.columns:
        mascara &= ~df["outlier_tempo"].astype(bool)
    return mascara


def _percentual(parte: pd.Series) -> float:
    """Média de uma série booleana em %; NaN se vazia."""
    return float(parte.mean() * 100) if len(parte) else float("nan")


def taxa_otd(df: pd.DataFrame) -> float:
    """OTD (%) = entregas no prazo / entregas concluídas."""
    feitas = df[mascara_concluidas(df)]
    return _percentual(feitas["status"] == STATUS_NO_PRAZO)


def taxa_atraso(df: pd.DataFrame) -> float:
    """Taxa de atraso (%) = entregas com atraso / entregas concluídas (= 100 - OTD)."""
    feitas = df[mascara_concluidas(df)]
    return _percentual(feitas["status"] == STATUS_ATRASO)


def taxa_cancelamento(df: pd.DataFrame) -> float:
    """Taxa de cancelamento (%) = cancelados / total de pedidos."""
    return _percentual(df["status"] == STATUS_CANCELADO)


def resumo_operacional(grupo: pd.DataFrame) -> pd.Series:
    """Indicadores básicos de um grupo de entregas (usar com groupby().apply)."""
    feitas = grupo[mascara_concluidas(grupo)]
    return pd.Series({
        "pedidos": len(grupo),
        "otd_%": taxa_otd(grupo),
        "cancelamento_%": taxa_cancelamento(grupo),
        "distancia_media_km": grupo["distancia_km"].mean(),
        "tempo_mediano_min": feitas["tempo_transito_min"].median(),
        "valor_medio_brl": grupo["valor_entrega_brl"].mean(),
    })
