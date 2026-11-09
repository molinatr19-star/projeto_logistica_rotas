"""Gerador de dataset simulado de entregas urbanas de moto no ABC paulista e em Mauá.

O que é real e o que é simulado:
- Real: municípios (Santo André, São Bernardo do Campo, São Caetano do Sul,
  Diadema e Mauá), nomes de bairros e nomes de vias de cada município.
- Aproximado: coordenada do centro de cada município (WGS84).
- Simulado: posição de cada bairro dentro do município (sorteada com seed fixa,
  NÃO geocodificada), pedidos, horários, tempos, valores e status.
- A rua do endereço é sorteada entre vias reais do mesmo município do destino;
  a combinação rua x bairro não foi verificada e pode não existir.

Distância = haversine (linha reta) entre os pontos x fator de tortuosidade.

Uso pela linha de comando (na raiz do projeto):
    .venv\\Scripts\\python.exe -m logistica_rotas.ingestao.simulacao
(com `src` no PYTHONPATH) ou chamando `gerar_e_salvar()` no notebook.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
CAMINHO_PADRAO = RAIZ_PROJETO / "data" / "raw" / "dados_entregas_simulados.csv"
FUSO = "America/Sao_Paulo"

# ---------------------------------------------------------------------------
# Geografia
# lat/lon: centro aproximado do município (verificar antes de usar em mapas).
# raio_km: raio usado para espalhar os bairros em volta do centro.
# peso: participação aproximada na demanda (proporcional ao porte da cidade).
# ---------------------------------------------------------------------------
CIDADES = {
    "Santo André": {
        "lat": -23.6639, "lon": -46.5383, "raio_km": 3.5, "peso": 0.27,
        "bairros": ["Centro", "Vila Assunção", "Bairro Jardim", "Campestre", "Vila Bastos",
                    "Utinga", "Vila Luzita", "Parque das Nações", "Vila Guiomar", "Casa Branca"],
        "ruas": ["Rua Coronel Oliveira Lima", "Rua Senador Fláquer", "Avenida Portugal",
                 "Avenida Industrial", "Avenida Dom Pedro II", "Avenida Pereira Barreto",
                 "Rua das Figueiras", "Avenida Queirós dos Santos", "Avenida Lino Jardim",
                 "Avenida dos Estados"],
    },
    "São Bernardo do Campo": {
        "lat": -23.6939, "lon": -46.5650, "raio_km": 3.5, "peso": 0.30,
        "bairros": ["Centro", "Rudge Ramos", "Baeta Neves", "Nova Petrópolis", "Assunção",
                    "Planalto", "Demarchi", "Ferrazópolis", "Jardim do Mar", "Paulicéia"],
        "ruas": ["Rua Marechal Deodoro", "Avenida Kennedy", "Avenida Senador Vergueiro",
                 "Rua Jurubatuba", "Avenida Faria Lima", "Avenida Lucas Nogueira Garcez",
                 "Avenida Caminho do Mar", "Avenida Winston Churchill"],
    },
    "São Caetano do Sul": {
        "lat": -23.6229, "lon": -46.5548, "raio_km": 1.8, "peso": 0.11,
        "bairros": ["Centro", "Santa Paula", "Barcelona", "Santa Maria", "Cerâmica",
                    "Fundação", "Osvaldo Cruz", "Olímpico", "Nova Gerty"],
        "ruas": ["Rua Manoel Coelho", "Avenida Goiás", "Rua Santa Catarina",
                 "Avenida Presidente Kennedy", "Rua Alegre", "Rua Baraldi",
                 "Avenida Senador Roberto Simonsen", "Rua Amazonas"],
    },
    "Diadema": {
        "lat": -23.6813, "lon": -46.6205, "raio_km": 2.5, "peso": 0.16,
        "bairros": ["Centro", "Piraporinha", "Serraria", "Eldorado", "Taboão",
                    "Canhema", "Campanário", "Conceição"],
        "ruas": ["Avenida Antônio Piranga", "Avenida Alda", "Avenida Fábio Eduardo Ramos Esquível",
                 "Avenida Conceição", "Avenida Piraporinha", "Rua Manoel da Nóbrega"],
    },
    "Mauá": {
        "lat": -23.6678, "lon": -46.4613, "raio_km": 3.0, "peso": 0.16,
        "bairros": ["Centro", "Vila Noêmia", "Barão de Mauá", "Jardim Zaíra", "Parque São Vicente",
                    "Vila Bocaina", "Jardim Itapeva", "Matriz"],
        "ruas": ["Avenida Barão de Mauá", "Avenida Capitão João", "Avenida Itapark",
                 "Rua Gabriel Marques", "Avenida Antônia Rosa Fioravante"],
    },
}

SEED_GEOGRAFIA = 2026      # posição dos bairros: fixa e independente dos pedidos
PESO_CENTRO_ORIGEM = 3.0   # Centro concentra comércio: mais coletas
PROB_MESMA_CIDADE = 0.80   # a maioria das entregas de moto fica no mesmo município
JITTER_KM = 0.6            # ponto exato da coleta/entrega dentro do bairro
KM_POR_GRAU_LAT = 111.32


def _montar_bairros() -> pd.DataFrame:
    """Tabela de bairros com posição simulada (lat/lon) em volta do centro da cidade."""
    rng = np.random.default_rng(SEED_GEOGRAFIA)
    linhas = []
    for cidade, info in CIDADES.items():
        km_por_grau_lon = KM_POR_GRAU_LAT * np.cos(np.radians(info["lat"]))
        for bairro in info["bairros"]:
            if bairro == "Centro":
                dx = dy = 0.0
            else:
                raio = info["raio_km"] * np.sqrt(rng.uniform(0.15, 1.0))
                angulo = rng.uniform(0, 2 * np.pi)
                dx, dy = raio * np.cos(angulo), raio * np.sin(angulo)
            linhas.append({
                "cidade": cidade,
                "bairro": bairro,
                "lat": info["lat"] + dy / KM_POR_GRAU_LAT,
                "lon": info["lon"] + dx / km_por_grau_lon,
                "peso_origem": PESO_CENTRO_ORIGEM if bairro == "Centro" else 1.0,
            })
    return pd.DataFrame(linhas)


BAIRROS = _montar_bairros()

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


def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Distância em linha reta (km) entre pares de coordenadas WGS84."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


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


def _sortear_origens(rng: np.random.Generator, n: int) -> np.ndarray:
    """Índices de BAIRROS para a coleta: peso da cidade x peso do bairro (Centro maior)."""
    peso_cidade = BAIRROS["cidade"].map({c: i["peso"] for c, i in CIDADES.items()})
    peso_bairro_na_cidade = BAIRROS["peso_origem"] / BAIRROS.groupby("cidade")["peso_origem"].transform("sum")
    p = (peso_cidade * peso_bairro_na_cidade).to_numpy()
    return rng.choice(len(BAIRROS), size=n, p=p / p.sum())


def _sortear_destinos(rng: np.random.Generator, idx_origem: np.ndarray) -> np.ndarray:
    """Índices de BAIRROS para a entrega: 80% no mesmo município, 20% em outro."""
    cidades = list(CIDADES)
    peso_cidade = np.array([CIDADES[c]["peso"] for c in cidades])
    cidade_origem = BAIRROS["cidade"].to_numpy()[idx_origem]
    mesma = rng.random(len(idx_origem)) < PROB_MESMA_CIDADE

    cidade_destino = cidade_origem.copy()
    for i in np.flatnonzero(~mesma):
        outras = [j for j, c in enumerate(cidades) if c != cidade_origem[i]]
        p = peso_cidade[outras] / peso_cidade[outras].sum()
        cidade_destino[i] = cidades[rng.choice(outras, p=p)]

    destino = np.empty(len(idx_origem), dtype=int)
    for cidade in cidades:
        linhas = np.flatnonzero(cidade_destino == cidade)
        candidatos = np.flatnonzero(BAIRROS["cidade"].to_numpy() == cidade)
        destino[linhas] = rng.choice(candidatos, size=len(linhas))
    return destino


def _calcular_distancia_km(rng: np.random.Generator, idx_o: np.ndarray, idx_d: np.ndarray) -> np.ndarray:
    """Distância pelas ruas: haversine entre pontos sorteados nos bairros x tortuosidade."""
    lat, lon = BAIRROS["lat"].to_numpy(), BAIRROS["lon"].to_numpy()
    jitter_grau = JITTER_KM / KM_POR_GRAU_LAT
    n = len(idx_o)
    lat_o = lat[idx_o] + rng.uniform(-jitter_grau, jitter_grau, n)
    lon_o = lon[idx_o] + rng.uniform(-jitter_grau, jitter_grau, n)
    lat_d = lat[idx_d] + rng.uniform(-jitter_grau, jitter_grau, n)
    lon_d = lon[idx_d] + rng.uniform(-jitter_grau, jitter_grau, n)
    return np.maximum(haversine_km(lat_o, lon_o, lat_d, lon_d) * FATOR_TORTUOSIDADE, 0.5)


def _sortear_enderecos(rng: np.random.Generator, cidades_destino: np.ndarray) -> list[str]:
    """Rua real do município de destino + número sorteado."""
    numeros = rng.integers(10, 3000, size=len(cidades_destino))
    return [
        f"{rng.choice(CIDADES[cidade]['ruas'])}, {numero}"
        for cidade, numero in zip(cidades_destino, numeros)
    ]


def gerar_entregas(n: int = 5000, inicio: str = "2026-09-01", dias: int = 61, random_state: int = 42) -> pd.DataFrame:
    """Gera um DataFrame com `n` entregas simuladas de moto."""
    rng = np.random.default_rng(random_state)

    data_hora = _sortear_datas(rng, n, inicio, dias).sort_values(ignore_index=True)
    dia_util = data_hora.dt.day_of_week < 5
    horario_pico = dia_util & data_hora.dt.hour.isin(HORAS_PICO_TRANSITO)

    idx_o = _sortear_origens(rng, n)
    idx_d = _sortear_destinos(rng, idx_o)
    origem, destino = BAIRROS.iloc[idx_o], BAIRROS.iloc[idx_d]
    distancia_km = _calcular_distancia_km(rng, idx_o, idx_d)
    enderecos = _sortear_enderecos(rng, destino["cidade"].to_numpy())

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
            "cidade_origem": origem["cidade"].to_numpy(),
            "bairro_origem": origem["bairro"].to_numpy(),
            "cidade_destino": destino["cidade"].to_numpy(),
            "bairro_destino": destino["bairro"].to_numpy(),
            "endereco_destino": enderecos,
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
