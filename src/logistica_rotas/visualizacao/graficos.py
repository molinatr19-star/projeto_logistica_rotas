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
    _titulo(fig, "Mauá, a cidade mais afastada, tem o pior OTD nas entregas vindas de fora",
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


# ---------------------------------------------------------------------------
# Mapas estáticos e roteirização (notebooks 04 e 05)
# ---------------------------------------------------------------------------
CORES_VIAGENS = ["#2a78d6", "#eb6834", "#1baf7a", "#e87ba4", "#6250d6", "#008300", "#eda100", "#e34948"]
VERMELHO_STATUS = "#d03b3b"
ASPECTO_LAT = 1 / np.cos(np.radians(-23.67))  # corrige a distorção lon x lat na latitude do ABC


def _formatar(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def mapa_bairros_estatico(tabela: pd.DataFrame) -> Figure:
    """Bairros de destino em lat/lon: cor = taxa de atraso, tamanho = entregas. Sem mapa de fundo."""
    fig, ax = _nova_figura(9.0, 7.2)
    fig.subplots_adjust(top=0.86, left=0.04, right=0.93, bottom=0.08)
    ax.grid(False)
    for lado in ("bottom", "left"):
        ax.spines[lado].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    cmap = LinearSegmentedColormap.from_list("azul", RAMPA_AZUL)
    reais = tabela[tabela["fonte_coordenada"] == "osm"]
    simuladas = tabela[tabela["fonte_coordenada"] != "osm"]
    pontos = ax.scatter(reais["lon"], reais["lat"], s=reais["entregas"] * 2.2, c=reais["atraso_pct"], cmap=cmap,
                        vmin=0, vmax=15, edgecolor=SUPERFICIE, linewidth=1.5, zorder=3)
    ax.scatter(simuladas["lon"], simuladas["lat"], s=simuladas["entregas"] * 2.2, facecolor="none",
               edgecolor=TINTA_SEC, linewidth=1.2, linestyle="--", zorder=3, label="posição simulada")
    hubs = tabela[tabela["bairro"] == "Centro"]
    ax.scatter(hubs["lon"], hubs["lat"], marker="s", s=28, color=TINTA, zorder=4, label="hub (Centro)")
    for linha in hubs.itertuples(index=False):
        ax.annotate(linha.cidade, (linha.lon, linha.lat), xytext=(0, 12), textcoords="offset points",
                    ha="center", fontsize=10, fontweight="bold", color=TINTA, zorder=5)
    ax.set_aspect(ASPECTO_LAT)
    barra = fig.colorbar(pontos, ax=ax, fraction=0.03, pad=0.01)
    barra.outline.set_visible(False)
    barra.ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    barra.ax.tick_params(length=0, labelsize=9)
    barra.set_label("Taxa de atraso", color=TINTA_SEC)
    ax.legend(loc="lower left", fontsize=9)
    correlacao = tabela[["atraso_pct", "distancia_media_km"]].corr().iloc[0, 1]
    _titulo(fig, "Bairros com entregas mais longas tendem a atrasar mais",
            f"Bairros de destino: cor = taxa de atraso, tamanho = entregas. "
            f"Correlação com a distância média: {_formatar(correlacao, 2)}")
    _nota(fig, "Coordenadas: OpenStreetMap/Nominatim (© colaboradores do OSM). Cada bairro tem de "
               f"{tabela['entregas'].min()} a {tabela['entregas'].max()} entregas: diferenças pequenas são ruído.")
    return fig


def comparacao_metodos(resumo: pd.DataFrame, destaque: str = "OR-Tools com prazo") -> Figure:
    """Dois painéis (mesma ordem de métodos): economia de km e % de entregas no prazo."""
    aplicar_estilo()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    fig.subplots_adjust(top=0.76, left=0.2, right=0.97, bottom=0.12, wspace=0.12)
    metodos = list(resumo.index)
    cores = [AZUL if m == destaque else "#c3c2b7" for m in metodos]
    pos = np.arange(len(metodos))
    for ax, coluna, titulo_painel in [(ax1, "economia_km_pct", "Economia de km vs individual"),
                                      (ax2, "no_prazo_pct", "Entregas no prazo")]:
        valores = resumo[coluna].to_numpy()
        barras = ax.barh(pos, valores, height=0.6, color=cores, edgecolor=SUPERFICIE, lw=1.5)
        ax.bar_label(barras, labels=[f"{_formatar(v)}%" for v in valores], padding=4, fontsize=10, color=TINTA)
        ax.set_title(titulo_painel, loc="left", fontsize=11, color=TINTA_SEC, pad=8)
        if coluna == "no_prazo_pct":  # percentual de um total: eixo de 0 a 100%
            ax.set_xlim(0, 115)
            ax.set_xticks(range(0, 101, 25))
        else:
            ax.set_xlim(0, max(valores.max() * 1.25, 10))
        ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.tick_params(axis="y", length=0)
    ax1.set_yticks(pos, [m[0].upper() + m[1:] for m in metodos], fontsize=10.5)
    ax1.invert_yaxis()
    d = resumo.loc[destaque]
    _titulo(fig, f"Com o prazo no modelo, a roteirização economiza {_formatar(d['economia_km_pct'], 0)}% dos km "
                 f"e mantém {_formatar(d['no_prazo_pct'], 0)}% no prazo",
            f"{int(resumo['entregas'].iloc[0]):,} entregas em lotes de 2 h a partir do hub de cada cidade; "
            "até 4 pedidos por viagem".replace(",", "."))
    _nota(fig, "Tempo de chegada determinístico (velocidade média + 3 min por parada): compare os métodos entre si, "
               "não com o OTD real.")
    return fig


def exemplo_rotas(hub: tuple[float, float], lats: np.ndarray, lons: np.ndarray, prazos: np.ndarray,
                  resultados: list, titulo: str) -> Figure:
    """Um painel por método: rotas do mesmo lote; paradas fora do prazo com anel vermelho."""
    aplicar_estilo()
    fig, eixos = plt.subplots(1, len(resultados), figsize=(3.6 * len(resultados), 5.6))
    fig.subplots_adjust(top=0.78, left=0.03, right=0.97, bottom=0.03, wspace=0.15)
    for ax, r in zip(eixos, resultados):
        ax.grid(False)
        for lado in ("bottom", "left"):
            ax.spines[lado].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])
        atrasado = r.chegada_min > prazos
        for k, rota in enumerate(r.rotas):
            cor = CORES_VIAGENS[k % len(CORES_VIAGENS)]
            xs = [hub[1]] + [lons[i - 1] for i in rota] + [hub[1]]
            ys = [hub[0]] + [lats[i - 1] for i in rota] + [hub[0]]
            ax.plot(xs, ys, color=cor, lw=2, zorder=2)
            ax.scatter([lons[i - 1] for i in rota], [lats[i - 1] for i in rota], s=60, color=cor,
                       edgecolor=SUPERFICIE, linewidth=1.5, zorder=3)
        ax.scatter(lons[atrasado], lats[atrasado], s=190, facecolor="none", edgecolor=VERMELHO_STATUS,
                   linewidth=2, zorder=4)
        ax.scatter([hub[1]], [hub[0]], marker="s", s=70, color=TINTA, zorder=5)
        ax.set_aspect(ASPECTO_LAT, adjustable="datalim")
        ax.margins(0.12)
        no_prazo = int((~atrasado).sum())
        ax.set_title(f"{r.metodo[0].upper() + r.metodo[1:]}\n{_formatar(r.km_total)} km · {len(r.rotas)} viagens · "
                     f"{no_prazo}/{len(prazos)} no prazo", fontsize=10.5, color=TINTA, loc="left")
    _titulo(fig, titulo, "Mesmo lote nos três métodos. Quadrado = hub; cada cor = uma viagem; "
                         "anel vermelho = entrega fora do prazo")
    return fig


