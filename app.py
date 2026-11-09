"""Dashboard interativo de entregas urbanas de moto (dados simulados).

Executar na raiz do projeto:
    .venv\\Scripts\\python.exe -m streamlit run app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from logistica_rotas.ingestao.leitura import carregar_entregas  # noqa: E402
from logistica_rotas.limpeza.tratamento import limpar_entregas  # noqa: E402
from logistica_rotas.metricas.kpis import mascara_concluidas, taxa_atraso, taxa_cancelamento  # noqa: E402

# ---------------------------------------------------------------------------
# Paleta neon (dark mode)
# Status mantém o significado: verde = no prazo, amarelo/laranja = atraso,
# vermelho = cancelado. Azul e ciano são as cores de volume/série.
# ---------------------------------------------------------------------------
COR_FUNDO = "#0a0b10"          # fundo da página: separa segmentos e marcadores
COR_CARTAO = "#12141c"
COR_TEXTO = "#f4f5fb"
COR_TEXTO_SEC = "#b4b8c8"
COR_MUTED = "#7c8197"
COR_GRADE = "#1f2230"
COR_EIXO = "#2a2e3d"

NEON_AZUL = "#3b9eff"
NEON_CIANO = "#22d3ee"
NEON_VERDE = "#22e584"
NEON_AMARELO = "#ffb020"
NEON_VERMELHO = "#ff4d6d"
NEON_VIOLETA = "#a78bfa"

STATUS_ORDEM = ["entregue", "com_atraso", "cancelado"]
STATUS_ROTULO = {"entregue": "Entregue no prazo", "com_atraso": "Com atraso", "cancelado": "Cancelado"}
STATUS_COR = {"entregue": NEON_VERDE, "com_atraso": NEON_AMARELO, "cancelado": NEON_VERMELHO}

FAIXAS_KM = [0, 2, 4, 6, 8, 10, float("inf")]
FAIXAS_ROTULO = ["0-2 km", "2-4 km", "4-6 km", "6-8 km", "8-10 km", "10+ km"]
HORAS_PICO = [(7.5, 8.5), (16.5, 19.5)]  # faixas sombreadas no gráfico por hora
TOP_BAIRROS = 12  # bairros exibidos no gráfico de volume

st.set_page_config(page_title="Logística de Entregas", page_icon=":material/two_wheeler:", layout="wide")

# ---------------------------------------------------------------------------
# CSS: cartões de KPI neon, cartões dos gráficos e abas em formato de pílula
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            radial-gradient(1200px 500px at 85% -10%, rgba(59,158,255,0.10), transparent 60%),
            radial-gradient(900px 400px at -10% 10%, rgba(34,211,238,0.06), transparent 60%),
            {COR_FUNDO};
    }}
    .block-container {{padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1500px;}}
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #10121a 0%, #0b0c12 100%);
        border-right: 1px solid {COR_GRADE};
    }}

    /* Cabeçalho */
    .titulo {{
        font-size: 2.5rem; font-weight: 800; line-height: 1.1; margin: 0;
        background: linear-gradient(90deg, {COR_TEXTO} 0%, {NEON_CIANO} 55%, {NEON_AZUL} 100%);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }}
    .subtitulo {{color: {COR_TEXTO_SEC}; margin: .35rem 0 1.4rem 0; font-size: .98rem;}}
    .selo {{
        display: inline-block; margin-left: .6rem; padding: .15rem .6rem; border-radius: 999px;
        font-size: .72rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
        color: {NEON_CIANO}; border: 1px solid rgba(34,211,238,.45); background: rgba(34,211,238,.08);
        vertical-align: middle;
    }}

    /* Cartões de KPI */
    .kpi {{
        position: relative; overflow: hidden; height: 100%; min-width: 0;
        container-type: inline-size;  /* o número se ajusta à largura do próprio cartão */
        padding: 1rem 1.1rem 1.05rem 1.1rem; border-radius: 16px;
        background: linear-gradient(150deg, color-mix(in srgb, var(--acc) 16%, {COR_CARTAO}) 0%, {COR_CARTAO} 65%);
        border: 1px solid color-mix(in srgb, var(--acc) 60%, transparent);
        box-shadow: 0 0 22px -6px var(--acc), inset 0 1px 0 rgba(255,255,255,.05);
        transition: transform .15s ease, box-shadow .15s ease;
    }}
    .kpi:hover {{transform: translateY(-2px); box-shadow: 0 0 30px -4px var(--acc), inset 0 1px 0 rgba(255,255,255,.06);}}
    .kpi::before {{
        content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
        background: linear-gradient(90deg, var(--acc), transparent);
    }}
    .kpi-rotulo {{display: flex; align-items: center; gap: .45rem; color: {COR_TEXTO_SEC};
        font-size: clamp(.62rem, 7cqi, .82rem); font-weight: 600; letter-spacing: .03em; text-transform: uppercase;
        white-space: nowrap;}}
    .kpi-ponto {{flex-shrink: 0; width: 8px; height: 8px; border-radius: 50%; background: var(--acc); box-shadow: 0 0 10px var(--acc);}}
    .kpi-valor {{color: {COR_TEXTO}; font-size: clamp(1.5rem, 20cqi, 2.55rem); font-weight: 800; line-height: 1.15;
        margin-top: .35rem; font-variant-numeric: tabular-nums; white-space: nowrap;}}
    .kpi-valor small {{font-size: .45em; font-weight: 600; color: {COR_TEXTO_SEC}; margin-left: .2rem;}}
    .kpi-valor small.prefixo {{margin-left: 0; margin-right: .25rem;}}
    .kpi-nota {{color: {COR_MUTED}; font-size: .8rem; margin-top: .15rem;}}

    /* Cartões dos gráficos (containers com key "card_...") */
    [class*="st-key-card_"] {{
        background: linear-gradient(180deg, #131620 0%, #0f1118 100%);
        border: 1px solid {COR_GRADE}; border-radius: 18px; padding: 1.1rem 1.2rem .6rem 1.2rem;
        box-shadow: 0 10px 30px -18px rgba(0,0,0,.9);
    }}
    .card-titulo {{color: {COR_TEXTO}; font-size: 1.08rem; font-weight: 700; margin: 0;}}
    .card-nota {{color: {COR_MUTED}; font-size: .84rem; margin: .2rem 0 .2rem 0;}}

    /* Abas em pílula com destaque neon (Streamlit 1.67: role="tablist" / data-testid="stTab") */
    .stTabs [role="tablist"] {{
        gap: 6px; width: fit-content; padding: 5px; border-radius: 12px;
        background: #0b0d14; border: 1px solid {COR_EIXO}; border-bottom: 1px solid {COR_EIXO};
    }}
    .stTabs [data-testid="stTab"] {{
        height: 38px; padding: 0 1.1rem; border-radius: 9px; background: transparent;
        display: flex; align-items: center; transition: all .15s ease; cursor: pointer;
    }}
    .stTabs [data-testid="stTab"] p {{color: {COR_TEXTO_SEC}; font-weight: 600; font-size: .92rem; margin: 0;}}
    .stTabs [data-testid="stTab"]:hover {{background: rgba(59,158,255,.12);}}
    .stTabs [data-testid="stTab"][aria-selected="true"] {{
        background: linear-gradient(135deg, {NEON_AZUL}, {NEON_CIANO});
        box-shadow: 0 0 18px -3px rgba(59,158,255,.75);
    }}
    .stTabs [data-testid="stTab"][aria-selected="true"] p {{color: #05070c !important;}}
    .stTabs .react-aria-SelectionIndicator {{display: none;}}

    /* Chips de destaque dentro das abas */
    .chips {{display: flex; flex-wrap: wrap; gap: .5rem; margin: .7rem 0 .1rem 0;}}
    .chip {{padding: .3rem .7rem; border-radius: 999px; font-size: .8rem; color: {COR_TEXTO_SEC};
        background: #0b0d14; border: 1px solid {COR_EIXO};}}
    .chip b {{color: {COR_TEXTO};}}
    .chip i {{display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: .4rem;
        background: var(--acc); box-shadow: 0 0 8px var(--acc); font-style: normal;}}

    [data-testid="stExpander"] details {{border-radius: 14px; border-color: {COR_GRADE}; background: #10121a;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Dados e indicadores
# ---------------------------------------------------------------------------
@st.cache_data
def obter_dados() -> pd.DataFrame:
    """Carrega a base limpa (outliers de tempo tratados, ver notebook 02) e guarda em cache."""
    df = limpar_entregas(carregar_entregas())
    df["faixa_distancia"] = pd.cut(df["distancia_km"], bins=FAIXAS_KM, labels=FAIXAS_ROTULO, right=False)
    return df


def calcular_kpis(df: pd.DataFrame) -> dict[str, float]:
    """KPIs do topo (regras em metricas/kpis.py): concluídas sem cancelados e sem tempo inválido."""
    concluidas = df[mascara_concluidas(df)]
    return {
        "total": len(df),
        "concluidas": len(concluidas),
        "taxa_atraso_%": taxa_atraso(df),
        "tempo_medio_min": concluidas["tempo_transito_min"].mean(),
        "tempo_mediano_min": concluidas["tempo_transito_min"].median(),
        "cancelamento_%": taxa_cancelamento(df),
        "valor_medio_brl": df["valor_entrega_brl"].mean(),
    }


def formatar(valor: float, casas: int = 1, sufixo: str = "") -> str:
    """Número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    if pd.isna(valor):
        return "-"
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto + sufixo


