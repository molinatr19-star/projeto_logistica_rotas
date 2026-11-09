# Dicionário de dados

Registrar cada coluna das bases em `data/processed`.

## dados_entregas_simulados.csv (data/raw)

Gerado por `src/logistica_rotas/ingestao/simulacao.py` (`random_state=42`, 5.000 pedidos, 01/09/2026 a 31/10/2026). Cidade e bairros fictícios.

| Coluna | Tipo | Unidade | Regra / descrição |
|--------|------|---------|-------------------|
| id_pedido | texto | - | Identificador único, formato `PED000001` |
| data_hora_pedido | datetime com fuso | America/Sao_Paulo | Sorteada com mais peso no almoço (11h-13h) e jantar (18h-20h); faixa 8h-23h |
| bairro_origem | categoria | - | Local de coleta; mais peso em bairros comerciais (Centro ~30%) |
| bairro_destino | categoria | - | Local de entrega; mais peso em bairros residenciais |
| distancia_km | decimal | km | Linha reta entre pontos sorteados nos bairros x 1,3 (tortuosidade); mínimo 0,5 |
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
