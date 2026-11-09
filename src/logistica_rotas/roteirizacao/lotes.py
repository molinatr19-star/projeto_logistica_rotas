"""Montagem dos lotes de entrega e avaliação dos métodos de roteirização em todos eles."""

from pathlib import Path

import numpy as np
import pandas as pd

from logistica_rotas.ingestao.simulacao import BAIRROS, RAIZ_PROJETO
from logistica_rotas.roteirizacao.rotas import CAPACIDADE_PADRAO, comparar_metodos

CAMINHO_RESULTADOS = RAIZ_PROJETO / "data" / "processed" / "resultados_rotas.parquet"
JANELA_PADRAO = "2h"
MINIMO_POR_LOTE = 3
ORDEM_METODOS = ["individual", "vizinho mais próximo", "OR-Tools", "OR-Tools com prazo"]


def hubs_por_cidade() -> pd.DataFrame:
    """Hub de cada cidade = coordenada do bairro Centro."""
    return BAIRROS[BAIRROS["bairro"] == "Centro"].set_index("cidade")[["lat", "lon"]]


def montar_lotes(df: pd.DataFrame, janela: str = JANELA_PADRAO, minimo: int = MINIMO_POR_LOTE) -> pd.DataFrame:
    """Pedidos não cancelados com coluna `lote` (cidade de origem + janela de tempo); só lotes >= minimo."""
    base = df[df["status"] != "cancelado"].copy()
    base["janela"] = base["data_hora_pedido"].dt.floor(janela)
    base["cidade_hub"] = base["cidade_origem"].astype(str)
    tamanho = base.groupby(["cidade_hub", "janela"])["id_pedido"].transform("size")
    base = base[tamanho >= minimo]
    base["lote"] = base.groupby(["cidade_hub", "janela"]).ngroup()
    return base


def lote_em_pico(lote: pd.DataFrame) -> bool:
    """O lote usa a velocidade de pico se a maioria dos pedidos foi feita no pico."""
    return bool((lote["horario_pico"] == "sim").mean() >= 0.5)


def avaliar_lote(lote: pd.DataFrame, hubs: pd.DataFrame, capacidade: int = CAPACIDADE_PADRAO) -> list:
    """Roda os 4 métodos em um lote; devolve a lista de ResultadoRotas."""
    hub = tuple(hubs.loc[lote["cidade_hub"].iloc[0]])
    return comparar_metodos(hub, lote["lat_destino"].to_numpy(), lote["lon_destino"].to_numpy(),
                            lote["prazo_prometido_min"].to_numpy(), lote_em_pico(lote), capacidade)


def avaliar_lotes(lotes: pd.DataFrame, capacidade: int = CAPACIDADE_PADRAO) -> pd.DataFrame:
    """Uma linha por lote x método: km, viagens, entregas no prazo e minutos de atraso."""
    hubs = hubs_por_cidade()
    linhas = []
    for id_lote, lote in lotes.groupby("lote"):
        prazos = lote["prazo_prometido_min"].to_numpy()
        for r in avaliar_lote(lote, hubs, capacidade):
            atraso = np.clip(r.chegada_min - prazos, 0, None)
            linhas.append({
                "lote": id_lote, "cidade_hub": lote["cidade_hub"].iloc[0], "janela": lote["janela"].iloc[0],
                "entregas": len(lote), "pico": lote_em_pico(lote), "metodo": r.metodo,
                "km": r.km_total, "viagens": len(r.rotas), "no_prazo": int((atraso == 0).sum()),
                "atraso_total_min": float(atraso.sum()),
            })
    return pd.DataFrame(linhas)


def resumo_metodos(resultados: pd.DataFrame, por: list[str] | None = None) -> pd.DataFrame:
    """Km, km por entrega, economia vs individual, entregas por viagem e % no prazo por método."""
    chaves = (por or []) + ["metodo"]
    r = resultados.groupby(chaves, sort=False)[["km", "viagens", "no_prazo", "entregas", "atraso_total_min"]].sum()
    r["km_por_entrega"] = r["km"] / r["entregas"]
    r["entregas_por_viagem"] = r["entregas"] / r["viagens"]
    r["no_prazo_pct"] = r["no_prazo"] / r["entregas"] * 100
    base = r.xs("individual", level="metodo")["km"] if por else r.loc["individual", "km"]
    r["economia_km_pct"] = (1 - r["km"] / (base.reindex(r.index.droplevel("metodo")).to_numpy() if por else base)) * 100
    return r


def carregar_ou_calcular(lotes: pd.DataFrame, caminho: Path = CAMINHO_RESULTADOS, recalcular: bool = False) -> pd.DataFrame:
    """Lê os resultados salvos ou calcula de novo (leva alguns minutos) e salva."""
    caminho = Path(caminho)
    if caminho.exists() and not recalcular:
        return pd.read_parquet(caminho)
    resultados = avaliar_lotes(lotes)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    resultados.to_parquet(caminho, index=False)
    return resultados
