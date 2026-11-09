"""Mapas interativos (folium) dos bairros e das rotas.

Base cartográfica: OpenStreetMap (© colaboradores do OpenStreetMap, ODbL).
Bairros com `fonte_coordenada = simulada` aparecem com borda tracejada e aviso no popup.
"""

from pathlib import Path

import branca.colormap as cm
import folium
import numpy as np
import pandas as pd

from logistica_rotas.ingestao.simulacao import BAIRROS, RAIZ_PROJETO
from logistica_rotas.metricas.kpis import mascara_concluidas

PASTA_REPORTS = RAIZ_PROJETO / "reports"
RAMPA_ATRASO = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
CORES_ROTAS = ["#2a78d6", "#eb6834", "#1baf7a", "#e87ba4", "#6250d6", "#008300", "#eda100", "#e34948"]


def indicadores_por_bairro(df: pd.DataFrame) -> pd.DataFrame:
    """Entregas, taxa de atraso e tempo mediano por bairro de destino, com coordenadas."""
    feitas = df[mascara_concluidas(df)]
    chaves = [feitas["cidade_destino"].astype(str), feitas["bairro_destino"].astype(str)]
    tabela = feitas.groupby(chaves).agg(
        entregas=("status", "size"),
        atraso_pct=("status", lambda s: (s == "com_atraso").mean() * 100),
        tempo_mediano_min=("tempo_transito_min", "median"),
        distancia_media_km=("distancia_km", "mean"),
    )
    tabela.index.names = ["cidade", "bairro"]
    coords = BAIRROS.set_index(["cidade", "bairro"])[["lat", "lon", "fonte_coordenada"]]
    return tabela.join(coords).reset_index()


def mapa_bairros(df: pd.DataFrame, vmax_atraso: float = 15.0) -> folium.Map:
    """Círculos por bairro de destino: tamanho = entregas, cor = taxa de atraso. Hubs marcados."""
    tabela = indicadores_por_bairro(df)
    mapa = folium.Map(location=[tabela["lat"].mean(), tabela["lon"].mean()], zoom_start=12,
                      tiles="OpenStreetMap", control_scale=True)
    escala = cm.LinearColormap(RAMPA_ATRASO, vmin=0, vmax=vmax_atraso,
                               caption="Taxa de atraso no bairro de destino (%)")
    for linha in tabela.itertuples(index=False):
        simulada = linha.fonte_coordenada != "osm"
        aviso = "<br><i>Posição simulada (não encontrada no OSM)</i>" if simulada else ""
        popup = (f"<b>{linha.bairro}</b> · {linha.cidade}<br>Entregas: {linha.entregas}<br>"
                 f"Atraso: {linha.atraso_pct:.1f}%<br>Tempo mediano: {linha.tempo_mediano_min:.0f} min<br>"
                 f"Distância média: {linha.distancia_media_km:.1f} km{aviso}").replace(".", ",")
        folium.CircleMarker(
            location=[linha.lat, linha.lon],
            radius=float(4 + np.sqrt(linha.entregas) * 1.2),
            color="#0b0b0b" if simulada else "#ffffff",
            dash_array="4" if simulada else None,
            weight=1.5,
            fill=True, fill_color=escala(min(linha.atraso_pct, vmax_atraso)), fill_opacity=0.85,
            popup=folium.Popup(popup, max_width=260),
            tooltip=f"{linha.bairro} · {linha.cidade}",
        ).add_to(mapa)
    for cidade, (lat, lon) in BAIRROS[BAIRROS["bairro"] == "Centro"].set_index("cidade")[["lat", "lon"]].iterrows():
        folium.Marker([lat, lon], tooltip=f"Hub (Centro) · {cidade}",
                      icon=folium.Icon(color="black", icon="home")).add_to(mapa)
    escala.add_to(mapa)
    return mapa


def mapa_rotas(hub: tuple[float, float], lats: np.ndarray, lons: np.ndarray, rotas: list[list[int]],
               titulo: str = "") -> folium.Map:
    """Desenha as rotas de um lote (uma cor por viagem), saindo e voltando ao hub."""
    mapa = folium.Map(location=[np.mean([hub[0], *lats]), np.mean([hub[1], *lons])], zoom_start=13,
                      tiles="OpenStreetMap", control_scale=True)
    folium.Marker(hub, tooltip="Hub", icon=folium.Icon(color="black", icon="home")).add_to(mapa)
    for k, rota in enumerate(rotas):
        cor = CORES_ROTAS[k % len(CORES_ROTAS)]
        pontos = [hub] + [(lats[i - 1], lons[i - 1]) for i in rota] + [hub]
        folium.PolyLine(pontos, color=cor, weight=4, opacity=0.85, tooltip=f"Viagem {k + 1}").add_to(mapa)
        for ordem, i in enumerate(rota, start=1):
            folium.CircleMarker((lats[i - 1], lons[i - 1]), radius=7, color="#ffffff", weight=1.5, fill=True,
                                fill_color=cor, fill_opacity=1, tooltip=f"Viagem {k + 1} · parada {ordem}").add_to(mapa)
    if titulo:
        mapa.get_root().html.add_child(folium.Element(
            f'<div style="position:fixed;top:10px;left:50px;z-index:9999;background:#fff;padding:6px 10px;'
            f'border-radius:6px;font:14px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)">{titulo}</div>'))
    return mapa


def salvar_mapa(mapa: folium.Map, nome: str, pasta: Path = PASTA_REPORTS) -> Path:
    """Salva o mapa como HTML em reports/."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.html"
    mapa.save(str(caminho))
    return caminho
