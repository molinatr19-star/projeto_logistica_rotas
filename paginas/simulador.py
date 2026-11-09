"""Página Simulador de despacho: quanto agrupar pedidos economiza e quanto custa em prazo."""

import pandas as pd
import streamlit as st

from logistica_rotas.dashboard.dados import obter_dados
from logistica_rotas.dashboard.estilo import (
    NEON_AMARELO, NEON_AZUL, NEON_CIANO, NEON_VERDE, cabecalho, cartao_kpi, formatar, titulo_cartao,
)
from logistica_rotas.dashboard.graficos import CONFIG_PLOTLY, curva_simulador
from logistica_rotas.ingestao.simulacao import gerar_entregas
from logistica_rotas.roteirizacao.despacho import resumo_despacho, simular_despacho

ESPERAS_CURVA = [0, 2, 5, 10, 15]
VOLUMES = {"Atual (5.000 pedidos)": None, "4x (20.000 pedidos)": 20_000}
COLETAS = {"Hub por cidade": "hub", "Coleta no bairro": "bairro"}


@st.cache_data(show_spinner=False)
def base_volume(volume: str) -> pd.DataFrame:
    n = VOLUMES[volume]
    return obter_dados() if n is None else gerar_entregas(n=n)


@st.cache_data(show_spinner=False)
def simular(volume: str, coleta: str, espera: float, margem: float, esperar_no_pico: bool, capacidade: int = 4) -> dict:
    """Resumo de uma simulação (em cache: o mesmo cenário não roda duas vezes)."""
    base = base_volume(volume)
    entregas = simular_despacho(base, espera, capacidade, margem, ponto_coleta=COLETAS[coleta],
                                espera_max_pico_min=None if esperar_no_pico else 0)
    return resumo_despacho(entregas).to_dict()


cabecalho("Simulador de despacho", "Agrupar pedidos na mesma moto: quanto economiza em km e quanto custa em prazo.")
st.markdown(
    "A moto espera outros pedidos **só enquanto o prazo de todos permite** (menos a margem de segurança). "
    "O prazo \"com variação\" sorteia o tempo de cada viagem, como o trânsito real. "
    "Os filtros da barra lateral **não** se aplicam aqui: o simulador usa toda a operação. "
    "Detalhes nos notebooks 07, 08 e 10."
)

with st.container(key="card_controles"):
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        espera = st.slider("Espera máxima (min)", 0, 15, 5, 1, key="sim_espera",
                           help="Quanto tempo, no máximo, a moto aguarda outro pedido antes de sair.")
        margem = st.slider("Margem de segurança no prazo (min)", 0, 10, 5, 1, key="sim_margem",
                           help="A regra trata o prazo como se fosse X minutos menor, para absorver o trânsito.")
    with c2:
        esperar_no_pico = st.toggle("Esperar também no pico", value=False, key="sim_pico",
                                    help="Recomendado: não esperar no pico (notebook 08).")
        volume = st.radio("Volume de pedidos", list(VOLUMES), key="sim_volume", horizontal=True)
    with c3:
        coleta = st.radio("Modelo de coleta", list(COLETAS), key="sim_coleta",
                          help="Hub: todos os pedidos da cidade saem do Centro. Bairro: cada bairro é um ponto de coleta.")
        if VOLUMES[volume]:
            st.caption("Volume 4x: a primeira simulação leva alguns segundos; depois fica em cache.")

with st.spinner("Simulando o despacho..."):
    individual = simular(volume, coleta, 0, 0, True, capacidade=1)
    escolhido = simular(volume, coleta, espera, margem, esperar_no_pico)
    curva = pd.DataFrame([{**simular(volume, coleta, w, margem, esperar_no_pico), "espera_max_min": w}
                          for w in sorted(set(ESPERAS_CURVA) | {espera})])

escolhido["economia_km_pct"] = (1 - escolhido["km"] / individual["km"]) * 100
curva["economia_km_pct"] = (1 - curva["km"] / individual["km"]) * 100

perda = individual["no_prazo_real_pct"] - escolhido["no_prazo_real_pct"]
cartoes = [
    cartao_kpi("Economia de km", formatar(escolhido["economia_km_pct"], 1),
               f"{formatar(individual['km'] - escolhido['km'], 0)} km a menos", NEON_VERDE, "%"),
    cartao_kpi("No prazo (rua)", formatar(escolhido["no_prazo_real_pct"], 1),
               f"individual {formatar(individual['no_prazo_real_pct'], 1)}%", NEON_AMARELO if perda > 2 else NEON_AZUL,
               "%", delta=f"{'▼' if perda > 0 else '▲'} {formatar(abs(perda), 1)} p.p. vs individual",
               delta_bom=perda <= 0),
    cartao_kpi("Pedidos por viagem", formatar(escolhido["entregas_por_viagem"], 2),
               f"{formatar(escolhido['viagens'], 0)} viagens", NEON_CIANO),
    cartao_kpi("Espera média", formatar(escolhido["espera_media_min"], 1), "até a moto sair", NEON_AZUL, "min"),
]
for coluna_kpi, html in zip(st.columns(4, gap="small"), cartoes):
    coluna_kpi.markdown(html, unsafe_allow_html=True)

with st.container(key="card_curva"):
    titulo_cartao("Curva de troca: km x prazo",
                  "Cada ponto é uma espera máxima com a margem e a regra de pico escolhidas. O círculo marca o cenário atual.")
    st.plotly_chart(curva_simulador(curva, pd.Series(escolhido), pd.Series(individual)), width="stretch",
                    config=CONFIG_PLOTLY)

st.info(
    "Leitura: com hub por cidade, esperar até 5 min fora do pico (margem de 5 min) economiza cerca de 2% dos km "
    "no volume atual e 6% com 4x, perdendo menos de 2 pontos de prazo. Sem hub (coleta no bairro), quase não há "
    "pedidos para agrupar: a economia fica perto de zero e a espera só custa prazo.",
    icon=":material/lightbulb:",
)
