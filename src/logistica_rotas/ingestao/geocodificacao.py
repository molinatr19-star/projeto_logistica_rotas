"""Geocodificação dos bairros com o Nominatim (OpenStreetMap).

- Uso conforme a política do Nominatim: no máximo 1 consulta por segundo,
  User-Agent identificando a aplicação e resultados guardados em cache
  (data/external/bairros_geocodificados.csv) para não repetir consultas.
- Dados © colaboradores do OpenStreetMap, licença ODbL
  (https://www.openstreetmap.org/copyright).
- Validação: o resultado precisa ser uma área de bairro (TIPOS_ACEITOS), citar
  o município e estar a até DISTANCIA_MAX_KM do centro aproximado dele; caso
  contrário o bairro fica sem coordenada real e a simulação usa posição simulada.

Uso (na raiz do projeto, só quando quiser refazer o cache):
    .venv\\Scripts\\python.exe -m logistica_rotas.ingestao.geocodificacao
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
CAMINHO_CACHE = RAIZ_PROJETO / "data" / "external" / "bairros_geocodificados.csv"
URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "projeto-logistica-rotas/0.1 (portfolio de estudos em analise de dados)"
PAUSA_SEGUNDOS = 1.1
DISTANCIA_MAX_KM = 9.0
# Só aceitamos resultados que representam uma área de bairro (não rua, estação, posto etc.).
TIPOS_ACEITOS = {"suburb", "quarter", "neighbourhood", "city_district", "residential"}


def _consultar(texto: str) -> dict | None:
    """Uma consulta ao Nominatim; devolve o primeiro resultado ou None."""
    parametros = urllib.parse.urlencode({"q": texto, "format": "jsonv2", "limit": 1, "countrycodes": "br"})
    requisicao = urllib.request.Request(f"{URL_NOMINATIM}?{parametros}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requisicao, timeout=30) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    return dados[0] if dados else None


def _distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(2 * 6371.0 * np.arcsin(np.sqrt(a)))


def geocodificar_bairros(cidades: dict, caminho: Path = CAMINHO_CACHE) -> pd.DataFrame:
    """Consulta cada bairro (bairro, cidade, SP) e salva o cache em CSV."""
    linhas = []
    for cidade, info in cidades.items():
        for bairro in info["bairros"]:
            consulta = f"{bairro}, {cidade}, São Paulo, Brasil"
            resultado = _consultar(consulta)
            time.sleep(PAUSA_SEGUNDOS)
            linha = {"cidade": cidade, "bairro": bairro, "consulta": consulta,
                     "lat": np.nan, "lon": np.nan, "tipo_osm": None, "nome_osm": None,
                     "dist_centro_km": np.nan, "valido": False}
            if resultado:
                lat, lon = float(resultado["lat"]), float(resultado["lon"])
                dist = _distancia_km(lat, lon, info["lat"], info["lon"])
                tipo = resultado.get("addresstype") or resultado.get("type")
                linha.update(lat=lat, lon=lon, tipo_osm=tipo,
                             nome_osm=resultado.get("display_name"), dist_centro_km=round(dist, 2),
                             valido=(tipo in TIPOS_ACEITOS and dist <= DISTANCIA_MAX_KM
                                     and cidade in resultado.get("display_name", "")))
            linhas.append(linha)
            print(f"{'ok ' if linha['valido'] else '-- '} {cidade} / {bairro}: {linha['tipo_osm']} "
                  f"{linha['dist_centro_km']} km")
    tabela = pd.DataFrame(linhas)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(caminho, index=False, encoding="utf-8")
    return tabela


def carregar_cache(caminho: Path = CAMINHO_CACHE) -> pd.DataFrame | None:
    """Lê o cache de geocodificação, se existir."""
    caminho = Path(caminho)
    return pd.read_csv(caminho, encoding="utf-8") if caminho.exists() else None


if __name__ == "__main__":
    from logistica_rotas.ingestao.simulacao import CIDADES

    tabela = geocodificar_bairros(CIDADES)
    print(f"\n{int(tabela['valido'].sum())} de {len(tabela)} bairros com coordenada válida. Cache: {CAMINHO_CACHE}")