# ---------------------------------------------------------------------------
# Sensibilidade da roteirização (notebook 06)
# ---------------------------------------------------------------------------
AQUA = "#1baf7a"


def curva_troca_penalidade(sens: pd.DataFrame, titulo: str) -> Figure:
    """Economia de km (x) x entregas no prazo (y): um ponto por penalidade + métodos de referência."""
    fig, ax = _nova_figura(9.0, 5.4)
    fig.subplots_adjust(top=0.82, left=0.1, right=0.96, bottom=0.14)
    pen = sens[sens["analise"] == "penalidade"]
    curva = pen[pen["metodo"] == "OR-Tools com prazo"].assign(p=lambda d: d["valor"].astype(float)).sort_values("p")
    ax.plot(curva["economia_km_pct"], curva["no_prazo_pct"], color=AZUL, lw=2, marker="o", ms=7,
            mec=SUPERFICIE, mew=1.5, zorder=3, label="OR-Tools com prazo")
    for linha in curva[curva["p"].isin([0.25, 2.0, 30.0])].itertuples(index=False):  # rótulos seletivos
        ax.annotate(f"{_formatar(linha.p, 2 if linha.p < 1 else 0)} km/min", (linha.economia_km_pct, linha.no_prazo_pct),
                    xytext=(7, -3), textcoords="offset points", fontsize=8.5, color=TINTA_SEC)
    refs = pen[(pen["valor"].astype(float) == 0) & (pen["metodo"] != "OR-Tools com prazo")]
    for linha in refs.itertuples(index=False):
        ax.scatter(linha.economia_km_pct, linha.no_prazo_pct, s=55, color=CINZA, zorder=3)
        ax.annotate(linha.metodo[0].upper() + linha.metodo[1:], (linha.economia_km_pct, linha.no_prazo_pct),
                    xytext=(7, 4), textcoords="offset points", fontsize=9.5, color=TINTA_SEC)
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_xlabel("Economia de km vs viagens individuais")
    ax.set_ylabel("Entregas no prazo")
    ax.grid(axis="x", visible=True)
    ax.set_xlim(-2, max(40, pen["economia_km_pct"].max() + 6))
    _titulo(fig, titulo, "Cada ponto azul é uma penalidade de atraso (quantos km \"vale\" 1 minuto de atraso)")
    n_entregas = f"{int(pen['entregas'].iloc[0]):,}".replace(",", ".")
    _nota(fig, f"Amostra de {n_entregas} entregas em 200 lotes de 2 h, até 4 pedidos por viagem, "
               "sem contar a espera do lote.")
    return fig


