"""Gráficos estáticos (matplotlib) para o relatório e o README.

Padrão visual:
- Título diz a conclusão; subtítulo diz o que está sendo medido.
- Uma cor por entidade, fixa em todos os gráficos: azul = mesma cidade,
  laranja = entre cidades. Cinza = série de contexto.
- Marcas finas, grade discreta, rótulos de valor só onde ajudam a leitura.
- Grupos com poucas entregas (< 30) não são desenhados (OTD instável).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter

from logistica_rotas.ingestao.leitura import SIGLA_CIDADE
from logistica_rotas.ingestao.simulacao import RAIZ_PROJETO
from logistica_rotas.metricas.kpis import mascara_concluidas, tabela_otd

PASTA_FIGURAS = RAIZ_PROJETO / "reports" / "figures"

# Paleta (modo claro, fundo do relatório)
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SEC = "#52514e"
TINTA_MUTED = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
AZUL = "#2a78d6"      # mesma cidade / série principal
LARANJA = "#eb6834"   # entre cidades
CINZA = "#898781"     # série de contexto
FAIXA_PICO = "#f0efec"
RAMPA_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

COR_TRAJETO = {"mesma cidade": AZUL, "entre cidades": LARANJA}
ROTULO_TRAJETO = {"mesma cidade": "Mesma cidade", "entre cidades": "Entre cidades"}
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
HORAS_PICO = [(7.5, 8.5), (16.5, 19.5)]
MIN_PEDIDOS = 30


def aplicar_estilo() -> None:
    """Define o padrão visual de todos os gráficos."""
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 11,
        "text.color": TINTA,
        "axes.labelcolor": TINTA_SEC,
        "axes.edgecolor": EIXO,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRADE,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": TINTA_MUTED,
        "ytick.color": TINTA_MUTED,
        "xtick.labelcolor": TINTA_SEC,
        "ytick.labelcolor": TINTA_SEC,
        "ytick.left": False,
        "legend.frameon": False,
        "legend.labelcolor": TINTA_SEC,
    })


def _nova_figura(largura: float = 9.0, altura: float = 4.8) -> tuple[Figure, plt.Axes]:
    aplicar_estilo()
    fig, ax = plt.subplots(figsize=(largura, altura))
    fig.subplots_adjust(top=0.80, left=0.09, right=0.97, bottom=0.14)
    return fig, ax


def _titulo(fig: Figure, titulo: str, subtitulo: str) -> None:
    """Título (conclusão) e subtítulo (o que é medido), alinhados à esquerda."""
    fig.text(0.02, 0.95, titulo, fontsize=14.5, fontweight="bold", color=TINTA, va="top")
    fig.text(0.02, 0.885, subtitulo, fontsize=10.5, color=TINTA_SEC, va="top")


def _nota(fig: Figure, texto: str) -> None:
    fig.text(0.02, 0.015, texto, fontsize=8.5, color=TINTA_MUTED, va="bottom")


def _eixo_percentual(ax: plt.Axes, minimo: float = 0, maximo: float = 100) -> None:
    ax.set_ylim(minimo, maximo)
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))


def otd_por_hora(df: pd.DataFrame) -> Figure:
    """Linha: OTD por hora do pedido, dia útil x fim de semana, com picos sombreados."""
    fig, ax = _nova_figura()
    for inicio, fim in HORAS_PICO:
        ax.axvspan(inicio, fim, color=FAIXA_PICO, zorder=0, lw=0)
    ax.text(18, 101, "pico de trânsito\n(dias úteis)", ha="center", va="bottom", fontsize=8.5, color=TINTA_MUTED)

    series = [(True, "Dia útil", AZUL), (False, "Fim de semana", CINZA)]
    for dia_util, rotulo, cor in series:
        t = tabela_otd(df[df["dia_util"] == dia_util], "hora", MIN_PEDIDOS)["otd_pct"]
        ax.plot(t.index, t.values, color=cor, lw=2, marker="o", ms=5, mec=SUPERFICIE, mew=1.2, label=rotulo)
        ultimo = t.dropna()
        ax.annotate(rotulo, (ultimo.index[-1], ultimo.iloc[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=10, color=TINTA_SEC)

    _eixo_percentual(ax, 50, 100)
    ax.set_xlim(7.5, 24.8)
    ax.set_xticks(range(8, 24, 2), [f"{h}h" for h in range(8, 24, 2)])
    ax.set_xlabel("Hora do pedido")
    ax.legend(loc="lower left", ncols=2)
    _titulo(fig, "Nos dias úteis, o OTD despenca às 8h e entre 17h e 19h",
            "OTD (% de entregas no prazo) por hora do pedido")
    _nota(fig, f"Base limpa (notebook 02). Horas com menos de {MIN_PEDIDOS} entregas concluídas não são exibidas.")
    return fig


def otd_por_faixa_trajeto(df: pd.DataFrame) -> Figure:
    """Linhas: OTD por faixa de distância, mesma cidade x entre cidades."""
    fig, ax = _nova_figura()
    tabela = tabela_otd(df, ["faixa_distancia_km", "trajeto"], MIN_PEDIDOS)["otd_pct"].unstack()
    x = np.arange(len(tabela.index))
    for trajeto in ["mesma cidade", "entre cidades"]:
        serie = tabela[trajeto]
        ax.plot(x, serie.values, color=COR_TRAJETO[trajeto], lw=2, marker="o", ms=6, mec=SUPERFICIE, mew=1.2,
                label=ROTULO_TRAJETO[trajeto])
        ultimo = serie.dropna()
        pos = tabela.index.get_loc(ultimo.index[-1])
        ax.annotate(ROTULO_TRAJETO[trajeto], (pos, ultimo.iloc[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=10, color=TINTA_SEC)
    _eixo_percentual(ax, 70, 100)
    ax.set_xticks(x, [f"{f} km" for f in tabela.index])
    ax.set_xlim(-0.3, len(x) - 0.3)
    ax.set_xlabel("Faixa de distância")
    ax.legend(loc="lower left", ncols=2)
    _titulo(fig, "Na mesma faixa de distância, cruzar a divisa quase não muda o prazo",
            "OTD por faixa de distância: o que derruba o OTD é a distância, não a mudança de cidade")
    _nota(fig, f"Grupos com menos de {MIN_PEDIDOS} entregas concluídas não são exibidos "
               "(ex.: entre cidades até 2 km; mesma cidade acima de 10 km).")
    return fig


def _barras_agrupadas(ax: plt.Axes, tabela: pd.DataFrame, horizontal: bool = False) -> None:
    """Barras agrupadas por trajeto (colunas da tabela), com rótulos de valor."""
    n_grupos, trajetos = len(tabela.index), ["mesma cidade", "entre cidades"]
    largura = 0.36
    pos = np.arange(n_grupos)
    for i, trajeto in enumerate(trajetos):
        valores = tabela[trajeto].to_numpy()
        desloc = pos + (i - 0.5) * (largura + 0.04)
        if horizontal:
            barras = ax.barh(desloc, valores, height=largura, color=COR_TRAJETO[trajeto],
                             edgecolor=SUPERFICIE, lw=1.5, label=ROTULO_TRAJETO[trajeto])
        else:
            barras = ax.bar(desloc, valores, width=largura, color=COR_TRAJETO[trajeto],
                            edgecolor=SUPERFICIE, lw=1.5, label=ROTULO_TRAJETO[trajeto])
        ax.bar_label(barras, labels=[f"{v:.1f}%".replace(".", ",") for v in valores], padding=4,
                     fontsize=9.5, color=TINTA)


def otd_pico_trajeto(df: pd.DataFrame) -> Figure:
    """Barras agrupadas: OTD fora do pico x no pico, por trajeto."""
    fig, ax = _nova_figura(8.0, 4.8)
    tabela = tabela_otd(df, ["horario_pico", "trajeto"], MIN_PEDIDOS)["otd_pct"].unstack()
    tabela = tabela.reindex(["nao", "sim"])
    _barras_agrupadas(ax, tabela)
    ax.set_xticks(range(2), ["Fora do pico", "Pico de trânsito"])
    ax.tick_params(axis="x", length=0, labelsize=11)
    _eixo_percentual(ax, 0, 110)
    ax.set_yticks(range(0, 101, 25))
    ax.legend(loc="upper right", ncols=2)
    _titulo(fig, "Entre cidades no pico, só metade das entregas chega no prazo",
            "OTD por horário e tipo de trajeto")
    return fig


def otd_cidade_trajeto(df: pd.DataFrame) -> Figure:
    """Barras horizontais agrupadas: OTD por cidade de destino e trajeto."""
    fig, ax = _nova_figura(9.0, 5.4)
    fig.subplots_adjust(left=0.22, top=0.82)
    tabela = tabela_otd(df, ["cidade_destino", "trajeto"], MIN_PEDIDOS)["otd_pct"].unstack()
    tabela.index = tabela.index.astype(str)
    tabela = tabela.sort_values("entre cidades", ascending=False)  # pior no topo (eixo invertido abaixo)
    _barras_agrupadas(ax, tabela, horizontal=True)
    ax.set_yticks(range(len(tabela)), tabela.index)
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0, labelsize=10.5)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlim(0, 110)
    ax.set_xticks(range(0, 101, 25))
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.legend(loc="lower right", ncols=2, bbox_to_anchor=(1, 1.0))
    _titulo(fig, "Mauá e Diadema têm o pior OTD nas entregas vindas de outras cidades",
            "OTD por cidade de destino e tipo de trajeto")
    entre = df[mascara_concluidas(df) & (df["trajeto"] == "entre cidades")]
    dist = entre.groupby("cidade_destino", observed=True)["distancia_km"].mean().sort_values(ascending=False)
    trechos = " · ".join(f"{SIGLA_CIDADE.get(c, c)} {v:.1f} km".replace(".", ",") for c, v in dist.items())
    _nota(fig, f"Distância média das entregas vindas de outras cidades: {trechos}.")
    return fig


def mapa_calor_atraso(df: pd.DataFrame) -> Figure:
    """Mapa de calor: taxa de atraso por dia da semana x hora."""
    fig, ax = _nova_figura(10.0, 4.6)
    fig.subplots_adjust(left=0.07, right=0.95, top=0.78, bottom=0.12)
    feitas = df[mascara_concluidas(df)]
    tabela = (feitas.assign(atraso=(feitas["status"] == "com_atraso") * 100,
                            dia=feitas["data_hora_pedido"].dt.day_of_week)
              .pivot_table(index="dia", columns="hora", values="atraso", aggfunc="mean")
              .reindex(range(7)))
    cmap = LinearSegmentedColormap.from_list("azul", RAMPA_AZUL)
    imagem = ax.imshow(tabela.to_numpy(), cmap=cmap, vmin=0, vmax=40, aspect="auto")
    ax.grid(False)
    ax.set_yticks(range(7), DIAS)
    ax.set_xticks(range(len(tabela.columns)), [f"{h}h" for h in tabela.columns])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    # Rótulo só nas células de destaque (>= 15%), para não poluir.
    for (i, j), valor in np.ndenumerate(tabela.to_numpy()):
        if not np.isnan(valor) and valor >= 15:
            ax.text(j, i, f"{valor:.0f}", ha="center", va="center", fontsize=8.5,
                    color="#ffffff" if valor >= 18 else TINTA)
    barra = fig.colorbar(imagem, ax=ax, fraction=0.025, pad=0.015)
    barra.outline.set_visible(False)
    barra.ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    barra.ax.tick_params(length=0, labelsize=9)
    _titulo(fig, "Os atrasos se concentram nas manhãs e fins de tarde dos dias úteis",
            "Taxa de atraso (% das entregas concluídas) por dia da semana e hora do pedido")
    n = feitas.groupby([feitas["data_hora_pedido"].dt.day_of_week, "hora"]).size()
    _nota(fig, f"Cada célula tem de {n.min()} a {n.max()} entregas: valores isolados oscilam bastante. "
               "Números exibidos só a partir de 15%.")
    return fig


def distribuicao_tempo_trajeto(df: pd.DataFrame) -> Figure:
    """Histogramas (linha) do tempo de trânsito por trajeto, com medianas."""
    fig, ax = _nova_figura()
    feitas = df[mascara_concluidas(df)]
    bins = np.arange(0, 92, 3)
    for trajeto in ["mesma cidade", "entre cidades"]:
        tempos = feitas.loc[feitas["trajeto"] == trajeto, "tempo_transito_min"].dropna()
        pesos = np.full(len(tempos), 100 / len(tempos))
        ax.hist(tempos.clip(upper=90), bins=bins, weights=pesos, histtype="step", lw=2,
                color=COR_TRAJETO[trajeto], label=ROTULO_TRAJETO[trajeto])
        mediana = tempos.median()
        ax.axvline(mediana, color=COR_TRAJETO[trajeto], lw=1, ls="--")
        ax.text(mediana + 1, ax.get_ylim()[1] * 0.98 if trajeto == "mesma cidade" else ax.get_ylim()[1] * 0.6,
                f"mediana {mediana:.0f} min", fontsize=9.5, color=TINTA_SEC, va="top")
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_xlim(0, 90)
    ax.set_xlabel("Tempo de trânsito (min)")
    ax.set_ylabel("% das entregas do trajeto")
    ax.legend(loc="upper right")
    _titulo(fig, "Entregas entre cidades levam o dobro do tempo e variam muito mais",
            "Distribuição do tempo de trânsito por tipo de trajeto")
    _nota(fig, "Base limpa (outliers de tempo removidos no notebook 02). Tempos acima de 90 min somados na última faixa.")
    return fig


def salvar_figura(fig: Figure, nome: str, pasta: Path = PASTA_FIGURAS) -> Path:
    """Salva a figura em PNG em reports/figures."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.png"
    fig.savefig(caminho)
    return caminho
