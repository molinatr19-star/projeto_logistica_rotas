"""Página Visão geral: KPIs com meta e variação, OTD por dia, status e volume por bairro."""

import pandas as pd
import streamlit as st

from logistica_rotas.dashboard.dados import (
    aplicar_filtros, calcular_kpis, obter_dados, periodo_anterior, resumo_bairros,
)
from logistica_rotas.dashboard.estilo import (
    META_OTD_PCT, NEON_AMARELO, NEON_AZUL, NEON_CIANO, NEON_VERDE, NEON_VERMELHO, NEON_VIOLETA, cabecalho,
    cartao_kpi, formatar, titulo_cartao,
)
from logistica_rotas.dashboard.graficos import (
    CONFIG_PLOTLY, grafico_bairros, grafico_otd_por_dia, grafico_status,
)

GLOSSARIO = """
<dl class="glossario">
<dt>OTD (On-Time Delivery)</dt><dd>% de entregas concluídas que chegaram dentro do prazo prometido. Cancelados e tempos com erro de registro ficam fora da conta.</dd>
<dt>Taxa de atraso</dt><dd>% de entregas concluídas que chegaram depois do prazo (= 100% - OTD).</dd>
<dt>Cancelamento</dt><dd>% de todos os pedidos que foram cancelados.</dd>
<dt>Tempo de trânsito</dt><dd>Minutos entre a coleta e a entrega. O cartão mostra a média e, embaixo, a mediana, que é menos afetada por valores extremos.</dd>
<dt>Prazo prometido</dt><dd>12 min + 2,5 min por km, arredondado para cima em múltiplos de 5 (regra da simulação).</dd>
<dt>Pico de trânsito</dt><dd>7h-8h e 17h-19h em dias úteis.</dd>
<dt>Variação "vs anterior"</dt><dd>Linha embaixo de cada cartão: comparação com o período de mesmo tamanho imediatamente antes do selecionado (mesmos demais filtros). Entregas são comparadas por dia. Só aparece quando pelo menos 80% desse período existe nos dados.</dd>
<dt>Distância</dt><dd>Linha reta x 1,3 (a malha viária real é cerca de 37% maior que a linha reta - notebook 09).</dd>
</dl>
"""


def _variacao(atual: float, anterior: float | None, casas: int, sufixo: str, maior_melhor: bool | None,
              pontos: bool = False, prefixo: str = "") -> tuple[str, bool | None]:
    """Texto '▲ 1,2 p.p. vs período anterior' e se a mudança é boa (None = neutra)."""
    if anterior is None or pd.isna(anterior) or pd.isna(atual):
        return "", None
    diff = atual - anterior
    if abs(diff) < 10 ** -casas / 2:
        return "= igual ao anterior", None
    seta = "▲" if diff > 0 else "▼"
    unidade = " p.p." if pontos else sufixo
    bom = None if maior_melhor is None else (diff > 0) == maior_melhor
    return f"{seta} {prefixo}{formatar(abs(diff), casas)}{unidade} vs anterior", bom


dados = obter_dados()
filtros = st.session_state["_filtros"]
df = aplicar_filtros(dados, filtros)

cabecalho("Entregas urbanas de moto", "Visão geral: volume, prazo, tempo de trânsito e cancelamentos.")
if df.empty:
    st.warning("Nenhuma entrega com os filtros selecionados. Ajuste os filtros ou use \"Limpar filtros\".")
    st.stop()

kpi = calcular_kpis(df)
anterior = periodo_anterior(dados, filtros)
ant = calcular_kpis(anterior[0]) if anterior is not None and not anterior[0].empty else {}

# Entregas: compara a média por dia (o período anterior pode ser um pouco mais curto).
dias = (filtros.fim - filtros.inicio).days + 1
por_dia = kpi["total"] / dias
por_dia_ant = ant["total"] / anterior[1] if ant else None
if por_dia_ant:
    mudanca = (por_dia / por_dia_ant - 1) * 100
    d_total = (f"{'▲' if mudanca > 0 else '▼'} {formatar(abs(mudanca), 1)}% por dia vs anterior", None)
else:
    d_total = ("", None)
d_otd = _variacao(kpi["otd_%"], ant.get("otd_%"), 1, "", True, pontos=True)
d_tempo = _variacao(kpi["tempo_medio_min"], ant.get("tempo_medio_min"), 1, " min", False)
d_canc = _variacao(kpi["cancelamento_%"], ant.get("cancelamento_%"), 1, "", False, pontos=True)
d_valor = _variacao(kpi["valor_medio_brl"], ant.get("valor_medio_brl"), 2, "", None, prefixo="R$ ")
acima_meta = kpi["otd_%"] >= META_OTD_PCT

