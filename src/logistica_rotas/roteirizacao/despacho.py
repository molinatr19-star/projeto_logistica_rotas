"""Simulação de despacho dinâmico: a moto espera outros pedidos só enquanto o prazo permite.

Regras (por hub = Centro de cada cidade; uma moto "aberta" por vez em cada hub):
- Pedido chega e há moto aberta: entra se, com ele, existir uma ordem de visita em que
  todos os pedidos ainda podem cumprir o prazo (menos a `margem_min`) saindo agora.
  Se não couber, a moto aberta sai na hora e o pedido abre outra.
- A moto aberta sai quando: lotar (`capacidade`), atingir `espera_max_min` desde que abriu,
  ou chegar o último minuto que ainda cumpre o prazo de todos - o que vier primeiro.
- Rota: com até `capacidade` paradas testamos todas as ordens (força bruta) e ficamos com
  a de menor km entre as que cumprem o prazo; se nenhuma cumpre, a de maior folga.
- Planejamento usa tempo médio (velocidade normal ou de pico + 3 min por parada).
  Execução: cada viagem recebe um fator aleatório de tempo (lognormal, sigma `SIGMA_EXECUCAO`)
  para medir o prazo "com variação" - o que aconteceria na rua.

`espera_max_min=0` e `capacidade=1` reproduzem a operação individual (sai na hora, um pedido).

Variações:
- `fator`: fator de tortuosidade (número) ou "osrm" para o fator calibrado por distância.
- `espera_max_pico_min`: espera máxima diferente para pedidos feitos no pico (ex.: 0 = não esperar no pico).
- `ponto_coleta="bairro"`: em vez de um hub por cidade, cada bairro de origem é um ponto de coleta
  (restaurantes agrupados no bairro). Só pedidos do mesmo bairro de origem podem dividir a moto.
"""

from dataclasses import dataclass
from itertools import permutations

import numpy as np
import pandas as pd

from logistica_rotas.ingestao.simulacao import BAIRROS, FATOR_TORTUOSIDADE, haversine_km
from logistica_rotas.roteirizacao.lotes import hubs_por_cidade
from logistica_rotas.roteirizacao.rotas import TEMPO_PARADA_MIN, velocidade_kmh

SIGMA_EXECUCAO = 0.25


@dataclass
class _Plano:
    ordem: tuple[int, ...]
    km: float
    chegada_rel: np.ndarray   # minutos após a saída, na ordem de `ordem`
    folga_saida: float        # último minuto (absoluto) de saída que cumpre todos os prazos


def fator_por_distancia(reta_km: np.ndarray) -> np.ndarray:
    """Fator de tortuosidade calibrado com o OSRM (notebook 09): maior em trechos curtos.

    Ajuste simples aos fatores medianos por faixa: 1,31 + 0,40 / distância em linha reta (km).
    """
    return 1.31 + 0.40 / np.maximum(reta_km, 0.3)


def _planejar(pontos: np.ndarray, hub: np.ndarray, prazos_abs: np.ndarray, pico: bool,
              t_saida: float, margem: float, fator: float | str = FATOR_TORTUOSIDADE) -> tuple[_Plano, _Plano]:
    """Melhor plano para sair em `t_saida` (menor km viável) e o plano de maior folga."""
    v = velocidade_kmh(pico)
    todos = np.vstack([hub, pontos])
    reta = haversine_km(todos[:, None, 0], todos[:, None, 1], todos[None, :, 0], todos[None, :, 1])
    dist = reta * (fator_por_distancia(reta) if fator == "osrm" else fator)
    melhor_km, maior_folga = None, None
    for ordem in permutations(range(len(pontos))):
        nos = [0] + [i + 1 for i in ordem]
        trechos = np.array([dist[a, b] for a, b in zip(nos[:-1], nos[1:])])
        chegada = np.cumsum(trechos) / v * 60 + np.arange(len(ordem)) * TEMPO_PARADA_MIN
        km = trechos.sum() + dist[nos[-1], 0]
        folga = float(np.min(prazos_abs[list(ordem)] - margem - chegada))
        plano = _Plano(ordem, km, chegada, folga)
        if maior_folga is None or folga > maior_folga.folga_saida:
            maior_folga = plano
        if folga >= t_saida and (melhor_km is None or km < melhor_km.km):
            melhor_km = plano
    return (melhor_km or maior_folga), maior_folga


