# Dicionário de dados

Registrar cada coluna das bases em `data/processed`.

## dados_entregas_simulados.csv (data/raw)

Gerado por `src/logistica_rotas/ingestao/simulacao.py` (`random_state=42`, 5.000 pedidos, 01/09/2026 a 31/10/2026). Região: ABC paulista (Santo André, São Bernardo do Campo, São Caetano do Sul, Diadema) e Mauá.

**Real x simulado**
- Real: municípios, nomes de bairros e nomes de vias.
- Geocodificado (OpenStreetMap/Nominatim, © colaboradores do OSM, ODbL): posição de 43 dos 45 bairros. Cache em `data/external/bairros_geocodificados.csv`.
- Posição simulada (sorteada com `SEED_GEOGRAFIA=2026`): Utinga (SA) e Barão de Mauá (Mauá), que não passaram na validação. **Verificar** o nome "Barão de Mauá": não há bairro com esse nome no OSM.
- Aproximado: coordenada do centro de cada município (usada só para a posição simulada e para validar a geocodificação).
- Simulado: ponto exato da coleta/entrega dentro do bairro (±0,6 km), pedidos, horários, tempos, valores e status.
- A rua do endereço é sorteada entre vias reais do município de destino; a combinação rua x bairro não foi verificada.
- O nome "Centro" existe nas 5 cidades: sempre analisar bairro junto com a cidade (no dashboard, rótulo "Bairro · Sigla").

| Coluna | Tipo | Unidade | Regra / descrição |
|--------|------|---------|-------------------|
| id_pedido | texto | - | Identificador único, formato `PED000001` |
| data_hora_pedido | datetime com fuso | America/Sao_Paulo | Sorteada com mais peso no almoço (11h-13h) e jantar (18h-20h); faixa 8h-23h |
| cidade_origem | categoria | - | Município da coleta; peso por porte (SBC 30%, Santo André 27%, Diadema 16%, Mauá 16%, São Caetano 11%) |
| bairro_origem | categoria | - | Bairro da coleta; o Centro de cada cidade tem peso 3x (comércio) |
| cidade_destino | categoria | - | 80% no mesmo município da origem; 20% em outro, por porte |
| bairro_destino | categoria | - | Bairro da entrega, sorteado com peso igual dentro do município |
| endereco_destino | texto | - | Via real do município de destino + número sorteado (10 a 2999) |
| lat_origem / lon_origem | decimal | graus (WGS84) | Ponto da coleta: centro do bairro de origem ± 0,6 km |
| lat_destino / lon_destino | decimal | graus (WGS84) | Ponto da entrega: centro do bairro de destino ± 0,6 km |
| distancia_km | decimal | km | Haversine entre pontos sorteados nos bairros (±0,6 km) x 1,3 (tortuosidade); mínimo 0,5 |
| horario_pico | sim/nao | - | Dia útil e hora em 7h, 8h, 17h, 18h ou 19h (pico de trânsito) |
| tempo_transito_min | decimal | min | Distância / velocidade (28 km/h normal, 18 km/h pico, com variação) + tempo fixo de coleta/entrega (~6 min). Vazio se cancelado. ~0,5% com erro proposital (x4 a x8) |
| prazo_prometido_min | inteiro | min | 12 + 2,5 x distância, arredondado para cima em múltiplos de 5 |
| valor_entrega_brl | decimal | R$ | 5,99 + 1,50 x distância; +20% no pico |
| status | categoria | - | `cancelado` (4%, ou 7% no pico); `com_atraso` se tempo > prazo; senão `entregue` |

## entregas_validadas.parquet (data/interim) e entregas_limpas.parquet (data/processed)

Gerados pelo `notebooks/02_limpeza.ipynb` com `src/logistica_rotas/limpeza/tratamento.py`. Mesmas 5.000 linhas do CSV (nenhuma apagada). A base `interim` mantém os valores originais; a `processed` tem o tempo dos outliers vazio.

