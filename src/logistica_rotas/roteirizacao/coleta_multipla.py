"""Despacho dinâmico com várias coletas na mesma viagem (pickup and delivery).

Diferença para `despacho.py`: não há hub. Cada pedido tem o seu ponto de coleta real
(`lat_origem`, `lon_origem`, o restaurante) e o seu destino. Uma moto pode pegar pedidos
em restaurantes diferentes e entregá-los em qualquer ordem, desde que cada pedido seja
coletado antes de ser entregue.

Regras (por cidade de origem; uma moto "aberta" por vez em cada cidade):
- Pedido chega e há moto aberta: entra se existir uma sequência de coletas/entregas em que
  todos cumprem o prazo (menos a margem) saindo agora **e** se o caminho conjunto for mais curto
  que a moto aberta + a viagem individual do pedido (sem hub, juntar pode alongar o caminho).
  Senão, a moto aberta sai e o pedido abre outra.
- A moto sai quando lota (`capacidade`, no máximo 3), atinge a espera máxima ou chega o último
  minuto que cumpre todos os prazos.
- Sequência: força bruta sobre todas as ordens válidas (coleta antes da entrega):
  2 pedidos = 6 ordens, 3 pedidos = 90.
- Km = caminho da primeira coleta até a última entrega (caminho aberto). O deslocamento vazio
  até o primeiro restaurante não entra - nem aqui nem nas viagens individuais.
- Cada parada (coleta ou entrega) custa TEMPO_PARADA_MIN. O tempo de preparo do pedido não é modelado.
"""

from functools import lru_cache

import numpy as np
import pandas as pd

from logistica_rotas.ingestao.simulacao import FATOR_TORTUOSIDADE, haversine_km
from logistica_rotas.roteirizacao.despacho import SIGMA_EXECUCAO, fator_por_distancia
from logistica_rotas.roteirizacao.rotas import TEMPO_PARADA_MIN, velocidade_kmh

CAPACIDADE_MAXIMA = 3


@lru_cache(maxsize=None)
def sequencias_validas(k: int) -> tuple[tuple[tuple[int, str], ...], ...]:
    """Todas as ordens de 2k paradas (pedido, 'c'/'e') com a coleta de cada pedido antes da entrega."""
    resultado = []

    def montar(seq, coletados, entregues):
        if len(seq) == 2 * k:
            resultado.append(tuple(seq))
            return
        for j in range(k):
            if j not in coletados:
                montar(seq + [(j, "c")], coletados | {j}, entregues)
            elif j not in entregues:
                montar(seq + [(j, "e")], coletados, entregues | {j})

    montar([], frozenset(), frozenset())
    return tuple(resultado)


def _planejar(origens: np.ndarray, destinos: np.ndarray, prazos_abs: np.ndarray, pico: bool,
              t_saida: float, margem: float, fator: float | str) -> tuple[dict, dict]:
    """Melhor plano viável para sair em `t_saida` (menor km) e o plano de maior folga."""
    k = len(origens)
    pontos = np.vstack([origens, destinos])  # índices: coleta j = j, entrega j = k + j
    reta = haversine_km(pontos[:, None, 0], pontos[:, None, 1], pontos[None, :, 0], pontos[None, :, 1])
    dist = reta * (fator_por_distancia(reta) if fator == "osrm" else fator)
    v = velocidade_kmh(pico)
    melhor_km, maior_folga = None, None
    for seq in sequencias_validas(k):
        nos = [j if tipo == "c" else k + j for j, tipo in seq]
        trechos = np.array([0.0] + [dist[a, b] for a, b in zip(nos[:-1], nos[1:])])
        tempo = np.cumsum(trechos) / v * 60 + np.arange(len(nos)) * TEMPO_PARADA_MIN
        chegada = np.empty(k)
        for pos, (j, tipo) in enumerate(seq):
            if tipo == "e":
                chegada[j] = tempo[pos]
        plano = {"km": float(trechos.sum()), "chegada_rel": chegada,
                 "folga_saida": float(np.min(prazos_abs - margem - chegada))}
        if maior_folga is None or plano["folga_saida"] > maior_folga["folga_saida"]:
            maior_folga = plano
        if plano["folga_saida"] >= t_saida and (melhor_km is None or plano["km"] < melhor_km["km"]):
            melhor_km = plano
    return (melhor_km or maior_folga), maior_folga


