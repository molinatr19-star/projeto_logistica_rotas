---
name: logistica-dados
description: Padrões de análise de dados logísticos e geográficos do projeto_logistica_rotas - KPIs de entrega (OTD, OTIF, lead time, custo por km, ocupação), tempos de trânsito, coordenadas, distâncias, mapas e roteirização com pandas, geopandas, folium e OR-Tools. Use ao planejar, escrever ou revisar qualquer análise, limpeza, gráfico ou mapa deste projeto.
---

Projeto: `projeto_logistica_rotas`. Ler o `CLAUDE.md` da raiz antes de começar.

# Fluxo padrão de uma análise
1. Pergunta de negócio -> KPI que responde -> fórmula registrada em `docs/`.
2. Ingestão: ler de `data/raw` sem alterar o arquivo original.
3. Limpeza e validação (ver checklist) -> salvar em `data/interim`.
4. Enriquecimento (distâncias, regiões, feriados) -> salvar em `data/processed` em Parquet.
5. Análise e visualização em notebook numerado.
6. Conclusão em linguagem de negócio + limitações dos dados.

# Checklist de validação de dados de entrega
- Chave única por entrega/pedido; sem duplicatas.
- Ordem temporal: pedido <= coleta <= entrega. Registrar e tratar violações.
- Fuso horário explícito (`America/Sao_Paulo`).
- Coordenadas válidas (EPSG:4326, lat/lon dentro do Brasil, sem 0,0).
- Unidades padronizadas e no nome da coluna (`_km`, `_h`, `_kg`, `_m3`, `_brl`).
- Status de entrega normalizado (entregue, atrasado, cancelado, devolvido).
- Outliers: tempos negativos ou absurdos, velocidades médias impossíveis (> 120 km/h em rodovia, por exemplo).

# Definições de KPIs (confirmar com a Molina antes de calcular)
- OTD = entregas no prazo / entregas concluídas.
- OTIF = entregas no prazo e completas / entregas concluídas.
- Lead time = data_entrega - data_pedido.
- Tempo de trânsito = data_entrega - data_coleta.
- Custo por km = custo_total_brl / distancia_km.
- Ocupação = carga transportada / capacidade do veículo (peso ou volume, declarar qual).
- Cancelados ficam fora do denominador, salvo decisão diferente registrada em `docs/`.

# Geografia e rotas
- Distância rápida: haversine (linha reta). Sempre rotular como tal nos gráficos.
- Distância real de rota exige API ou malha viária (OSRM, OpenStreetMap); avisar custo e limites antes de usar.
- Otimização: começar por heurística simples (vizinho mais próximo) como baseline; depois OR-Tools (VRP) e comparar ganho em km e tempo.
- Mapas: folium para interativo (exportar HTML em `reports/`), geopandas + matplotlib para estático.

# Visualização
- Um gráfico responde uma pergunta; título diz a conclusão.
- Eixos com unidade. Séries temporais em linha; comparação entre rotas/regiões em barras ordenadas.
- Salvar figuras em `reports/figures/` com nome descritivo (`otd_por_regiao.png`).

# Boas práticas
- Funções puras em `src/logistica_rotas/`, testadas com pytest em `tests/`.
- `random_state=42` em amostragens e simulações.
- Não versionar dados reais sensíveis; anonimizar clientes e endereços.
- Nunca inventar fonte de dados ou parâmetro de biblioteca; marcar "verificar" quando houver dúvida.
