"""Roteirização de lotes de entregas a partir de um hub.

Cenário (simulado): cada cidade tem um hub no Centro. Os pedidos coletados na
cidade são despachados em lotes (janela de tempo). Cada moto leva até
`capacidade` pedidos por viagem, sai do hub e volta ao hub.

Métodos comparados:
- individual: uma viagem de ida e volta por pedido (operação atual);
- vizinho mais próximo: heurística gulosa, com capacidade;
- OR-Tools (CVRP): minimiza a distância total, com capacidade;
- OR-Tools com prazo: minimiza distância + penalidade por minuto de atraso
  em relação ao prazo prometido (janela de tempo "suave").

Tempo de chegada (determinístico, para comparar métodos de forma justa):
distância / velocidade (normal ou pico) + TEMPO_PARADA_MIN por entrega anterior.
Distância = haversine x fator de tortuosidade (mesma regra da simulação).
"""

from dataclasses import dataclass

import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from logistica_rotas.ingestao.simulacao import (
    FATOR_TORTUOSIDADE,
    VELOCIDADE_NORMAL_KMH,
    VELOCIDADE_PICO_KMH,
    haversine_km,
)

CAPACIDADE_PADRAO = 4
TEMPO_PARADA_MIN = 3.0          # estacionar, entregar e voltar à moto
ESCALA = 1000                   # OR-Tools trabalha com inteiros: km -> metros, min -> milésimos
PENALIDADE_ATRASO_POR_MIN = 2_000  # em metros equivalentes: 1 min de atraso "custa" 2 km
TEMPO_LIMITE_S = 0.2


@dataclass
class ResultadoRotas:
    """Rotas (listas de índices de pedidos, base 1 = primeiro pedido) e indicadores."""

    metodo: str
    rotas: list[list[int]]
    km_total: float
    chegada_min: np.ndarray        # tempo de chegada de cada pedido (ordem original)


