"""Análise de sensibilidade da roteirização.

Três perguntas:
1. Penalidade de atraso: quanto de km trocamos por prazo? (curva de troca)
2. Capacidade da moto: quantos pedidos por viagem compensam?
3. Janela do lote, contando a espera até o despacho, em dois volumes de demanda:
   a partir de que volume agrupar pedidos compensa?

Cada cenário roda numa amostra fixa de lotes (`N_LOTES_AMOSTRA`, seed 42) para caber
em poucos minutos. Resultado salvo em data/processed/sensibilidade.parquet.
"""

from pathlib import Path

import pandas as pd

from logistica_rotas.ingestao.simulacao import RAIZ_PROJETO, gerar_entregas
from logistica_rotas.roteirizacao.lotes import amostrar_lotes, avaliar_lotes, montar_lotes, resumo_metodos
from logistica_rotas.roteirizacao.rotas import CAPACIDADE_PADRAO, PENALIDADE_KM_POR_MIN

CAMINHO_SENSIBILIDADE = RAIZ_PROJETO / "data" / "processed" / "sensibilidade.parquet"
N_LOTES_AMOSTRA = 200
PENALIDADES = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
CAPACIDADES = [2, 3, 4, 5, 6]
JANELAS = ["15min", "30min", "1h", "2h"]
VOLUMES = {"atual (5.000 pedidos)": 5_000, "4x (20.000 pedidos)": 20_000}
METODOS = ["individual", "OR-Tools com prazo"]


def _resumir(resultados: pd.DataFrame, **rotulos) -> pd.DataFrame:
    """Resumo por método com colunas extras identificando o cenário."""
    r = resumo_metodos(resultados).reset_index()
    for chave, valor in rotulos.items():
        r[chave] = valor
    return r


def cenarios_penalidade(lotes: pd.DataFrame, valores: list[float] = PENALIDADES) -> pd.DataFrame:
    """OR-Tools com prazo variando a penalidade (sem espera, janela e capacidade padrão)."""
    amostra = amostrar_lotes(lotes, N_LOTES_AMOSTRA)
    partes = [_resumir(avaliar_lotes(amostra, metodos=["individual", "vizinho mais próximo", "OR-Tools"]),
                       analise="penalidade", valor=0.0)]
    for p in valores:
        partes.append(_resumir(avaliar_lotes(amostra, penalidade_km_por_min=p, metodos=METODOS),
                               analise="penalidade", valor=p))
    return pd.concat(partes, ignore_index=True)


def cenarios_capacidade(lotes: pd.DataFrame, valores: list[int] = CAPACIDADES) -> pd.DataFrame:
    """OR-Tools com prazo variando a capacidade da moto (penalidade padrão, sem espera)."""
    amostra = amostrar_lotes(lotes, N_LOTES_AMOSTRA)
    return pd.concat([_resumir(avaliar_lotes(amostra, capacidade=c, metodos=METODOS), analise="capacidade", valor=c)
                      for c in valores], ignore_index=True)


def cenarios_janela(df: pd.DataFrame, rotulo_volume: str, janelas: list[str] = JANELAS) -> pd.DataFrame:
    """Janela do lote contando a espera; inclui a cobertura (% das entregas que formam lote)."""
    nao_canceladas = int((df["status"] != "cancelado").sum())
    partes = []
    for janela in janelas:
        lotes = montar_lotes(df, janela=janela, minimo=2)
        cobertura = len(lotes) / nao_canceladas * 100
        amostra = amostrar_lotes(lotes, N_LOTES_AMOSTRA)
        r = _resumir(avaliar_lotes(amostra, considerar_espera=True, metodos=METODOS),
                     analise="janela", valor=janela, volume=rotulo_volume)
        r["cobertura_pct"] = cobertura
        r["espera_media_min"] = amostra["espera_min"].mean()
        partes.append(r)
    return pd.concat(partes, ignore_index=True)


def rodar_tudo(df: pd.DataFrame) -> pd.DataFrame:
    """Roda as três análises. `df` é a base limpa atual (5.000 pedidos)."""
    lotes = montar_lotes(df)
    partes = [cenarios_penalidade(lotes), cenarios_capacidade(lotes)]
    for rotulo, n in VOLUMES.items():
        base = df if n == len(df) else gerar_entregas(n=n)
        partes.append(cenarios_janela(base, rotulo))
    resultado = pd.concat(partes, ignore_index=True)
    resultado["valor"] = resultado["valor"].astype(str)
    return resultado


def carregar_ou_calcular(df: pd.DataFrame, caminho: Path = CAMINHO_SENSIBILIDADE, recalcular: bool = False) -> pd.DataFrame:
    """Lê o resultado salvo ou roda tudo de novo (cerca de 15 minutos) e salva."""
    caminho = Path(caminho)
    if caminho.exists() and not recalcular:
        return pd.read_parquet(caminho)
    resultado = rodar_tudo(df)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_parquet(caminho, index=False)
    return resultado


__all__ = ["CAPACIDADE_PADRAO", "PENALIDADE_KM_POR_MIN", "carregar_ou_calcular", "rodar_tudo"]
