# projeto_logistica_rotas

Projeto de portfólio de análise de dados da Molina sobre logística: rotas inteligentes, desempenho de entregas, tempos de trânsito e eficiência operacional.

## Status atual
- Fase: análise exploratória (2026-11-09). Feitos: gerador de dados simulados (`src/logistica_rotas/ingestao/simulacao.py`) e `notebooks/01_analise_exploratoria_logistica.ipynb`.
- Dashboard Streamlit em `app.py` (tema escuro em `.streamlit/config.toml`; leitura via `src/logistica_rotas/ingestao/leitura.py`).
- Ambiente Windows com Smart App Control ligado: versões muito recentes de pacotes com DLL podem ser bloqueadas ("política de Controle de Aplicativo"). Por isso `pyarrow==25.0.1` está fixado.
- Fonte de dados atual: entregas de moto simuladas no ABC paulista + Mauá (bairros e vias reais; posições, pedidos e tempos simulados), em `data/raw/dados_entregas_simulados.csv`. Bairro "Centro" existe nas 5 cidades: analisar sempre bairro + cidade.
- Comandos do `.venv` via `python -m` (ex.: `.venv\Scripts\python.exe -m streamlit run app.py`): os `.exe` de atalho são bloqueados pelo Smart App Control.
- Não implementar lógica, baixar dados nem rodar scripts sem pedido explícito da Molina.

## Objetivo do projeto
- Responder perguntas de negócio de logística com dados:
  - Quais rotas/regiões atrasam mais e por quê?
  - Qual o tempo médio de trânsito por trecho, transportadora e período?
  - Onde há ineficiência (km ociosos, baixa ocupação, custo por entrega alto)?
  - Uma roteirização melhor reduziria distância/tempo? Quanto?
- Entregável final: notebooks de análise, relatório com gráficos e mapas, e README de portfólio.

## Tecnologias
- Python 3.13 (ambiente virtual `.venv` local).
- Dados: pandas, numpy, pyarrow (Parquet).
- Visualização: matplotlib, seaborn, plotly.
- Geografia e rotas: geopandas, folium, haversine (distâncias), networkx / OR-Tools (otimização, quando chegar a fase).
- Notebooks: jupyter. Testes: pytest. Estilo: ruff.
- Dependências listadas em `requirements.txt`; adicionar novas lá ao usá-las.

## Estrutura
```
data/raw/         dados originais, nunca editados à mão
data/interim/     dados intermediários de limpeza
data/processed/   bases finais para análise (Parquet)
data/external/    tabelas de apoio (CEPs, municípios IBGE, feriados)
notebooks/        análises numeradas: 01_exploracao.ipynb, 02_...
src/logistica_rotas/
  ingestao/       leitura das fontes
  limpeza/        padronização e validação
  metricas/       KPIs logísticos
  roteirizacao/   distâncias e otimização de rotas
  visualizacao/   gráficos e mapas
reports/figures/  imagens exportadas para o relatório
docs/             dicionário de dados e decisões do projeto
tests/            testes com pytest
```

## Diretrizes de código
- Lógica reutilizável em `src/`; notebooks só orquestram e mostram resultados.
- Funções pequenas, com type hints e docstring curta. Nomes em português, de forma consistente.
- Fluxo de dados sempre em uma direção: raw -> interim -> processed. Nunca sobrescrever `data/raw`.
- Seed fixa (`random_state=42`) para qualquer amostragem ou simulação.
- Caminhos com `pathlib.Path`, relativos à raiz do projeto.

## Diretrizes de dados logísticos
- Datas e horas: converter para `datetime` com fuso explícito (`America/Sao_Paulo`). Documentar se o dado vier sem fuso.
- Coordenadas: WGS84 (EPSG:4326), latitude antes de longitude. Validar faixas (Brasil: lat -34 a 6, lon -74 a -34).
- Distâncias em km e tempos em horas (ou minutos, mas um só padrão por base). Unidade no nome da coluna: `distancia_km`, `tempo_transito_h`.
- Distância haversine é linha reta; deixar claro quando a análise usa ela em vez de distância real de rota.
- Registrar no `docs/dicionario_dados.md` cada coluna nova: nome, tipo, unidade, origem e regra de cálculo.
- Dados de clientes ou endereços reais: anonimizar antes de versionar ou publicar no portfólio.

## KPIs de referência
- OTD (On-Time Delivery): % de entregas dentro do prazo prometido.
- OTIF (On-Time In-Full): no prazo e completas.
- Lead time: pedido -> entrega. Tempo de trânsito: coleta -> entrega.
- Custo por entrega e custo por km.
- Taxa de ocupação do veículo (peso ou volume).
- Entregas por rota / por veículo / por dia.
- Definir em `docs/` a fórmula exata de cada KPI antes de calcular.

## Apoio do Claude
- Agente do projeto: `.claude/agents/analista-logistica.md`.
- Skill do projeto: `.claude/skills/logistica-dados/SKILL.md`.
- Responder em português do Brasil, direto, em tópicos, sem emojis.
- Explicar o porquê de cada etapa (projeto também é de aprendizado).
- Nunca inventar fontes de dados, funções ou parâmetros de bibliotecas. Em dúvida, marcar como "verificar".
