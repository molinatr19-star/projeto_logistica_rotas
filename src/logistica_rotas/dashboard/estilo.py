"""Estilo do dashboard: paleta neon (dark mode), CSS e componentes HTML (cartões e títulos)."""

import pandas as pd
import streamlit as st

# Paleta neon. Status mantém o significado: verde = no prazo, amarelo/laranja = atraso,
# vermelho = cancelado. Azul e ciano são as cores de volume/série.
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

META_OTD_PCT = 95.0  # meta de entregas no prazo exibida nos cartões


def aplicar_css() -> None:
    """Injeta o CSS do dashboard (cartões de KPI neon, cartões de gráfico, abas em pílula)."""
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

        /* Variação vs período anterior e selo de meta nos cartões de KPI */
        .kpi-delta {{font-size: clamp(.62rem, 6.2cqi, .76rem); margin-top: .3rem; font-weight: 600; white-space: nowrap;}}
        .kpi-delta.bom {{color: {NEON_VERDE};}}
        .kpi-delta.ruim {{color: {NEON_VERMELHO};}}
        .kpi-delta.neutro {{color: {COR_MUTED};}}
        .kpi-selo {{display: inline-block; margin-left: .4rem; padding: 0 .45rem; border-radius: 999px; font-size: .7rem;
            font-weight: 700; border: 1px solid currentColor;}}
        .kpi-selo.bom {{color: {NEON_VERDE};}}
        .kpi-selo.ruim {{color: {NEON_VERMELHO};}}
        .glossario dt {{color: {COR_TEXTO}; font-weight: 700; margin-top: .5rem;}}
        .glossario dd {{color: {COR_TEXTO_SEC}; margin-left: 0;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def formatar(valor: float, casas: int = 1, sufixo: str = "") -> str:
    """Número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    if pd.isna(valor):
        return "-"
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto + sufixo


def cartao_kpi(rotulo: str, valor: str, nota: str, cor: str, unidade: str = "", dica: str = "",
               prefixo: str = "", delta: str = "", delta_bom: bool | None = None, selo: str = "",
               selo_bom: bool | None = None) -> str:
    """Cartão de KPI com borda neon.

    `delta`: variação contra o período anterior (texto pronto); `delta_bom` define a cor (verde/vermelho).
    `selo`: indicador de meta (ex.: "acima da meta"), com ícone e cor pelo `selo_bom`.
    """
    unidade_html = f"<small>{unidade}</small>" if unidade else ""
    prefixo_html = f'<small class="prefixo">{prefixo}</small>' if prefixo else ""
    classe = {True: "bom", False: "ruim", None: "neutro"}
    delta_html = f'<div class="kpi-delta {classe[delta_bom]}">{delta}</div>' if delta else ""
    icone = {True: "✔", False: "✖", None: "•"}[selo_bom]
    selo_html = f'<span class="kpi-selo {classe[selo_bom]}">{icone} {selo}</span>' if selo else ""
    return (
        f'<div class="kpi" style="--acc:{cor}" title="{dica}">'
        f'<div class="kpi-rotulo"><span class="kpi-ponto"></span>{rotulo}</div>'
        f'<div class="kpi-valor">{prefixo_html}{valor}{unidade_html}</div>'
        f'<div class="kpi-nota">{nota}{selo_html}</div>{delta_html}</div>'
    )


def titulo_cartao(titulo: str, nota: str = "") -> None:
    """Título e nota de um cartão de gráfico."""
    nota_html = f'<div class="card-nota">{nota}</div>' if nota else ""
    st.markdown(f'<div class="card-titulo">{titulo}</div>{nota_html}', unsafe_allow_html=True)

def cabecalho(titulo: str, subtitulo: str) -> None:
    """Título da página em degradê com selo 'dados simulados'."""
    st.markdown(
        f'<h1 class="titulo">{titulo}<span class="selo">dados simulados</span></h1>'
        f'<div class="subtitulo">{subtitulo}</div>',
        unsafe_allow_html=True,
    )