def simular_coleta_multipla(df: pd.DataFrame, espera_max_min: float, capacidade: int = 2, margem_min: float = 5.0,
                            espera_max_pico_min: float | None = 0.0, fator: float | str = FATOR_TORTUOSIDADE,
                            random_state: int = 42) -> pd.DataFrame:
    """Simula o despacho com coletas em restaurantes diferentes; uma linha por entrega."""
    if capacidade > CAPACIDADE_MAXIMA:
        raise ValueError(f"capacidade máxima suportada: {CAPACIDADE_MAXIMA}")
    base = df[df["status"] != "cancelado"].sort_values("data_hora_pedido")
    inicio = base["data_hora_pedido"].min()
    t_pedido = ((base["data_hora_pedido"] - inicio).dt.total_seconds() / 60).to_numpy()
    prazo_abs = t_pedido + base["prazo_prometido_min"].to_numpy(dtype=float)
    origens = base[["lat_origem", "lon_origem"]].to_numpy()
    destinos = base[["lat_destino", "lon_destino"]].to_numpy()
    pico = (base["horario_pico"] == "sim").to_numpy()
    cidade = base["cidade_origem"].astype(str).to_numpy()
    espera_pedido = np.full(len(base), float(espera_max_min))
    if espera_max_pico_min is not None:
        espera_pedido[pico] = float(espera_max_pico_min)

    saida = np.full(len(base), np.nan)
    chegada_plan = np.full(len(base), np.nan)
    viagem = np.full(len(base), -1)
    km_viagem: list[float] = []

    def planejar(itens: list[int], t: float) -> tuple[dict, dict]:
        return _planejar(origens[itens], destinos[itens], prazo_abs[itens], bool(pico[itens[0]]), t, margem_min, fator)

    def despachar(itens: list[int], t: float) -> None:
        plano, _ = planejar(itens, t)
        km_viagem.append(plano["km"])
        for pos, i in enumerate(itens):
            saida[i], chegada_plan[i], viagem[i] = t, t + plano["chegada_rel"][pos], len(km_viagem) - 1

    for nome_cidade in np.unique(cidade):
        aberta: list[int] = []
        limite = t_abertura = espera_aberta = 0.0
        for i in np.flatnonzero(cidade == nome_cidade):
            t = t_pedido[i]
            if aberta and limite < t:
                despachar(aberta, limite)
                aberta = []
            if aberta:
                candidata = aberta + [i]
                if len(candidata) <= capacidade:
                    melhor, folga = planejar(candidata, t)
                    separado = planejar(aberta, t)[0]["km"] + planejar([i], t)[0]["km"]
                    if folga["folga_saida"] >= t and melhor["folga_saida"] >= t and melhor["km"] < separado:
                        aberta = candidata
                        limite = min(t_abertura + espera_aberta, folga["folga_saida"])
                        if len(aberta) == capacidade:
                            despachar(aberta, t)
                            aberta = []
                        continue
                despachar(aberta, t)
            aberta, t_abertura, espera_aberta = [i], t, espera_pedido[i]
            _, folga = planejar(aberta, t)
            limite = max(t, min(t + espera_aberta, folga["folga_saida"]))
            if capacidade == 1:
                despachar(aberta, t)
                aberta = []
        if aberta:
            despachar(aberta, limite)

    rng = np.random.default_rng(random_state)
    fator_exec = rng.lognormal(0.0, SIGMA_EXECUCAO, size=len(km_viagem))
    chegada_real = saida + (chegada_plan - saida) * fator_exec[viagem]
    km = np.array(km_viagem)
    return pd.DataFrame({
        "id_pedido": base["id_pedido"].to_numpy(),
        "cidade_hub": cidade,
        "pico": pico,
        "viagem": viagem,
        "km_viagem": km[viagem],
        "espera_min": saida - t_pedido,
        "chegada_plan_min": chegada_plan - t_pedido,
        "chegada_real_min": chegada_real - t_pedido,
        "prazo_min": base["prazo_prometido_min"].to_numpy(),
    })