def matriz_distancias_km(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Matriz de distâncias (km pelas ruas, estimada) entre todos os pontos."""
    lat1, lat2 = np.meshgrid(lats, lats, indexing="ij")
    lon1, lon2 = np.meshgrid(lons, lons, indexing="ij")
    return haversine_km(lat1, lon1, lat2, lon2) * FATOR_TORTUOSIDADE


def velocidade_kmh(pico: bool) -> float:
    return VELOCIDADE_PICO_KMH if pico else VELOCIDADE_NORMAL_KMH


def avaliar_rotas(rotas: list[list[int]], matriz: np.ndarray, pico: bool) -> tuple[float, np.ndarray]:
    """Km total (com retorno ao hub) e minuto de chegada de cada pedido."""
    v = velocidade_kmh(pico)
    chegada = np.full(matriz.shape[0] - 1, np.nan)
    km_total = 0.0
    for rota in rotas:
        atual, km, paradas = 0, 0.0, 0
        for no in rota:
            km += matriz[atual, no]
            chegada[no - 1] = km / v * 60 + paradas * TEMPO_PARADA_MIN
            paradas += 1
            atual = no
        km_total += km + matriz[atual, 0]
    return km_total, chegada


def rotas_individuais(matriz: np.ndarray, pico: bool) -> ResultadoRotas:
    """Uma viagem por pedido (ida e volta)."""
    rotas = [[i] for i in range(1, matriz.shape[0])]
    km, chegada = avaliar_rotas(rotas, matriz, pico)
    return ResultadoRotas("individual", rotas, km, chegada)


def rotas_vizinho_mais_proximo(matriz: np.ndarray, pico: bool, capacidade: int = CAPACIDADE_PADRAO) -> ResultadoRotas:
    """Heurística gulosa: sai do hub e vai sempre ao pedido mais próximo; volta ao hub ao lotar."""
    pendentes = set(range(1, matriz.shape[0]))
    rotas = []
    while pendentes:
        atual, rota = 0, []
        while pendentes and len(rota) < capacidade:
            proximo = min(pendentes, key=lambda j: matriz[atual, j])
            rota.append(proximo)
            pendentes.remove(proximo)
            atual = proximo
        rotas.append(rota)
    km, chegada = avaliar_rotas(rotas, matriz, pico)
    return ResultadoRotas("vizinho mais próximo", rotas, km, chegada)


def rotas_ortools(
    matriz: np.ndarray,
    pico: bool,
    capacidade: int = CAPACIDADE_PADRAO,
    prazos_min: np.ndarray | None = None,
    tempo_limite_s: float = TEMPO_LIMITE_S,
) -> ResultadoRotas:
    """CVRP com OR-Tools. Com `prazos_min`, penaliza cada minuto de chegada após o prazo."""
    n = matriz.shape[0]
    n_motos = int(np.ceil((n - 1) / capacidade))
    if prazos_min is not None:
        n_motos = n - 1  # permite mandar sozinho o pedido que não cabe no prazo
    gerente = pywrapcp.RoutingIndexManager(n, n_motos, 0)
    modelo = pywrapcp.RoutingModel(gerente)

    dist_m = np.rint(matriz * ESCALA).astype(int)
    cb_dist = modelo.RegisterTransitCallback(
        lambda i, j: int(dist_m[gerente.IndexToNode(i), gerente.IndexToNode(j)])
    )
    modelo.SetArcCostEvaluatorOfAllVehicles(cb_dist)

    demanda = [0] + [1] * (n - 1)
    cb_dem = modelo.RegisterUnaryTransitCallback(lambda i: demanda[gerente.IndexToNode(i)])
    modelo.AddDimensionWithVehicleCapacity(cb_dem, 0, [capacidade] * n_motos, True, "Carga")

    if prazos_min is not None:
        v = velocidade_kmh(pico)
        # tempo de i até j = deslocamento + parada em i (se i não for o hub), em milésimos de minuto
        tempo = (matriz / v * 60 * ESCALA).astype(int)
        tempo[1:, :] += int(TEMPO_PARADA_MIN * ESCALA)
        cb_tempo = modelo.RegisterTransitCallback(
            lambda i, j: int(tempo[gerente.IndexToNode(i), gerente.IndexToNode(j)])
        )
        modelo.AddDimension(cb_tempo, 0, 10_000 * ESCALA, True, "Tempo")
        dim_tempo = modelo.GetDimensionOrDie("Tempo")
        coef = max(1, PENALIDADE_ATRASO_POR_MIN // ESCALA)  # custo por milésimo de minuto
        for no in range(1, n):
            dim_tempo.SetCumulVarSoftUpperBound(gerente.NodeToIndex(no), int(prazos_min[no - 1] * ESCALA), coef)

    parametros = pywrapcp.DefaultRoutingSearchParameters()
    parametros.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parametros.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    parametros.time_limit.FromMilliseconds(int(tempo_limite_s * 1000))
    solucao = modelo.SolveWithParameters(parametros)
    if solucao is None:
        raise RuntimeError("OR-Tools não encontrou solução")

    rotas = []
    for moto in range(n_motos):
        indice, rota = modelo.Start(moto), []
        indice = solucao.Value(modelo.NextVar(indice))
        while not modelo.IsEnd(indice):
            rota.append(gerente.IndexToNode(indice))
            indice = solucao.Value(modelo.NextVar(indice))
        if rota:
            rotas.append(rota)
    km, chegada = avaliar_rotas(rotas, matriz, pico)
    nome = "OR-Tools com prazo" if prazos_min is not None else "OR-Tools"
    return ResultadoRotas(nome, rotas, km, chegada)


def comparar_metodos(
    hub: tuple[float, float],
    lats: np.ndarray,
    lons: np.ndarray,
    prazos_min: np.ndarray,
    pico: bool,
    capacidade: int = CAPACIDADE_PADRAO,
) -> list[ResultadoRotas]:
    """Roda os 4 métodos para um lote (hub + destinos)."""
    matriz = matriz_distancias_km(np.r_[hub[0], lats], np.r_[hub[1], lons])
    return [
        rotas_individuais(matriz, pico),
        rotas_vizinho_mais_proximo(matriz, pico, capacidade),
        rotas_ortools(matriz, pico, capacidade),
        rotas_ortools(matriz, pico, capacidade, prazos_min=np.asarray(prazos_min, dtype=float)),
    ]
