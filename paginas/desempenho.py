"""Página Desempenho: onde e por que o prazo falha (hora, distância x trajeto, faixas)."""

import streamlit as st

from logistica_rotas.dashboard.dados import aplicar_filtros, obter_dados
from logistica_rotas.dashboard.estilo import cabecalho, titulo_cartao
from logistica_rotas.dashboard.graficos import (
    CONFIG_PLOTLY, grafico_atraso_hora, grafico_faixas, grafico_otd_faixa_trajeto,
)

dados = obter_dados()
df = aplicar_filtros(dados, st.session_state["_filtros"])

cabecalho("Desempenho", "Onde e por que o prazo falha: horário, distância e tipo de trajeto.")
if df.empty:
    st.warning("Nenhuma entrega com os filtros selecionados. Ajuste os filtros ou use \"Limpar filtros\".")
    st.stop()

with st.container(key="card_faixa_trajeto"):
    titulo_cartao(
        "Na mesma faixa de distância, cruzar a divisa quase não muda o prazo",
        "OTD por faixa de distância: entregas entre cidades atrasam por serem mais longas, não por mudarem de "
        "cidade (notebook 03). Faixas com menos de 30 entregas não aparecem.",
    )
    st.plotly_chart(grafico_otd_faixa_trajeto(df), width="stretch", config=CONFIG_PLOTLY)

col_a, col_b = st.columns(2, gap="medium")
with col_a:
    with st.container(key="card_hora"):
        titulo_cartao("Taxa de atraso por hora do pedido",
                      "Faixas em amarelo: picos de trânsito (7h-8h e 17h-19h em dias úteis).")
        st.plotly_chart(grafico_atraso_hora(df), width="stretch", config=CONFIG_PLOTLY)
with col_b:
    with st.container(key="card_faixas"):
        titulo_cartao("Entregas por faixa de distância", "Distância estimada (linha reta x 1,3), não a rota real.")
        st.plotly_chart(grafico_faixas(df), width="stretch", config=CONFIG_PLOTLY)
