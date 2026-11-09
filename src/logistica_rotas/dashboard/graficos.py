"""Gráficos Plotly do dashboard (fundo transparente para herdar o tema escuro)."""

import pandas as pd
import plotly.graph_objects as go

from logistica_rotas.dashboard.estilo import (
    COR_CARTAO, COR_EIXO, COR_GRADE, COR_MUTED, COR_TEXTO, COR_TEXTO_SEC, NEON_AMARELO, NEON_AZUL, NEON_CIANO,
    NEON_VERDE, NEON_VERMELHO, NEON_VIOLETA, formatar,
)
from logistica_rotas.metricas.kpis import mascara_concluidas

STATUS_ORDEM = ["entregue", "com_atraso", "cancelado"]
STATUS_ROTULO = {"entregue": "Entregue no prazo", "com_atraso": "Com atraso", "cancelado": "Cancelado"}
STATUS_COR = {"entregue": NEON_VERDE, "com_atraso": NEON_AMARELO, "cancelado": NEON_VERMELHO}
FAIXAS_KM = [0, 2, 4, 6, 8, 10, float("inf")]
FAIXAS_ROTULO = ["0-2 km", "2-4 km", "4-6 km", "6-8 km", "8-10 km", "10+ km"]
HORAS_PICO = [(7.5, 8.5), (16.5, 19.5)]  # faixas sombreadas no gráfico por hora

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
# Gráficos novos (páginas Visão geral, Desempenho, Mapa e Simulador)
# ---------------------------------------------------------------------------
COR_TRAJETO = {"mesma cidade": NEON_AZUL, "entre cidades": NEON_AMARELO}


def grafico_otd_por_dia(df: pd.DataFrame, meta: float) -> go.Figure:
    """OTD por dia (linha) com média móvel de 7 dias e linha da meta."""
    feitas = df[mascara_concluidas(df)]
    diario = feitas.groupby("data").agg(otd=("status", lambda s: (s == "entregue").mean() * 100),
                                        entregas=("status", "size"))
    diario.index = pd.to_datetime(diario.index)
    media7 = diario["otd"].rolling(7, min_periods=3).mean()
    fig = go.Figure()
    fig.add_hline(y=meta, line=dict(color=NEON_VERDE, width=1, dash="dot"),
                  annotation_text=f"meta {formatar(meta, 0)}%", annotation_position="top left",
                  annotation_font=dict(color=NEON_VERDE, size=11))
    fig.add_trace(go.Scatter(x=diario.index, y=diario["otd"], mode="markers", name="OTD do dia",
                             marker=dict(size=6, color="rgba(59,158,255,0.45)"),
                             customdata=diario["entregas"],
                             hovertemplate="%{x|%d/%m}<br>OTD: %{y:.1f}%<br>Entregas: %{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=media7.index, y=media7, mode="lines", name="média móvel 7 dias",
                             line=dict(color=NEON_AZUL, width=2.5),
                             hovertemplate="%{x|%d/%m}<br>Média 7 dias: %{y:.1f}%<extra></extra>"))
    fig.update_yaxes(ticksuffix="%", range=[max(0, diario["otd"].min() - 5), 101])
    fig.update_xaxes(tickformat="%d/%m", showgrid=False)
    return aplicar_layout(fig, altura=300)


def grafico_otd_faixa_trajeto(df: pd.DataFrame, minimo: int = 30) -> go.Figure:
    """OTD por faixa de distância, mesma cidade x entre cidades (faixas com poucas entregas omitidas)."""
    feitas = df[mascara_concluidas(df)]
    tabela = feitas.groupby(["faixa_distancia", "trajeto"], observed=True)["status"].agg(
        otd=lambda s: (s == "entregue").mean() * 100, n="size").reset_index()
    tabela.loc[tabela["n"] < minimo, "otd"] = None
    fig = go.Figure()
    for trajeto, cor in COR_TRAJETO.items():
        parte = tabela[tabela["trajeto"] == trajeto].set_index("faixa_distancia").reindex(FAIXAS_ROTULO)
        fig.add_trace(go.Scatter(
            x=FAIXAS_ROTULO, y=parte["otd"], name=trajeto.capitalize(), mode="lines+markers",
            line=dict(color=cor, width=2.5), marker=dict(size=9, color=cor, line=dict(color=COR_CARTAO, width=2)),
            customdata=parte["n"], connectgaps=False,
            hovertemplate=f"<b>{trajeto}</b> · %{{x}}<br>OTD: %{{y:.1f}}%<br>Entregas: %{{customdata:.0f}}<extra></extra>",
        ))
    fig.update_yaxes(ticksuffix="%", title=dict(text="Entregas no prazo", font=dict(color=COR_MUTED)))
    fig.update_xaxes(showgrid=False, title=dict(text="Faixa de distância", font=dict(color=COR_MUTED)))
    return aplicar_layout(fig, altura=340)