| Coluna | Tipo | Unidade | Regra / descrição |
|--------|------|---------|-------------------|
| local_origem / local_destino | texto | - | "Bairro · Sigla da cidade" (SA, SBC, SCS, Diadema, Mauá) |
| trajeto | texto | - | `mesma cidade` ou `entre cidades` |
| hora | inteiro | h | Hora do pedido (0-23) |
| dia_util | booleano | - | Segunda a sexta |
| faixa_distancia_km | categoria | km | 0-2, 2-4, 4-6, 6-8, 8-10, 10-15, 15+ (intervalo fechado à esquerda) |
| velocidade_media_kmh | decimal | km/h | distancia_km / (tempo_transito_min / 60); inclui o tempo fixo de coleta/entrega |
| outlier_tempo | booleano | - | Tempo > 3 x mediana do tempo na mesma faixa de distância, ou velocidade > 60 km/h. Cancelados = False |
| tempo_transito_min_bruto | decimal | min | Só na `processed`: valor original do tempo antes do tratamento |
| tempo_transito_min | decimal | min | Na `processed`: vazio (NaN) quando `outlier_tempo` = True |

# Definições de KPIs

Implementadas em `src/logistica_rotas/metricas/kpis.py` e testadas em `tests/test_kpis.py`.

| KPI | Fórmula | Observações |
|-----|---------|-------------|
| Entregas concluídas | status != `cancelado` e `outlier_tempo` = False | O filtro de outlier só se aplica quando a coluna existe (base limpa) |
| OTD (%) | entregas `entregue` / entregas concluídas | On-Time Delivery |
| Taxa de atraso (%) | entregas `com_atraso` / entregas concluídas | = 100 - OTD |
| Taxa de cancelamento (%) | `cancelado` / total de pedidos | |
| Tempo de trânsito | mediana de `tempo_transito_min` das concluídas | Mediana nos resumos; média só no card do dashboard, com a mediana ao lado |
| Valor médio (R$) | média de `valor_entrega_brl` de todos os pedidos | |

# Decisões do projeto

