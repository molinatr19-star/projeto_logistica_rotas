"""Dashboard interativo de entregas de moto no ABC paulista e em Mauá (dados simulados).

Executar na raiz do projeto:
    .venv\\Scripts\\python.exe -m streamlit run app.py

Estrutura:
- app.py: configuração, estilo, filtros da barra lateral (valem para todas as páginas) e navegação;
- paginas/: Visão geral, Desempenho, Mapa e Simulador;
- src/logistica_rotas/dashboard/: estilo, gráficos, dados e filtros compartilhados.
"""

import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from logistica_rotas.dashboard.dados import barra_lateral, obter_dados  # noqa: E402
from logistica_rotas.dashboard.estilo import aplicar_css  # noqa: E402

st.set_page_config(page_title="Logística de Entregas", page_icon=":material/two_wheeler:", layout="wide")
aplicar_css()

paginas = st.navigation([
    st.Page("paginas/visao_geral.py", title="Visão geral", icon=":material/dashboard:", default=True),
    st.Page("paginas/desempenho.py", title="Desempenho", icon=":material/insights:"),
    st.Page("paginas/mapa.py", title="Mapa", icon=":material/map:"),
    st.Page("paginas/simulador.py", title="Simulador de despacho", icon=":material/route:"),
])

# Filtros na barra lateral: valem para todas as páginas (o simulador usa a operação inteira).
st.session_state["_filtros"] = barra_lateral(obter_dados())

paginas.run()