def mapa_bairros(tabela: pd.DataFrame, metrica: str, rotulo: str, sufixo: str) -> go.Figure:
    """Mapa (fundo escuro do OpenStreetMap/CARTO) com um círculo por bairro: cor = métrica, tamanho = entregas."""
    tamanho = 8 + (tabela["entregas"] / tabela["entregas"].max()) ** 0.5 * 22
    fig = go.Figure(go.Scattermap(
        lat=tabela["lat"], lon=tabela["lon"], mode="markers",
        marker=dict(size=tamanho, color=tabela[metrica], opacity=0.85,
                    colorscale=[[0, "#1e3a5f"], [0.5, NEON_AZUL], [1, NEON_CIANO]] if metrica == "entregas"
                    else [[0, NEON_VERDE], [0.5, NEON_AMARELO], [1, NEON_VERMELHO]],
                    colorbar=dict(title=dict(text=rotulo, font=dict(color=COR_TEXTO_SEC)), ticksuffix=sufixo,
                                  tickfont=dict(color=COR_TEXTO_SEC), thickness=12, outlinewidth=0)),
        text=tabela["bairro"] + " · " + tabela["cidade"],
        customdata=tabela[["entregas", "atraso_pct", "tempo_mediano_min", "fonte_coordenada"]],
        hovertemplate=("<b>%{text}</b><br>Entregas: %{customdata[0]}<br>Atraso: %{customdata[1]:.1f}%"
                       "<br>Tempo mediano: %{customdata[2]:.0f} min<br>Coordenada: %{customdata[3]}<extra></extra>"),
    ))
    fig.update_layout(map=dict(style="carto-darkmatter", zoom=11.2,
                               center=dict(lat=float(tabela["lat"].mean()), lon=float(tabela["lon"].mean()))))
    aplicar_layout(fig, altura=560)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def curva_simulador(curva: pd.DataFrame, escolhido: pd.Series, individual: pd.Series) -> go.Figure:
    """Economia de km (x) x no prazo com variação (y) para várias esperas; destaca o cenário escolhido."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curva["economia_km_pct"], y=curva["no_prazo_real_pct"], mode="lines+markers+text", name="espera máxima",
        line=dict(color=NEON_AZUL, width=2), marker=dict(size=8, color=NEON_AZUL),
        text=[f"{int(e)} min" for e in curva["espera_max_min"]], textposition="bottom center",
        textfont=dict(color=COR_MUTED, size=11),
        hovertemplate="Espera até %{text}<br>Economia: %{x:.1f}%<br>No prazo: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[0], y=[individual["no_prazo_real_pct"]], mode="markers+text", name="individual",
        marker=dict(size=11, color=COR_MUTED), text=["individual"], textposition="middle right",
        textfont=dict(color=COR_TEXTO_SEC), hovertemplate="Individual (sai na hora)<br>No prazo: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[escolhido["economia_km_pct"]], y=[escolhido["no_prazo_real_pct"]], mode="markers", name="cenário escolhido",
        marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=NEON_CIANO, width=3)),
        hovertemplate="Cenário escolhido<br>Economia: %{x:.1f}%<br>No prazo: %{y:.1f}%<extra></extra>",
    ))
    maximo = max(float(curva["economia_km_pct"].max()), 1.0)
    fig.update_xaxes(ticksuffix="%", title=dict(text="Economia de km vs individual", font=dict(color=COR_MUTED)),
                     range=[-0.06 * maximo, 1.12 * maximo])
    fig.update_yaxes(ticksuffix="%", title=dict(text="No prazo (com variação de trânsito)", font=dict(color=COR_MUTED)))
    return aplicar_layout(fig, altura=380, cor_destaque=NEON_CIANO)