def _paineis(n: int, largura: float = 11.0, altura: float = 4.4) -> tuple[Figure, list]:
    aplicar_estilo()
    fig, eixos = plt.subplots(1, n, figsize=(largura, altura))
    fig.subplots_adjust(top=0.72, left=0.07, right=0.98, bottom=0.16, wspace=0.28)
    return fig, list(np.atleast_1d(eixos))


def sensibilidade_capacidade(sens: pd.DataFrame, titulo: str) -> Figure:
    """Dois painéis: economia de km e entregas no prazo por capacidade da moto."""
    fig, (ax1, ax2) = _paineis(2, 10.0)
    cap = sens[(sens["analise"] == "capacidade") & (sens["metodo"] == "OR-Tools com prazo")].copy()
    cap["c"] = cap["valor"].astype(float).astype(int)
    cap = cap.sort_values("c")
    for ax, coluna, painel in [(ax1, "economia_km_pct", "Economia de km"), (ax2, "no_prazo_pct", "Entregas no prazo")]:
        ax.plot(cap["c"], cap[coluna], color=AZUL, lw=2, marker="o", ms=7, mec=SUPERFICIE, mew=1.5)
        for x, y in zip(cap["c"], cap[coluna]):
            ax.annotate(f"{_formatar(y)}%", (x, y), xytext=(0, 8), textcoords="offset points", ha="center",
                        fontsize=9, color=TINTA)
        ax.set_title(painel, loc="left", fontsize=11, color=TINTA_SEC, pad=10)
        ax.set_xticks(cap["c"])
        ax.set_xlabel("Pedidos por moto (capacidade)")
        ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax1.set_ylim(0, max(50, cap["economia_km_pct"].max() * 1.25))
    ax2.set_ylim(80, 100.5)
    _titulo(fig, titulo, "OR-Tools com prazo (penalidade de 2 km por minuto), lotes de 2 h, sem contar a espera")
    return fig


def sensibilidade_janela(sens: pd.DataFrame, titulo: str) -> Figure:
    """Três painéis por janela do lote (com espera): economia, no prazo e cobertura; uma linha por volume."""
    fig, eixos = _paineis(3, 12.0, 4.6)
    jan = sens[sens["analise"] == "janela"]
    ordem = ["15min", "30min", "1h", "2h"]
    rotulos = ["15 min", "30 min", "1 h", "2 h"]
    cores = dict(zip(jan["volume"].dropna().unique(), [AZUL, AQUA]))
    x = np.arange(len(ordem))
    paineis = [("economia_km_pct", "Economia de km (nos lotes)", "OR-Tools com prazo"),
               ("no_prazo_pct", "Entregas no prazo", "OR-Tools com prazo"),
               ("cobertura_pct", "Entregas que formam lote", "OR-Tools com prazo")]
    for ax, (coluna, painel, metodo) in zip(eixos, paineis):
        for volume, cor in cores.items():
            serie = (jan[(jan["volume"] == volume) & (jan["metodo"] == metodo)]
                     .set_index("valor")[coluna].reindex(ordem))
            ax.plot(x, serie.to_numpy(), color=cor, lw=2, marker="o", ms=7, mec=SUPERFICIE, mew=1.5, label=volume)
        ax.set_xticks(x, rotulos)
        ax.set_title(painel, loc="left", fontsize=11, color=TINTA_SEC, pad=10)
        ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
        ax.set_xlabel("Janela do lote")
    ind = jan[(jan["metodo"] == "individual")].groupby("valor")["no_prazo_pct"].mean().reindex(ordem)
    eixos[1].plot(x, ind.to_numpy(), color=CINZA, lw=1.5, ls="--", label="individual (sai na hora)")
    eixos[0].set_ylim(0, None)
    eixos[1].set_ylim(0, 105)
    eixos[2].set_ylim(0, 105)
    eixos[1].legend(loc="lower left", fontsize=9)
    _titulo(fig, titulo, "OR-Tools com prazo contando a espera até o despacho (fim da janela); lotes de 2+ pedidos")
    _nota(fig, "Volume 4x: base simulada com as mesmas regras e 20.000 pedidos no mesmo período.")
    return fig
