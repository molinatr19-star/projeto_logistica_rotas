"""Montagem dos lotes de entrega e avaliação dos métodos de roteirização em todos eles."""

from pathlib import Path

import numpy as np
import pandas as pd

from logistica_rotas.ingestao.simulacao import BAIRROS, RAIZ_PROJETO
from logistica_rotas.roteirizacao.rotas import (
    CAPACIDADE_PADRAO,
    PENALIDADE_KM_POR_MIN,
    matriz_distancias_km,
    rotas_individuais,
    rotas_ortools,
    rotas_vizinho_mais_proximo,
)

CAMINHO_RESULTADOS = RAIZ_PROJETO / "data" / "processed" / "resultados_rotas.parquet"
JANELA_PADRAO = "2h"
MINIMO_POR_LOTE = 3
ORDEM_METODOS = ["individual", "vizinho mais próximo", "OR-Tools", "OR-Tools com prazo"]


def hubs_por_cidade() -> pd.DataFrame:
    """Hub de cada cidade = coordenada do bairro Centro."""
    return BAIRROS[BAIRROS["bairro"] == "Centro"].set_index("cidade")[["lat", "lon"]]


def montar_lotes(df: pd.DataFrame, janela: str = JANELA_PADRAO, minimo: int = MINIMO_POR_LOTE) -> pd.DataFrame:
    """Pedidos não cancelados com coluna `lote` (cidade de origem + janela de tempo); só lotes >= minimo.

    `espera_min`: tempo entre o pedido e o fim da janela (momento do despacho do lote).
    """
    base = df[df["status"] != "cancelado"].copy()
    base["janela"] = base["data_hora_pedido"].dt.floor(janela)
    base["espera_min"] = (base["janela"] + pd.Timedelta(janela) - base["data_hora_pedido"]).dt.total_seconds() / 60
    base["cidade_hub"] = base["cidade_origem"].astype(str)
    tamanho = base.groupby(["cidade_hub", "janela"])["id_pedido"].transform("size")
    base = base[tamanho >= minimo]
    base["lote"] = base.groupby(["cidade_hub", "janela"]).ngroup()
    return base


def amostrar_lotes(lotes: pd.DataFrame, n: int, random_state: int = 42) -> pd.DataFrame:
    """Sorteia `n` lotes inteiros (para análises de sensibilidade mais rápidas)."""
    ids = lotes["lote"].drop_duplicates()
    escolhidos = ids.sample(n=min(n, len(ids)), random_state=random_state)
    return lotes[lotes["lote"].isin(escolhidos)]


def lote_em_pico(lote: pd.DataFrame) -> bool:
    """O lote usa a velocidade de pico se a maioria dos pedidos foi feita no pico."""
    return bool((lote["horario_pico"] == "sim").mean() >= 0.5)


def avaliar_lote(
    lote: pd.DataFrame,
    hubs: pd.DataFrame,
    capacidade: int = CAPACIDADE_PADRAO,
    penalidade_km_por_min: float = PENALIDADE_KM_POR_MIN,
    considerar_espera: bool = False,
    metodos: list[str] | None = None,
) -> list:
    """Roda os métodos em um lote; devolve a lista de ResultadoRotas (com o prazo usado em cada um).

    Com `considerar_espera`, os métodos em lote descontam do prazo a espera até o despacho;
    o método individual sai na hora (sem espera).
    """
    metodos = metodos or ORDEM_METODOS
    hub = tuple(hubs.loc[lote["cidade_hub"].iloc[0]])
    matriz = matriz_distancias_km(np.r_[hub[0], lote["lat_destino"].to_numpy()],
                                  np.r_[hub[1], lote["lon_destino"].to_numpy()])
    pico = lote_em_pico(lote)
    prazo = lote["prazo_prometido_min"].to_numpy(dtype=float)
    prazo_lote = prazo - lote["espera_min"].to_numpy() if considerar_espera else prazo

    resultados = []
    for metodo in metodos:
        if metodo == "individual":
            r, prazo_ref = rotas_individuais(matriz, pico), prazo
        elif metodo == "vizinho mais próximo":
            r, prazo_ref = rotas_vizinho_mais_proximo(matriz, pico, capacidade), prazo_lote
        elif metodo == "OR-Tools":
            r, prazo_ref = rotas_ortools(matriz, pico, capacidade), prazo_lote
        elif metodo == "OR-Tools com prazo":
            r = rotas_ortools(matriz, pico, capacidade, prazos_min=prazo_lote,
                              penalidade_km_por_min=penalidade_km_por_min)
            prazo_ref = prazo_lote
        else:
            raise ValueError(f"Método desconhecido: {metodo}")
        r.prazos_min = prazo_ref
        resultados.append(r)
    return resultados


def avaliar_lotes(lotes: pd.DataFrame, capacidade: int = CAPACIDADE_PADRAO,
                  penalidade_km_por_min: float = PENALIDADE_KM_POR_MIN, considerar_espera: bool = False,
                  metodos: list[str] | None = None) -> pd.DataFrame:
    """Uma linha por lote x método: km, viagens, entregas no prazo e minutos de atraso."""
    hubs = hubs_por_cidade()
    linhas = []
    for id_lote, lote in lotes.groupby("lote"):
        for r in avaliar_lote(lote, hubs, capacidade, penalidade_km_por_min, considerar_espera, metodos):
            atraso = np.clip(r.chegada_min - r.prazos_min, 0, None)
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
