"""Página Mapa: bairros de destino no mapa, coloridos pelo indicador escolhido."""

import streamlit as st

from logistica_rotas.dashboard.dados import aplicar_filtros, obter_dados
import pandas as pd

from logistica_rotas.dashboard.estilo import cabecalho, formatar, titulo_cartao
from logistica_rotas.dashboard.graficos import CONFIG_PLOTLY, mapa_bairros
from logistica_rotas.ingestao.leitura import SIGLA_CIDADE
from logistica_rotas.visualizacao.mapas import indicadores_por_bairro

METRICAS = {
    "Taxa de atraso": ("atraso_pct", "Atraso", "%"),
    "Entregas": ("entregas", "Entregas", ""),
    "Tempo mediano": ("tempo_mediano_min", "Tempo", " min"),
}
MIN_ENTREGAS = 10  # bairros com menos entregas no filtro ficam de fora (percentual instável)

dados = obter_dados()
df = aplicar_filtros(dados, st.session_state["_filtros"])

cabecalho("Mapa", "Bairros de destino: onde as entregas se concentram e onde atrasam.")
if df.empty:
    st.warning("Nenhuma entrega com os filtros selecionados. Ajuste os filtros ou use \"Limpar filtros\".")
    st.stop()

tabela = indicadores_por_bairro(df)
tabela = tabela[tabela["entregas"] >= MIN_ENTREGAS]
if tabela.empty:
    st.info(f"Nenhum bairro com pelo menos {MIN_ENTREGAS} entregas concluídas nos filtros atuais.")
    st.stop()

escolha = st.segmented_control("Colorir por", list(METRICAS), default="Taxa de atraso", key="mapa_metrica") \
    or "Taxa de atraso"
coluna, rotulo, sufixo = METRICAS[escolha]

with st.container(key="card_mapa"):
    titulo_cartao(f"{escolha} por bairro de destino",
                  f"Tamanho do círculo = entregas. Bairros com menos de {MIN_ENTREGAS} entregas concluídas ficam de fora. "
                  "Passe o mouse para ver os números.")
    st.plotly_chart(mapa_bairros(tabela, coluna, rotulo, sufixo), width="stretch",
                    config={"displayModeBar": False, "scrollZoom": True})
    st.caption("Mapa: © colaboradores do OpenStreetMap, © CARTO. Utinga (SA) e Barão de Mauá (Mauá) têm posição "
               "simulada: não foram encontrados como área de bairro no OpenStreetMap.")

col_a, col_b = st.columns(2, gap="medium")
tabela["local"] = tabela["bairro"] + " · " + tabela["cidade"].map(SIGLA_CIDADE)
colunas = {"local": "Bairro", "entregas": "Entregas", "atraso_pct": "Atraso (%)", "tempo_mediano_min": "Tempo (min)"}


def _tabela_br(parte: pd.DataFrame) -> pd.DataFrame:
    """Top-8 com números no padrão brasileiro (vírgula decimal)."""
    saida = parte[list(colunas)].rename(columns=colunas)
    saida["Atraso (%)"] = parte["atraso_pct"].map(lambda v: formatar(v, 1)).to_numpy()
    saida["Tempo (min)"] = parte["tempo_mediano_min"].map(lambda v: formatar(v, 1)).to_numpy()
    return saida
with col_a:
    with st.container(key="card_mapa_pior"):
        titulo_cartao("Maior taxa de atraso", "Com 50 a 150 entregas por bairro, diferenças de 1 a 2 pontos são ruído.")
        st.dataframe(_tabela_br(tabela.nlargest(8, "atraso_pct")), hide_index=True, width="stretch")
with col_b:
    with st.container(key="card_mapa_volume"):
        maior = tabela.loc[tabela["entregas"].idxmax()]
        titulo_cartao("Maior volume",
                      f"Líder: {maior['bairro']} · {maior['cidade']} ({formatar(maior['entregas'], 0)} entregas).")
        st.dataframe(_tabela_br(tabela.nlargest(8, "entregas")), hide_index=True, width="stretch")
