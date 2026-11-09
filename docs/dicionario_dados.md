# Dicionário de dados

Registrar cada coluna das bases em `data/processed`.

## dados_entregas_simulados.csv (data/raw)

Gerado por `src/logistica_rotas/ingestao/simulacao.py` (`random_state=42`, 5.000 pedidos, 01/09/2026 a 31/10/2026). Região: ABC paulista (Santo André, São Bernardo do Campo, São Caetano do Sul, Diadema) e Mauá.

**Real x simulado**
- Real: municípios, nomes de bairros e nomes de vias.
- Aproximado (verificar antes de usar em mapas): coordenada do centro de cada município.
- Simulado: posição de cada bairro dentro do município (sorteada com `SEED_GEOGRAFIA=2026`, sem geocodificação), pedidos, horários, tempos, valores e status.
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
| distancia_km | decimal | km | Haversine entre pontos sorteados nos bairros (±0,6 km) x 1,3 (tortuosidade); mínimo 0,5 |
| horario_pico | sim/nao | - | Dia útil e hora em 7h, 8h, 17h, 18h ou 19h (pico de trânsito) |
| tempo_transito_min | decimal | min | Distância / velocidade (28 km/h normal, 18 km/h pico, com variação) + tempo fixo de coleta/entrega (~6 min). Vazio se cancelado. ~0,5% com erro proposital (x4 a x8) |
| prazo_prometido_min | inteiro | min | 12 + 2,5 x distância, arredondado para cima em múltiplos de 5 |
| valor_entrega_brl | decimal | R$ | 5,99 + 1,50 x distância; +20% no pico |
| status | categoria | - | `cancelado` (4%, ou 7% no pico); `com_atraso` se tempo > prazo; senão `entregue` |

# Definições de KPIs

| KPI | Fórmula | Observações |
|-----|---------|-------------|
|     |         |             |

# Decisões do projeto

| Data | Decisão | Motivo |
|------|---------|--------|
| 2026-11-07 | Estrutura inicial criada | Início do projeto |
| 2026-11-09 | Usar dados simulados de entregas urbanas de moto | Controlar as regras de negócio e validar o método antes de usar dados reais |
| 2026-11-09 | CSV simulado fora do Git | É reproduzível pela seed; o notebook 01 regera se faltar |
| 2026-11-09 | Dashboard Streamlit (`app.py`) | Explorar KPIs e filtros de forma interativa no portfólio |
| 2026-11-09 | Fixar `pyarrow==25.0.1` | Versão 26.0.1 bloqueada pelo Smart App Control do Windows |
| 2026-11-09 | Simulação no ABC paulista + Mauá (bairros e vias reais) | Dar contexto geográfico real ao portfólio; posições dos bairros seguem simuladas |
