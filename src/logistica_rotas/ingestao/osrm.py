"""Distância e tempo pela malha viária real entre os bairros, via OSRM (serviço público de demonstração).

- Uma única consulta ao serviço `table` (matriz 45 x 45 entre os centros dos bairros),
  respeitando o uso leve exigido pelo servidor de demonstração; resultado em cache em
  data/external/osrm_bairros.csv. Os notebooks só leem o cache.
- Perfil `driving` (carro): é a aproximação disponível no servidor público para moto.
  Os tempos são de via livre (sem trânsito).
- Dados de vias © colaboradores do OpenStreetMap (ODbL); roteamento: Project OSRM.

Uso (na raiz do projeto, só para refazer o cache):
    .venv\\Scripts\\python.exe -m logistica_rotas.ingestao.osrm
"""

import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from logistica_rotas.ingestao.simulacao import BAIRROS, RAIZ_PROJETO, haversine_km

CAMINHO_CACHE = RAIZ_PROJETO / "data" / "external" / "osrm_bairros.csv"
URL_OSRM = "https://router.project-osrm.org/table/v1/driving/"
USER_AGENT = "projeto-logistica-rotas/0.1 (portfolio de estudos em analise de dados)"


def consultar_matriz(bairros: pd.DataFrame = BAIRROS, caminho: Path = CAMINHO_CACHE) -> pd.DataFrame:
    """Consulta a matriz de distâncias/tempos entre os bairros e salva em formato longo (uma linha por par)."""
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in bairros[["lat", "lon"]].to_numpy())
    url = f"{URL_OSRM}{coords}?annotations=distance,duration"
    requisicao = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requisicao, timeout=60) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    if dados.get("code") != "Ok":
        raise RuntimeError(f"OSRM respondeu: {dados.get('code')} - {dados.get('message')}")
    dist = np.array(dados["distances"], dtype=float) / 1000   # m -> km
    dur = np.array(dados["durations"], dtype=float) / 60      # s -> min
    lat, lon = bairros["lat"].to_numpy(), bairros["lon"].to_numpy()
    reta = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    n = len(bairros)
    i, j = np.meshgrid(range(n), range(n), indexing="ij")
    mascara = i != j
    tabela = pd.DataFrame({
        "cidade_origem": bairros["cidade"].to_numpy()[i[mascara]],
        "bairro_origem": bairros["bairro"].to_numpy()[i[mascara]],
        "cidade_destino": bairros["cidade"].to_numpy()[j[mascara]],
        "bairro_destino": bairros["bairro"].to_numpy()[j[mascara]],
        "reta_km": reta[mascara],
        "osrm_km": dist[mascara],
        "osrm_min": dur[mascara],
        "fonte_origem": bairros["fonte_coordenada"].to_numpy()[i[mascara]],
        "fonte_destino": bairros["fonte_coordenada"].to_numpy()[j[mascara]],
    })
    tabela["fator_tortuosidade"] = tabela["osrm_km"] / tabela["reta_km"]
    tabela["velocidade_livre_kmh"] = tabela["osrm_km"] / (tabela["osrm_min"] / 60)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(caminho, index=False, encoding="utf-8")
    return tabela


def carregar_cache(caminho: Path = CAMINHO_CACHE) -> pd.DataFrame | None:
    caminho = Path(caminho)
    return pd.read_csv(caminho, encoding="utf-8") if caminho.exists() else None


if __name__ == "__main__":
    t = consultar_matriz()
    print(f"{len(t)} pares. Fator de tortuosidade mediano: {t['fator_tortuosidade'].median():.2f}")
