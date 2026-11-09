"""Dados e filtros do dashboard.

Os filtros ficam na barra lateral e valem para todas as páginas. O estado é guardado em
`st.session_state` e espelhado no endereço da página (`st.query_params`), para que um link
compartilhado abra com os mesmos filtros. "Limpar filtros" volta tudo ao padrão.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from logistica_rotas.dashboard.graficos import FAIXAS_KM, FAIXAS_ROTULO, STATUS_ORDEM, STATUS_ROTULO
from logistica_rotas.ingestao.leitura import carregar_entregas
from logistica_rotas.limpeza.tratamento import limpar_entregas
from logistica_rotas.metricas.kpis import mascara_concluidas, taxa_atraso, taxa_cancelamento, taxa_otd

TOP_BAIRROS = 12
OPCOES_PICO = ["Todos", "Pico", "Fora do pico"]
OPCOES_DIA = ["Todos", "Dia útil", "Fim de semana"]
SEPARADOR = "|"  # separa itens de lista no endereço da página


@st.cache_data
def obter_dados() -> pd.DataFrame:
    """Base limpa (outliers de tempo tratados, notebook 02), com colunas de apoio do dashboard."""
    df = limpar_entregas(carregar_entregas())
    df["faixa_distancia"] = pd.cut(df["distancia_km"], bins=FAIXAS_KM, labels=FAIXAS_ROTULO, right=False)
    df["data"] = df["data_hora_pedido"].dt.date
    return df


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def calcular_kpis(df: pd.DataFrame) -> dict[str, float]:
    """KPIs do topo (regras em metricas/kpis.py): concluídas sem cancelados e sem tempo inválido."""
    concluidas = df[mascara_concluidas(df)]
    return {
        "total": len(df),
        "concluidas": len(concluidas),
        "otd_%": taxa_otd(df),
        "taxa_atraso_%": taxa_atraso(df),
        "tempo_medio_min": concluidas["tempo_transito_min"].mean(),
        "tempo_mediano_min": concluidas["tempo_transito_min"].median(),
        "cancelamento_%": taxa_cancelamento(df),
        "valor_medio_brl": df["valor_entrega_brl"].mean(),
    }


def resumo_bairros(df: pd.DataFrame, coluna: str, top: int = TOP_BAIRROS) -> pd.DataFrame:
    """Entregas e taxa de atraso (sobre concluídas) por bairro; os `top` de maior volume."""
    concl = df[mascara_concluidas(df)]
    return pd.DataFrame({
        "entregas": df.groupby(coluna, observed=True).size(),
        "atraso_%": concl.groupby(coluna, observed=True)["status"].apply(lambda s: (s == "com_atraso").mean() * 100),
    }).query("entregas > 0").nlargest(top, "entregas").sort_values("entregas")


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------
@dataclass
class Filtros:
    status: list[str]
    cidades_origem: list[str]
    cidades_destino: list[str]
    bairros_origem: list[str]
    bairros_destino: list[str]
    inicio: date
    fim: date
    pico: str
    dia: str


def _padroes(dados: pd.DataFrame) -> dict:
    return {
        "f_status": list(STATUS_ORDEM), "f_cid_o": [], "f_cid_d": [], "f_bai_o": [], "f_bai_d": [],
        "f_periodo": (dados["data"].min(), dados["data"].max()), "f_pico": "Todos", "f_dia": "Todos",
    }


# chave no session_state -> nome no endereço da página
_URL = {"f_status": "status", "f_cid_o": "cid_o", "f_cid_d": "cid_d", "f_bai_o": "bai_o", "f_bai_d": "bai_d",
        "f_pico": "pico", "f_dia": "dia"}


def _ler_url(dados: pd.DataFrame) -> dict:
    """Valores válidos vindos do endereço da página (o que for inválido é ignorado)."""
    qp = st.query_params
    validos = {
        "f_status": set(STATUS_ORDEM),
        "f_cid_o": set(dados["cidade_origem"].astype(str)), "f_cid_d": set(dados["cidade_destino"].astype(str)),
        "f_bai_o": set(dados["local_origem"]), "f_bai_d": set(dados["local_destino"]),
    }
    lido = {}
    for chave, nome in _URL.items():
        if nome not in qp:
            continue
        if chave in validos:
            itens = [v for v in qp[nome].split(SEPARADOR) if v in validos[chave]]
            if itens:
                lido[chave] = itens
        elif chave == "f_pico" and qp[nome] in OPCOES_PICO:
            lido[chave] = qp[nome]
        elif chave == "f_dia" and qp[nome] in OPCOES_DIA:
            lido[chave] = qp[nome]
    if "de" in qp and "ate" in qp:
        try:
            de, ate = date.fromisoformat(qp["de"]), date.fromisoformat(qp["ate"])
            minimo, maximo = dados["data"].min(), dados["data"].max()
            if minimo <= de <= ate <= maximo:
                lido["f_periodo"] = (de, ate)
        except ValueError:
            pass
    return lido


def _escrever_url(dados: pd.DataFrame) -> None:
    """Espelha no endereço da página só os filtros diferentes do padrão."""
    padroes = _padroes(dados)
    novo = {}
    for chave, nome in _URL.items():
        valor = st.session_state.get(chave)
        if valor is None or valor == padroes[chave]:
            continue
        novo[nome] = SEPARADOR.join(valor) if isinstance(valor, list) else str(valor)
    periodo = st.session_state.get("f_periodo")
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2 and tuple(periodo) != padroes["f_periodo"]:
        novo["de"], novo["ate"] = periodo[0].isoformat(), periodo[1].isoformat()
    if dict(st.query_params) != novo:
        st.query_params.from_dict(novo)


def limpar_filtros(dados: pd.DataFrame) -> None:
    """Volta todos os filtros ao padrão (usado como callback do botão)."""
    for chave, valor in _padroes(dados).items():
        st.session_state[chave] = valor
    st.query_params.clear()


def _iniciar_estado(dados: pd.DataFrame) -> None:
    """Na primeira execução da sessão, carrega padrões + o que vier no endereço da página."""
    if st.session_state.get("_filtros_iniciados"):
        return
    estado = {**_padroes(dados), **_ler_url(dados)}
    for chave, valor in estado.items():
        st.session_state[chave] = valor
    st.session_state["_filtros_iniciados"] = True


def _podar(chave: str, opcoes: list[str]) -> None:
    """Remove da seleção itens que deixaram de ser opção (ex.: bairro de cidade desmarcada)."""
    atual = st.session_state.get(chave, [])
    st.session_state[chave] = [v for v in atual if v in opcoes]


def barra_lateral(dados: pd.DataFrame) -> Filtros:
    """Desenha os filtros na barra lateral e devolve as escolhas."""
    _iniciar_estado(dados)
    with st.sidebar:
        st.header("Filtros")
        st.button("Limpar filtros", icon=":material/filter_alt_off:", on_click=limpar_filtros, args=(dados,),
                  width="stretch")
        minimo, maximo = dados["data"].min(), dados["data"].max()
        st.date_input("Período", min_value=minimo, max_value=maximo, key="f_periodo", format="DD/MM/YYYY")
        st.segmented_control("Horário", OPCOES_PICO, key="f_pico", help="Pico de trânsito: 7h-8h e 17h-19h em dias úteis.")
        st.segmented_control("Dia", OPCOES_DIA, key="f_dia")
        st.multiselect("Status da entrega", options=STATUS_ORDEM, format_func=STATUS_ROTULO.get, key="f_status")
        cidades = sorted(set(dados["cidade_origem"].astype(str)) | set(dados["cidade_destino"].astype(str)))
        st.multiselect("Cidade de origem", options=cidades, placeholder="Todas", key="f_cid_o")
        st.multiselect("Cidade de destino", options=cidades, placeholder="Todas", key="f_cid_d")
        base_o = dados[dados["cidade_origem"].isin(st.session_state["f_cid_o"])] if st.session_state["f_cid_o"] else dados
        base_d = dados[dados["cidade_destino"].isin(st.session_state["f_cid_d"])] if st.session_state["f_cid_d"] else dados
        opcoes_o, opcoes_d = sorted(base_o["local_origem"].unique()), sorted(base_d["local_destino"].unique())
        _podar("f_bai_o", opcoes_o)
        _podar("f_bai_d", opcoes_d)
        st.multiselect("Bairro de origem", options=opcoes_o, placeholder="Todos", key="f_bai_o")
        st.multiselect("Bairro de destino", options=opcoes_d, placeholder="Todos", key="f_bai_d")
        st.divider()
        st.caption(
            "Dados simulados: 5.000 pedidos (set-out/2026) no ABC paulista e em Mauá. "
            "Bairros e ruas reais; 43 de 45 bairros com coordenada do OpenStreetMap. "
            "Pedidos, tempos e valores são simulados. Os filtros ficam no endereço da página: "
            "copie o link para compartilhar esta visão."
        )
    _escrever_url(dados)
    periodo = st.session_state["f_periodo"]
    inicio, fim = (periodo[0], periodo[1]) if isinstance(periodo, (tuple, list)) and len(periodo) == 2 \
        else (periodo[0] if isinstance(periodo, (tuple, list)) and periodo else minimo, maximo)
    return Filtros(
        status=st.session_state["f_status"], cidades_origem=st.session_state["f_cid_o"],
        cidades_destino=st.session_state["f_cid_d"], bairros_origem=st.session_state["f_bai_o"],
        bairros_destino=st.session_state["f_bai_d"], inicio=inicio, fim=fim,
        pico=st.session_state.get("f_pico") or "Todos", dia=st.session_state.get("f_dia") or "Todos",
    )


def aplicar_filtros(dados: pd.DataFrame, f: Filtros, inicio: date | None = None, fim: date | None = None) -> pd.DataFrame:
    """Aplica os filtros. `inicio`/`fim` substituem o período (usado no período anterior)."""
    inicio, fim = inicio or f.inicio, fim or f.fim
    m = dados["status"].isin(f.status) & dados["data"].between(inicio, fim)
    if f.cidades_origem:
        m &= dados["cidade_origem"].isin(f.cidades_origem)
    if f.cidades_destino:
        m &= dados["cidade_destino"].isin(f.cidades_destino)
    if f.bairros_origem:
        m &= dados["local_origem"].isin(f.bairros_origem)
    if f.bairros_destino:
        m &= dados["local_destino"].isin(f.bairros_destino)
    if f.pico != "Todos":
        m &= dados["horario_pico"] == ("sim" if f.pico == "Pico" else "nao")
    if f.dia != "Todos":
        m &= dados["dia_util"] == (f.dia == "Dia útil")
    return dados[m]


COBERTURA_MINIMA = 0.8  # o período anterior precisa ter ao menos 80% do tamanho do atual


def periodo_anterior(dados: pd.DataFrame, f: Filtros) -> tuple[pd.DataFrame, int] | None:
    """Mesmos filtros no período de mesmo tamanho imediatamente anterior, e quantos dias ele tem nos dados.

    Se o início cair antes dos dados, o período é cortado; None se sobrar menos de 80% do tamanho.
    Contagens (como entregas) devem ser comparadas por dia, porque os tamanhos podem diferir um pouco.
    """
    dias = (f.fim - f.inicio).days + 1
    fim_ant = f.inicio - timedelta(days=1)
    inicio_ant = max(f.inicio - timedelta(days=dias), dados["data"].min())
    dias_ant = (fim_ant - inicio_ant).days + 1
    if dias_ant < COBERTURA_MINIMA * dias:
        return None
    return aplicar_filtros(dados, f, inicio_ant, fim_ant), dias_ant
