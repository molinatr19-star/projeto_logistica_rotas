"""Gerador de dataset simulado de entregas urbanas de moto.

Cidade e bairros são fictícios. As distâncias vêm de um mapa simplificado
(centro de cada bairro em coordenadas x, y em km) multiplicado por um fator
de tortuosidade, para imitar o trajeto real pelas ruas.

Uso pela linha de comando (na raiz do projeto):
    python -m logistica_rotas.ingestao.simulacao
(com `src` no PYTHONPATH) ou chamando `gerar_e_salvar()` no notebook.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
CAMINHO_PADRAO = RAIZ_PROJETO / "data" / "raw" / "dados_entregas_simulados.csv"
FUSO = "America/Sao_Paulo"

# Centro de cada bairro em um plano fictício (km) e peso como origem
# (comércio: restaurantes, farmácias, lojas) e como destino (residências).
BAIRROS = pd.DataFrame(
    [
        # bairro,            x,    y,  peso_origem, peso_destino
        ("Centro",            0.0,   0.0, 0.30, 0.08),
        ("Vila Nova",         1.5,   0.6, 0.12, 0.10),
        ("Jardim América",   -1.8,   1.2, 0.08, 0.12),
        ("Zona Industrial",   3.0,  -2.1, 0.05, 0.03),
        ("Parque Universitário",  -0.9,  -2.4, 0.10, 0.12),
        ("Jardim das Flores",   2.4,   2.7, 0.06, 0.11),
        ("Vila Operária",    -3.3,  -0.9, 0.05, 0.12),
        ("Alto da Colina",    0.6,   3.6, 0.07, 0.10),
        ("Bela Vista",       -2.4,   3.0, 0.07, 0.11),
        ("Porto Seco",        4.2,   0.3, 0.10, 0.11),
    ],
    columns=["bairro", "x_km", "y_km", "peso_origem", "peso_destino"],
)

# Demanda por hora do dia (8h às 23h): picos no almoço e no jantar.
PESO_HORA = {
    8: 2, 9: 3, 10: 4, 11: 8, 12: 10, 13: 8, 14: 4, 15: 3,
    16: 3, 17: 5, 18: 8, 19: 10, 20: 9, 21: 6, 22: 3, 23: 1,
}
# Horário de pico de trânsito em dias úteis.
HORAS_PICO_TRANSITO = {7, 8, 17, 18, 19}

FATOR_TORTUOSIDADE = 1.3  # rua não é linha reta
VELOCIDADE_NORMAL_KMH = 28.0
VELOCIDADE_PICO_KMH = 18.0
TAXA_BASE_BRL = 5.99
TAXA_POR_KM_BRL = 1.50
ADICIONAL_PICO = 0.20  # +20% no valor em horário de pico
PROB_CANCELAMENTO = 0.04
PROB_CANCELAMENTO_PICO = 0.07
PROB_OUTLIER_TEMPO = 0.005  # erro de registro proposital, para a etapa de limpeza


def _sortear_datas(rng: np.random.Generator, n: int, inicio: str, dias: int) -> pd.Series:
    """Sorteia data e hora dos pedidos seguindo a curva de demanda por hora."""
    horas = np.array(list(PESO_HORA.keys()))
    pesos = np.array(list(PESO_HORA.values()), dtype=float)
    hora = rng.choice(horas, size=n, p=pesos / pesos.sum())
    dia = rng.integers(0, dias, size=n)
    minuto = rng.integers(0, 60, size=n)
    base = pd.Timestamp(inicio, tz=FUSO)
    return pd.Series(
        base
        + pd.to_timedelta(dia, unit="D")
        + pd.to_timedelta(hora, unit="h")
        + pd.to_timedelta(minuto, unit="min")
    )


def _calcular_distancia_km(rng: np.random.Generator, origem: np.ndarray, destino: np.ndarray) -> np.ndarray:
    """Distância pelas ruas: reta entre pontos sorteados nos bairros x tortuosidade."""
    coords = BAIRROS.set_index("bairro")[["x_km", "y_km"]]
    xy_o = coords.loc[origem].to_numpy() + rng.uniform(-1.0, 1.0, size=(len(origem), 2))
    xy_d = coords.loc[destino].to_numpy() + rng.uniform(-1.0, 1.0, size=(len(destino), 2))
    reta = np.linalg.norm(xy_o - xy_d, axis=1)
    return np.maximum(reta * FATOR_TORTUOSIDADE, 0.5)


def gerar_entregas(n: int = 5000, inicio: str = "2026-09-01", dias: int = 61, random_state: int = 42) -> pd.DataFrame:
    """Gera um DataFrame com `n` entregas simuladas de moto."""
    rng = np.random.default_rng(random_state)

    data_hora = _sortear_datas(rng, n, inicio, dias).sort_values(ignore_index=True)
    dia_util = data_hora.dt.dayofweek < 5
    horario_pico = dia_util & data_hora.dt.hour.isin(HORAS_PICO_TRANSITO)

    p_o = BAIRROS["peso_origem"] / BAIRROS["peso_origem"].sum()
    p_d = BAIRROS["peso_destino"] / BAIRROS["peso_destino"].sum()
    origem = rng.choice(BAIRROS["bairro"], size=n, p=p_o)
    destino = rng.choice(BAIRROS["bairro"], size=n, p=p_d)
    distancia_km = _calcular_distancia_km(rng, origem, destino)

    # Tempo = deslocamento + tempo fixo de coleta/entrega, com variação aleatória.
    velocidade = np.where(horario_pico, VELOCIDADE_PICO_KMH, VELOCIDADE_NORMAL_KMH)
    velocidade = velocidade * rng.lognormal(0.0, 0.30, size=n)
    tempo_fixo = rng.lognormal(np.log(6.0), 0.35, size=n)
    tempo_transito_min = distancia_km / velocidade * 60 + tempo_fixo

    outlier = rng.random(n) < PROB_OUTLIER_TEMPO
    tempo_transito_min = np.where(outlier, tempo_transito_min * rng.uniform(4, 8, size=n), tempo_transito_min)

    # Prazo prometido ao cliente: 12 min + 2,5 min/km, arredondado para múltiplo de 5.
    prazo_prometido_min = np.ceil((12 + 2.5 * distancia_km) / 5) * 5

    valor = TAXA_BASE_BRL + TAXA_POR_KM_BRL * distancia_km
    valor = np.where(horario_pico, valor * (1 + ADICIONAL_PICO), valor)

    p_cancel = np.where(horario_pico, PROB_CANCELAMENTO_PICO, PROB_CANCELAMENTO)
    cancelado = rng.random(n) < p_cancel
    status = np.where(tempo_transito_min > prazo_prometido_min, "com_atraso", "entregue")
    status = np.where(cancelado, "cancelado", status)
    tempo_transito_min = np.where(cancelado, np.nan, tempo_transito_min)

    return pd.DataFrame(
        {
            "id_pedido": [f"PED{i:06d}" for i in range(1, n + 1)],
            "data_hora_pedido": data_hora,
            "bairro_origem": origem,
            "bairro_destino": destino,
            "distancia_km": distancia_km.round(2),
            "horario_pico": np.where(horario_pico, "sim", "nao"),
            "tempo_transito_min": np.round(tempo_transito_min, 1),
            "prazo_prometido_min": prazo_prometido_min.astype(int),
            "valor_entrega_brl": valor.round(2),
            "status": status,
        }
    )


def gerar_e_salvar(caminho: Path = CAMINHO_PADRAO, **kwargs) -> Path:
    """Gera o dataset e salva em CSV (UTF-8). Retorna o caminho do arquivo."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    gerar_entregas(**kwargs).to_csv(caminho, index=False, encoding="utf-8")
    return caminho


if __name__ == "__main__":
    arquivo = gerar_e_salvar()
    print(f"Dataset salvo em: {arquivo}")