def resumo_bairros(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Entregas e taxa de atraso (sobre concluídas) por bairro."""
    concl = df[mascara_concluidas(df)]
    return pd.DataFrame({
        "entregas": df.groupby(coluna, observed=True).size(),
        "atraso_%": concl.groupby(coluna, observed=True)["status"].apply(lambda s: (s == "com_atraso").mean() * 100),
    }).query("entregas > 0").nlargest(TOP_BAIRROS, "entregas").sort_values("entregas")


# ---------------------------------------------------------------------------
# Componentes HTML
# ---------------------------------------------------------------------------
def cartao_kpi(rotulo: str, valor: str, nota: str, cor: str, unidade: str = "", dica: str = "",
               prefixo: str = "") -> str:
    """Cartão de KPI com borda e brilho na cor de destaque. `prefixo`/`unidade` aparecem menores."""
    unidade_html = f"<small>{unidade}</small>" if unidade else ""
    prefixo_html = f'<small class="prefixo">{prefixo}</small>' if prefixo else ""
    return (
        f'<div class="kpi" style="--acc:{cor}" title="{dica}">'
        f'<div class="kpi-rotulo"><span class="kpi-ponto"></span>{rotulo}</div>'
        f'<div class="kpi-valor">{prefixo_html}{valor}{unidade_html}</div>'
        f'<div class="kpi-nota">{nota}</div></div>'
    )


def titulo_cartao(titulo: str, nota: str = "") -> None:
    """Título e nota de um cartão de gráfico."""
    nota_html = f'<div class="card-nota">{nota}</div>' if nota else ""
    st.markdown(f'<div class="card-titulo">{titulo}</div>{nota_html}', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Gráficos (Plotly, fundo transparente para herdar o tema)
# ---------------------------------------------------------------------------
CONFIG_PLOTLY = {"displayModeBar": False}


def aplicar_layout(fig: go.Figure, altura: int = 340, cor_destaque: str = NEON_AZUL) -> go.Figure:
    """Estilo comum: grade discreta, eixos recessivos, tooltip escuro com borda neon."""
    fig.update_layout(
        height=altura,
        margin=dict(l=8, r=16, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=COR_TEXTO_SEC),
        hoverlabel=dict(bgcolor="#0b0d14", bordercolor=cor_destaque, font=dict(color=COR_TEXTO, size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, traceorder="normal",
                    font=dict(color=COR_TEXTO_SEC)),
        bargap=0.32,
        separators=",.",  # padrão brasileiro: 1.500 e 7,5
    )
    fig.update_xaxes(gridcolor=COR_GRADE, linecolor=COR_EIXO, zeroline=False, tickfont=dict(color=COR_MUTED))
    fig.update_yaxes(gridcolor=COR_GRADE, linecolor=COR_EIXO, zeroline=False, tickfont=dict(color=COR_MUTED))
    return fig


def grafico_status(df: pd.DataFrame) -> go.Figure:
    """Barras horizontais: quantidade e % por status."""
    contagem = df["status"].value_counts().reindex(STATUS_ORDEM).dropna()
    perc = contagem / contagem.sum() * 100
    fig = go.Figure(
        go.Bar(
            x=contagem.values,
            y=[STATUS_ROTULO[s] for s in contagem.index],
            orientation="h",
            marker=dict(color=[STATUS_COR[s] for s in contagem.index], cornerradius=6),
            text=[f"<b>{formatar(q, 0)}</b>  ({formatar(p)}%)" for q, p in zip(contagem.values, perc.values)],
            textposition="outside",
            textfont=dict(color=COR_TEXTO, size=13),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Entregas: %{x:,.0f}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False, showline=False, tickfont=dict(color=COR_TEXTO_SEC, size=13))
    fig.update_xaxes(showticklabels=False, showgrid=False, showline=False, range=[0, contagem.max() * 1.38])
    return aplicar_layout(fig, altura=250)


def grafico_bairros(resumo: pd.DataFrame, cor: str) -> go.Figure:
    """Volume por bairro, ordenado, com taxa de atraso no tooltip."""
    fig = go.Figure(
        go.Bar(
            x=resumo["entregas"],
            y=resumo.index.astype(str),
            orientation="h",
            marker=dict(color=cor, cornerradius=6),
            text=resumo["entregas"].map(lambda v: formatar(v, 0)),
            textposition="outside",
            textfont=dict(color=COR_TEXTO_SEC),
            cliponaxis=False,
            customdata=resumo["atraso_%"],
            hovertemplate="<b>%{y}</b><br>Entregas: %{x:,.0f}<br>Taxa de atraso: %{customdata:.1f}%<extra></extra>",
        )
    )
    fig.update_yaxes(showgrid=False, showline=False, tickfont=dict(color=COR_TEXTO_SEC))
    fig.update_xaxes(tickformat=",d", title=dict(text="Entregas", font=dict(color=COR_MUTED)),
                     range=[0, resumo["entregas"].max() * 1.15])
    return aplicar_layout(fig, altura=360, cor_destaque=cor)


def grafico_faixas(df: pd.DataFrame) -> go.Figure:
    """Barras empilhadas: entregas por faixa de distância, divididas por status."""
    tabela = pd.crosstab(df["faixa_distancia"], df["status"]).reindex(index=FAIXAS_ROTULO, fill_value=0)
    fig = go.Figure()
    for status in STATUS_ORDEM:
        if status not in tabela.columns:
            continue
        fig.add_bar(
            x=tabela.index,
            y=tabela[status],
            name=STATUS_ROTULO[status],
            marker=dict(color=STATUS_COR[status], line=dict(color=COR_CARTAO, width=2)),
            hovertemplate=f"<b>%{{x}}</b><br>{STATUS_ROTULO[status]}: %{{y:,.0f}}<extra></extra>",
        )
    fig.update_layout(barmode="stack", barcornerradius=6)
    fig.update_xaxes(showgrid=False, tickfont=dict(color=COR_TEXTO_SEC))
    fig.update_yaxes(tickformat=",d", title=dict(text="Entregas", font=dict(color=COR_MUTED)))
    return aplicar_layout(fig, altura=370)


def grafico_atraso_hora(df: pd.DataFrame) -> go.Figure:
    """Linha com área: taxa de atraso por hora do pedido, com picos de trânsito sombreados."""
    concl = df[mascara_concluidas(df)]
    por_hora = concl.groupby("hora").agg(
        atraso=("status", lambda s: (s == "com_atraso").mean() * 100),
        entregas=("status", "size"),
    )
    fig = go.Figure()
    for inicio, fim in HORAS_PICO:
        fig.add_vrect(x0=inicio, x1=fim, fillcolor=NEON_AMARELO, opacity=0.08, line_width=0, layer="below")
    fig.add_annotation(x=18, y=1, yref="paper", text="pico de trânsito", showarrow=False,
                       font=dict(color=NEON_AMARELO, size=11), yanchor="bottom")
    fig.add_trace(
        go.Scatter(
            x=por_hora.index,
            y=por_hora["atraso"],
            mode="lines+markers",
            line=dict(color=NEON_CIANO, width=2.5, shape="spline", smoothing=0.6),
            marker=dict(size=8, color=NEON_CIANO, line=dict(color=COR_CARTAO, width=2)),
            fill="tozeroy",
            fillgradient=dict(type="vertical", colorscale=[[0, "rgba(34,211,238,0)"], [1, "rgba(34,211,238,0.28)"]]),
            customdata=por_hora["entregas"],
            hovertemplate="<b>%{x}h</b><br>Taxa de atraso: %{y:.1f}%<br>Entregas concluídas: %{customdata:,.0f}<extra></extra>",
        )
    )
    fig.update_xaxes(dtick=2, tickangle=0, range=[7.5, 23.5], ticksuffix="h", showgrid=False,
                     title=dict(text="Hora do pedido", font=dict(color=COR_MUTED)))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero", title=dict(text="Taxa de atraso", font=dict(color=COR_MUTED)))
    fig.update_layout(hovermode="x", showlegend=False)
    aplicar_layout(fig, altura=330, cor_destaque=NEON_CIANO)
    fig.update_layout(margin=dict(t=28))  # espaço para o rótulo "pico de trânsito"
    return fig


# ---------------------------------------------------------------------------
# Barra lateral: filtros (vazio = todos)
# ---------------------------------------------------------------------------
dados = obter_dados()

with st.sidebar:
    st.header("Filtros")
    status_sel = st.multiselect(
        "Status da entrega",
        options=STATUS_ORDEM,
        default=STATUS_ORDEM,
        format_func=STATUS_ROTULO.get,
    )
    cidades = sorted(dados["cidade_origem"].cat.categories.union(dados["cidade_destino"].cat.categories))
    cid_origem_sel = st.multiselect("Cidade de origem", options=cidades, placeholder="Todas")
    cid_destino_sel = st.multiselect("Cidade de destino", options=cidades, placeholder="Todas")
    # Bairros listados apenas das cidades escolhidas (rótulo "Bairro · Cidade").
    base_o = dados[dados["cidade_origem"].isin(cid_origem_sel)] if cid_origem_sel else dados
    base_d = dados[dados["cidade_destino"].isin(cid_destino_sel)] if cid_destino_sel else dados
    origem_sel = st.multiselect("Bairro de origem", options=sorted(base_o["local_origem"].unique()), placeholder="Todos")
    destino_sel = st.multiselect("Bairro de destino", options=sorted(base_d["local_destino"].unique()), placeholder="Todos")
    st.divider()
    st.caption(
        "Dados simulados: 5.000 pedidos (set-out/2026) no ABC paulista e em Mauá. "
        "Bairros e ruas reais; 43 de 45 bairros com coordenada do OpenStreetMap. "
        "Pedidos, tempos e valores são simulados."
    )

filtro = dados["status"].isin(status_sel)
if cid_origem_sel:
    filtro &= dados["cidade_origem"].isin(cid_origem_sel)
if cid_destino_sel:
    filtro &= dados["cidade_destino"].isin(cid_destino_sel)
if origem_sel:
    filtro &= dados["local_origem"].isin(origem_sel)
if destino_sel:
    filtro &= dados["local_destino"].isin(destino_sel)
df = dados[filtro]

# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
st.markdown(
    '<h1 class="titulo">Entregas urbanas de moto<span class="selo">dados simulados</span></h1>'
    '<div class="subtitulo">Desempenho operacional: volume, atrasos e tempo de trânsito.</div>',
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("Nenhuma entrega com os filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

kpi = calcular_kpis(df)
cartoes = [
    cartao_kpi("Entregas", formatar(kpi["total"], 0), f"{formatar(kpi['concluidas'], 0)} concluídas", NEON_AZUL),
    cartao_kpi("Taxa de atraso", formatar(kpi["taxa_atraso_%"], 1), "sobre as concluídas", NEON_AMARELO, "%",
               "Entregas com atraso / entregas concluídas (cancelados fora do cálculo)."),
    cartao_kpi("Tempo médio", formatar(kpi["tempo_medio_min"], 1), f"mediana {formatar(kpi['tempo_mediano_min'], 1)} min",
               NEON_CIANO, "min", "Tempo de trânsito das entregas concluídas."),
    cartao_kpi("Cancelamento", formatar(kpi["cancelamento_%"], 1), "sobre todos os pedidos", NEON_VERMELHO, "%"),
    cartao_kpi("Valor médio", formatar(kpi["valor_medio_brl"], 2), "por entrega", NEON_VERDE, prefixo="R$"),
]
for coluna_kpi, html in zip(st.columns(5, gap="small"), cartoes):
    coluna_kpi.markdown(html, unsafe_allow_html=True)

st.write("")
col_a, col_b = st.columns(2, gap="medium")
with col_a:
    with st.container(key="card_status"):
        titulo_cartao("Distribuição por status",
                      "Percentual sobre todos os pedidos. A taxa de atraso do topo exclui os cancelados.")
        st.plotly_chart(grafico_status(df), width="stretch", config=CONFIG_PLOTLY)
    with st.container(key="card_faixas"):
        titulo_cartao("Entregas por faixa de distância", "Distância estimada (linha reta x 1,3), não a rota real.")
        st.plotly_chart(grafico_faixas(df), width="stretch", config=CONFIG_PLOTLY)
with col_b:
    with st.container(key="card_bairros"):
        titulo_cartao(f"Volume por bairro (top {TOP_BAIRROS})", "Alterne entre o bairro de coleta e o de entrega.")
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
                st.plotly_chart(grafico_bairros(resumo, cor), width="stretch", config=CONFIG_PLOTLY,
                                key=f"graf_{coluna}")
    with st.container(key="card_hora"):
        titulo_cartao("Taxa de atraso por hora do pedido",
                      "Faixas em amarelo: picos de trânsito (7h-8h e 17h-19h em dias úteis).")
        st.plotly_chart(grafico_atraso_hora(df), width="stretch", config=CONFIG_PLOTLY)

with st.expander("Ver dados filtrados"):
    colunas_tabela = [
        "id_pedido", "data_hora_pedido", "cidade_origem", "bairro_origem", "cidade_destino", "bairro_destino",
        "endereco_destino", "distancia_km", "horario_pico", "tempo_transito_min", "prazo_prometido_min",
        "valor_entrega_brl", "status", "outlier_tempo", "tempo_transito_min_bruto",
    ]
    tabela = df[colunas_tabela].assign(
        data_hora_pedido=df["data_hora_pedido"].dt.strftime("%d/%m/%Y %H:%M")
    )
    st.dataframe(tabela, width="stretch", hide_index=True)
    st.download_button(
        "Baixar CSV filtrado",
        tabela.to_csv(index=False).encode("utf-8"),
        file_name="entregas_filtradas.csv",
        mime="text/csv",
    )
