"""Testes do dashboard Streamlit (app.py + paginas/) com o testador oficial (AppTest)."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT = 180


def abrir(**query_params) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    for chave, valor in query_params.items():
        at.query_params[chave] = valor
    return at.run()


def textos_kpi(at: AppTest, classe: str = "kpi-valor") -> list[str]:
    html = " ".join(m.value for m in at.markdown)
    return re.findall(rf'class="{classe}[^"]*">(.*?)</div>', html)


def entregas(at: AppTest) -> int:
    valor = re.sub(r"<[^>]+>", "", textos_kpi(at)[0])
    return int(valor.replace(".", ""))


def test_visao_geral_abre_com_cinco_cartoes():
    at = abrir()
    assert not at.exception
    assert len(textos_kpi(at)) == 5
    assert entregas(at) == 5000


@pytest.mark.parametrize("pagina", ["paginas/desempenho.py", "paginas/mapa.py", "paginas/simulador.py"])
def test_paginas_abrem_sem_erro(pagina):
    at = abrir()
    at.switch_page(pagina).run()
    assert not at.exception


def test_filtro_vindo_do_endereco_da_pagina():
    at = abrir(cid_o="Mauá")
    assert at.multiselect(key="f_cid_o").value == ["Mauá"]
    assert 0 < entregas(at) < 5000


def test_valor_invalido_no_endereco_e_ignorado():
    at = abrir(cid_o="Cidade Inexistente", pico="Talvez", de="2020-01-01", ate="2020-01-31")
    assert not at.exception
    assert at.multiselect(key="f_cid_o").value == []
    assert entregas(at) == 5000


def test_limpar_filtros_volta_ao_padrao():
    at = abrir(cid_o="Mauá")
    botao = next(b for b in at.button if b.label == "Limpar filtros")
    botao.click().run()
    assert at.multiselect(key="f_cid_o").value == []
    assert entregas(at) == 5000
    assert "cid_o" not in at.query_params


def test_filtro_escrito_no_endereco_da_pagina():
    at = abrir()
    at.multiselect(key="f_cid_d").set_value(["Diadema"]).run()
    assert at.query_params["cid_d"] == ["Diadema"] or at.query_params["cid_d"] == "Diadema"


def test_sem_entregas_mostra_aviso():
    at = abrir()
    at.multiselect(key="f_status").set_value([]).run()
    assert any("Nenhuma entrega" in w.value for w in at.warning)


def test_variacao_vs_periodo_anterior_aparece_em_outubro():
    at = abrir(de="2026-10-01", ate="2026-10-31")
    deltas = textos_kpi(at, "kpi-delta")
    assert len(deltas) == 5
    assert all("vs anterior" in d for d in deltas)


def test_simulador_economia_e_prazo():
    at = abrir()
    at.switch_page("paginas/simulador.py").run()
    at.slider(key="sim_espera").set_value(0).run()
    assert not at.exception
    valores = [re.sub(r"<[^>]+>", "", v) for v in textos_kpi(at)]
    economia = float(valores[0].replace("%", "").replace(",", "."))
    assert 0 <= economia < 1  # sem espera, quase nada se agrupa