| Data | Decisão | Motivo |
|------|---------|--------|
| 2026-11-07 | Estrutura inicial criada | Início do projeto |
| 2026-11-09 | Usar dados simulados de entregas urbanas de moto | Controlar as regras de negócio e validar o método antes de usar dados reais |
| 2026-11-09 | CSV simulado fora do Git | É reproduzível pela seed; o notebook 01 regera se faltar |
| 2026-11-09 | Dashboard Streamlit (`app.py`) | Explorar KPIs e filtros de forma interativa no portfólio |
| 2026-11-09 | Fixar `pyarrow==25.0.1` | Versão 26.0.1 bloqueada pelo Smart App Control do Windows |
| 2026-11-09 | Simulação no ABC paulista + Mauá (bairros e vias reais) | Dar contexto geográfico real ao portfólio; posições dos bairros seguem simuladas |
| 2026-11-09 | Outlier de tempo = tempo > 3 x mediana da faixa de distância (ou > 60 km/h) | Validada com gabarito no notebook 02: 32/32 erros encontrados, 1 falso positivo. A regra "velocidade < 3 km/h" do notebook 01 gerava 29 falsos positivos |
| 2026-11-09 | Outliers não são apagados: tempo vira NaN e sai do OTD | O pedido existiu; só o tempo é inválido, e o status foi calculado com ele |
| 2026-11-09 | Dashboard usa a base limpa e as funções de `metricas/kpis.py` | Uma única definição de KPI para notebooks, dashboard e testes |
| 2026-11-09 | Grupos com menos de 30 entregas concluídas ficam sem OTD nos gráficos (`tabela_otd`, `min_pedidos=30`) | Percentual com poucas entregas oscila demais e leva a conclusões falsas |
| 2026-11-09 | Comparar trajetos sempre dentro da mesma faixa de distância | O notebook 03 mostrou que a diferença "entre cidades x mesma cidade" vem da distância (composição), não da divisa |
| 2026-11-09 | Figuras do relatório versionadas em `reports/figures/` | O README do portfólio exibe os gráficos no GitHub |
| 2026-11-09 | Geocodificar bairros com Nominatim (1 consulta/s, cache versionado) | Coordenadas reais para mapas e roteirização; o cache evita repetir consultas ao serviço |
| 2026-11-09 | Aceitar só resultados do tipo área de bairro (suburb, quarter, neighbourhood...) | Utinga caiu numa estação e Barão de Mauá numa avenida: ponto errado é pior que posição simulada sinalizada |
| 2026-11-09 | "Osvaldo Cruz" renomeado para "Oswaldo Cruz" (São Caetano do Sul) | Grafia usada no OSM |
| 2026-11-09 | Fixar `ortools==9.14.6206` | 9.15 bloqueada pelo Smart App Control do Windows |
| 2026-11-09 | Roteirização: hub no Centro de cada cidade, lotes de 2 h com 3+ pedidos, até 4 pedidos por moto, 3 min por parada, velocidade determinística | Cenário simples e explícito para comparar métodos entre si (não é previsão de operação real) |
| 2026-11-09 | Penalidade de atraso no OR-Tools: 1 min = 2 km | Equilibra economia de km e prazo; valor arbitrário, a testar em sensibilidade |
| 2026-11-09 | Sensibilidade (notebook 06): penalidade recomendada de 10 a 30 km/min | 97,9% a 98,3% no prazo com 29,0% a 28,8% de economia, contra 95,1% e 30,6% com 2 km/min (amostra de 200 lotes, sem espera) |
| 2026-11-09 | Capacidade de 3 a 4 pedidos por moto | Com 5 ou 6 o resultado não muda: o prazo limita o agrupamento a cerca de 2,4 pedidos por viagem |
| 2026-11-09 | Resultados do notebook 05 tratados como teto teórico | Contando a espera até o fechamento do lote, nenhuma janela fixa (15 min a 2 h) mantém o prazo; próximo passo é despacho dinâmico |
| 2026-11-09 | Escala interna do OR-Tools: distância em metros, tempo em décimos de minuto | Permite penalidades fracionárias (ex.: 0,25 km/min) com custos inteiros |
| 2026-11-09 | Despacho dinâmico (notebook 07): moto espera só enquanto o prazo de todos permite; rota por força bruta (até 4 paradas) | Evita a espera fixa da janela; com 4 paradas são só 24 ordens possíveis, então a solução é exata |
| 2026-11-09 | Medir o prazo também "com variação": fator lognormal (sigma 0,25) por viagem | O prazo planejado não mostra o custo da espera; na rua, esperar consome a folga contra o trânsito |
| 2026-11-09 | Política sugerida: margem de 5 min, espera máxima de 5 min fora do pico e nenhuma no pico | Melhor equilíbrio observado: cerca de 2% de economia no volume atual (6% com 4x) perdendo cerca de 2 pontos de prazo; no pico o ganho é de 0,7% |
| 2026-11-09 | Política sem espera no pico confirmada (notebook 08) | Economia de 1,9% contra 2,0% e prazo de 96,4% contra 95,3% (volume atual): quase sem custo |
| 2026-11-09 | Coleta por bairro não compensa agrupar | Economia abaixo de 1,5% mesmo com 4x o volume; o ganho depende de centralizar a coleta (hub/dark kitchen) |
| 2026-11-09 | Matriz OSRM entre os 45 bairros (uma consulta ao servidor público, cache versionado em `data/external/osrm_bairros.csv`) | Medir o fator de tortuosidade real com uso leve do serviço |
| 2026-11-09 | Fator calibrado opcional: 1,31 + 0,40 / distância em linha reta (`fator="osrm"` no despacho) | Mediana real de 1,37 (1,71 até 2 km) contra 1,3 fixo; a simulação base continua com 1,3 para manter os notebooks comparáveis |