def simular_despacho(df: pd.DataFrame, espera_max_min: float, capacidade: int = 4, margem_min: float = 0.0,
                     random_state: int = 42, espera_max_pico_min: float | None = None,
                     ponto_coleta: str = "hub", fator: float | str = FATOR_TORTUOSIDADE) -> pd.DataFrame:
    """Simula o despacho; devolve uma linha por entrega com viagem, espera e chegadas planejada e real."""
    base = df[df["status"] != "cancelado"].sort_values("data_hora_pedido")
    inicio = base["data_hora_pedido"].min()
    t_pedido = ((base["data_hora_pedido"] - inicio).dt.total_seconds() / 60).to_numpy()
    prazo_abs = t_pedido + base["prazo_prometido_min"].to_numpy(dtype=float)
    pontos = base[["lat_destino", "lon_destino"]].to_numpy()
    pico = (base["horario_pico"] == "sim").to_numpy()
    cidade = base["cidade_origem"].astype(str).to_numpy()
    if ponto_coleta == "hub":
        grupo = cidade
        coords = hubs_por_cidade()
        origem_grupo = {c: coords.loc[c].to_numpy() for c in np.unique(cidade)}
    elif ponto_coleta == "bairro":
        grupo = (base["cidade_origem"].astype(str) + " | " + base["bairro_origem"].astype(str)).to_numpy()
        centros = BAIRROS.assign(chave=BAIRROS["cidade"] + " | " + BAIRROS["bairro"]).set_index("chave")
        origem_grupo = {g: centros.loc[g, ["lat", "lon"]].to_numpy(dtype=float) for g in np.unique(grupo)}
    else:
        raise ValueError("ponto_coleta deve ser 'hub' ou 'bairro'")
    espera_pedido = np.full(len(base), float(espera_max_min))
    if espera_max_pico_min is not None:
        espera_pedido[pico] = float(espera_max_pico_min)
    rng = np.random.default_rng(random_state)

    saida = np.full(len(base), np.nan)
    chegada_plan = np.full(len(base), np.nan)
    viagem = np.full(len(base), -1)
    km_viagem: list[float] = []

    def despachar(itens: list[int], t: float, hub: np.ndarray) -> None:
        plano, _ = _planejar(pontos[itens], hub, prazo_abs[itens], bool(pico[itens[0]]), t, margem_min, fator)
        id_viagem = len(km_viagem)
        km_viagem.append(plano.km)
        for pos, k in enumerate(plano.ordem):
            i = itens[k]
            saida[i], chegada_plan[i], viagem[i] = t, t + plano.chegada_rel[pos], id_viagem

    for nome_grupo in np.unique(grupo):
        hub = origem_grupo[nome_grupo]
        aberta: list[int] = []
        limite = 0.0  # minuto em que a moto aberta sai, se nada mudar
        espera_aberta = 0.0
        for i in np.flatnonzero(grupo == nome_grupo):
            t = t_pedido[i]
            if aberta and limite < t:
                despachar(aberta, limite, hub)
                aberta = []
            if aberta:
                candidata = aberta + [i]
                _, folga = _planejar(pontos[candidata], hub, prazo_abs[candidata], bool(pico[candidata[0]]), t,
                                     margem_min, fator)
                if len(candidata) <= capacidade and folga.folga_saida >= t:
                    aberta = candidata
                    limite = min(t_abertura + espera_aberta, folga.folga_saida)
                    if len(aberta) == capacidade:
                        despachar(aberta, t, hub)
                        aberta = []
                    continue
                despachar(aberta, t, hub)  # pedido não cabe: a moto aberta sai agora
            aberta, t_abertura, espera_aberta = [i], t, espera_pedido[i]
            _, folga = _planejar(pontos[aberta], hub, prazo_abs[aberta], bool(pico[i]), t, margem_min, fator)
            limite = max(t, min(t + espera_aberta, folga.folga_saida))
            if capacidade == 1:
                despachar(aberta, t, hub)
                aberta = []
        if aberta:
            despachar(aberta, limite, hub)

    # Execução com variação: um fator de tempo por viagem (trânsito do momento).
    fator = rng.lognormal(0.0, SIGMA_EXECUCAO, size=len(km_viagem))
    chegada_real = saida + (chegada_plan - saida) * fator[viagem]
    km = np.array(km_viagem)
    return pd.DataFrame({
        "id_pedido": base["id_pedido"].to_numpy(),
        "cidade_hub": cidade,
        "ponto_coleta": grupo,
        "pico": pico,
        "viagem": viagem,
        "km_viagem": km[viagem],
        "espera_min": saida - t_pedido,
        "chegada_plan_min": chegada_plan - t_pedido,
        "chegada_real_min": chegada_real - t_pedido,
        "prazo_min": base["prazo_prometido_min"].to_numpy(),
    })


def resumo_despacho(entregas: pd.DataFrame, km_individual: float | None = None) -> pd.Series:
    """Indicadores de uma simulação. `km_individual` permite calcular a economia."""
    viagens = entregas.drop_duplicates("viagem")
    km = float(viagens["km_viagem"].sum())
    r = {
        "entregas": len(entregas),
        "viagens": len(viagens),
        "entregas_por_viagem": len(entregas) / len(viagens),
        "km": km,
        "espera_media_min": entregas["espera_min"].mean(),
        "no_prazo_plan_pct": (entregas["chegada_plan_min"] <= entregas["prazo_min"] + 1e-9).mean() * 100,
        "no_prazo_real_pct": (entregas["chegada_real_min"] <= entregas["prazo_min"]).mean() * 100,
    }
    if km_individual:
        r["economia_km_pct"] = (1 - km / km_individual) * 100
    return pd.Series(r)


ESPERAS = [0, 2, 5, 10, 15]
MARGENS = [0, 5]
VOLUMES = {"atual (5.000 pedidos)": 5_000, "4x (20.000 pedidos)": 20_000}


def rodar_cenarios(df: pd.DataFrame, esperas: list[float] = ESPERAS, margens: list[float] = MARGENS,
                   volumes: dict[str, int] = VOLUMES, capacidade: int = 4) -> pd.DataFrame:
    """Grade de cenários (volume x margem x espera máxima), cada um comparado com o individual do mesmo volume."""
    from logistica_rotas.ingestao.simulacao import gerar_entregas

    linhas = []
    for rotulo, n in volumes.items():
        base = df if n == len(df) else gerar_entregas(n=n)
        individual = resumo_despacho(simular_despacho(base, 0, capacidade=1))
        linhas.append({**individual.to_dict(), "economia_km_pct": 0.0, "volume": rotulo, "politica": "individual",
                       "espera_max_min": 0.0, "margem_min": 0.0})
        for margem in margens:
            for espera in esperas:
                r = resumo_despacho(simular_despacho(base, espera, capacidade, margem), individual["km"])
                linhas.append({**r.to_dict(), "volume": rotulo, "politica": "dinâmico",
                               "espera_max_min": float(espera), "margem_min": float(margem)})
    return pd.DataFrame(linhas)