cartoes = [
    cartao_kpi("Entregas", formatar(kpi["total"], 0), f"{formatar(kpi['concluidas'], 0)} concluídas", NEON_AZUL,
               delta=d_total[0], delta_bom=d_total[1]),
    cartao_kpi("No prazo (OTD)", formatar(kpi["otd_%"], 1), f"meta {formatar(META_OTD_PCT, 0)}%",
               NEON_VERDE if acima_meta else NEON_AMARELO, "%",
               "Entregas no prazo / entregas concluídas (cancelados e tempos inválidos fora do cálculo).",
               selo="acima" if acima_meta else "abaixo", selo_bom=acima_meta, delta=d_otd[0], delta_bom=d_otd[1]),
    cartao_kpi("Tempo médio", formatar(kpi["tempo_medio_min"], 1), f"mediana {formatar(kpi['tempo_mediano_min'], 1)} min",
               NEON_CIANO, "min", "Tempo de trânsito das entregas concluídas.", delta=d_tempo[0], delta_bom=d_tempo[1]),
    cartao_kpi("Cancelamento", formatar(kpi["cancelamento_%"], 1), "sobre todos os pedidos", NEON_VERMELHO, "%",
               delta=d_canc[0], delta_bom=d_canc[1]),
    cartao_kpi("Valor médio", formatar(kpi["valor_medio_brl"], 2), "por entrega", NEON_VIOLETA, prefixo="R$",
               delta=d_valor[0], delta_bom=d_valor[1]),
]
for coluna_kpi, html in zip(st.columns(5, gap="small"), cartoes):
    coluna_kpi.markdown(html, unsafe_allow_html=True)
st.write("")  # respiro entre os cartões e o glossário

if not ant:
    st.caption("Variação vs período anterior: selecione um período menor (por exemplo, outubro) no filtro de período "
               "para comparar com o período de mesmo tamanho logo antes.")

with st.expander("Glossário: como cada indicador é calculado", icon=":material/menu_book:"):
    st.markdown(GLOSSARIO, unsafe_allow_html=True)

with st.container(key="card_dia"):
    titulo_cartao("Entregas no prazo por dia", "Pontos = OTD de cada dia; linha = média móvel de 7 dias.")
    st.plotly_chart(grafico_otd_por_dia(df, META_OTD_PCT), width="stretch", config=CONFIG_PLOTLY)

col_a, col_b = st.columns(2, gap="medium")
with col_a:
    with st.container(key="card_status"):
        titulo_cartao("Distribuição por status",
                      "Percentual sobre todos os pedidos. O OTD do topo exclui os cancelados.")
        st.plotly_chart(grafico_status(df), width="stretch", config=CONFIG_PLOTLY)
with col_b:
    with st.container(key="card_bairros"):
        titulo_cartao("Volume por bairro (top 12)", "Alterne entre o bairro de coleta e o de entrega.")
        aba_origem, aba_destino = st.tabs(["Origem (coleta)", "Destino (entrega)"])
        for aba, coluna, cor in [(aba_origem, "local_origem", NEON_AZUL), (aba_destino, "local_destino", NEON_VIOLETA)]:
            with aba:
                resumo = resumo_bairros(df, coluna)
                lider = resumo["entregas"].idxmax()
                pior = resumo["atraso_%"].idxmax() if resumo["atraso_%"].notna().any() else "-"
                pior_txt = formatar(resumo.loc[pior, "atraso_%"], 1, "%") if pior != "-" else "-"
                st.markdown(
                    f'<div class="chips">'
                    f'<span class="chip" style="--acc:{cor}"><i></i>Maior volume: <b>{lider}</b> '
                    f'({formatar(resumo.loc[lider, "entregas"], 0)})</span>'
                    f'<span class="chip" style="--acc:{NEON_AMARELO}"><i></i>Maior atraso: <b>{pior}</b> ({pior_txt})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(grafico_bairros(resumo, cor), width="stretch", config=CONFIG_PLOTLY, key=f"graf_{coluna}")

with st.expander("Ver dados filtrados"):
    colunas_tabela = [
        "id_pedido", "data_hora_pedido", "cidade_origem", "bairro_origem", "cidade_destino", "bairro_destino",
        "endereco_destino", "distancia_km", "horario_pico", "tempo_transito_min", "prazo_prometido_min",
        "valor_entrega_brl", "status", "outlier_tempo", "tempo_transito_min_bruto",
    ]
    tabela = df[colunas_tabela].assign(data_hora_pedido=df["data_hora_pedido"].dt.strftime("%d/%m/%Y %H:%M"))
    st.dataframe(tabela, width="stretch", hide_index=True)
    st.download_button("Baixar CSV filtrado", tabela.to_csv(index=False).encode("utf-8"),
                       file_name="entregas_filtradas.csv", mime="text/csv")
