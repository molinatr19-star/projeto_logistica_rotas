# Logística e Rotas Inteligentes

Projeto de portfólio em análise de dados sobre desempenho de entregas, tempos de trânsito, eficiência operacional e otimização de rotas.

Base simulada de entregas de moto no ABC paulista (Santo André, São Bernardo do Campo, São Caetano do Sul, Diadema) e em Mauá, com bairros e vias reais e bairros geocodificados pelo OpenStreetMap. Pedidos, tempos e valores são simulados.

> Status: exploração, limpeza, desempenho, mapas, roteirização e dashboard prontos.

## Principais resultados

**1. O trânsito, e não a demanda, derruba o prazo.** Nos dias úteis, o OTD cai de 95,9% para 77,6% no pico (8h e 17h às 19h). No fim de semana, sem pico, fica em 96,9%.

![OTD por hora](reports/figures/01_otd_por_hora.png)

**2. Entregas entre cidades atrasam mais por serem longas, e não por cruzarem a divisa.** No geral, o OTD é de 84,1% entre cidades e de 94,8% na mesma cidade. Comparando faixas de distância iguais, as duas linhas andam juntas.

![OTD por faixa de distância](reports/figures/02_otd_faixa_trajeto.png)

**3. Pico e distância se somam.** Só 51,4% das entregas entre cidades no pico chegam no prazo. A regra de prazo cresce com a distância, mas ignora o horário.

![OTD por pico e trajeto](reports/figures/03_otd_pico_trajeto.png)

**4. Roteirizar com o prazo no modelo economiza 29% dos km e mantém 96% no prazo.** Comparando lotes de 2 h a partir de um hub por cidade: otimizar só a distância economiza mais (34,7%), mas derruba as entregas no prazo para 68,4%.

![Comparação de métodos de roteirização](reports/figures/08_comparacao_metodos.png)

![Exemplo de rotas](reports/figures/09_exemplo_rotas.png)

**5. No mapa, bairros com entregas mais longas tendem a atrasar mais** (bairros geocodificados pelo OpenStreetMap). Mapa interativo em `reports/mapa_bairros.html`.

![Mapa de atraso por bairro](reports/figures/07_mapa_bairros_atraso.png)

Mais gráficos em [`reports/figures/`](reports/figures/) e nos notebooks. *Dados simulados: os resultados mostram o método, não uma operação real.*

## Perguntas de negócio
- Quais rotas e regiões concentram atrasos?
- Qual o tempo de trânsito por trecho e período?
- Onde estão as ineficiências de custo e ocupação?
- Quanto uma roteirização otimizada reduziria distância e tempo?

## Tecnologias
Python, pandas, numpy, matplotlib, seaborn, plotly, geopandas, folium, OR-Tools, Jupyter, pytest.

## Estrutura
```
data/        raw -> interim -> processed (+ external)
notebooks/   análises numeradas
src/         código reutilizável (pacote logistica_rotas)
reports/     relatório e figuras
docs/        dicionário de dados e decisões
tests/       testes automatizados
```

## Como rodar
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
jupyter lab
```

## Notebooks
1. `01_analise_exploratoria_logistica.ipynb` - visão geral da base, cidades, bairros, pico e entregas entre cidades.
2. `02_limpeza.ipynb` - regra de outlier de tempo validada com gabarito; gera as bases `interim` e `processed` (Parquet).
3. `03_desempenho.ipynb` - OTD por horário, trajeto e cidade; separa o efeito da distância do efeito de cruzar a divisa; gera as figuras do relatório.
4. `04_mapas.ipynb` - qualidade da geocodificação (43 de 45 bairros), checagem de coordenadas e mapas estático e interativo.
5. `05_roteirizacao.ipynb` - individual x vizinho mais próximo x OR-Tools x OR-Tools com prazo em 761 lotes; troca entre km e prazo.

## Créditos de dados
Coordenadas dos bairros e mapa de fundo: © colaboradores do [OpenStreetMap](https://www.openstreetmap.org/copyright), licença ODbL, consultados via Nominatim respeitando a política de uso (1 consulta/s, cache local).

## Testes
```powershell
.venv\Scripts\python.exe -m pytest
```

## Dashboard interativo (Streamlit)
```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```
Abre em `http://localhost:8501`. Filtros por status, cidade e bairro, KPIs (entregas, taxa de atraso, tempo médio, cancelamento, valor médio) e gráficos por status, bairro, faixa de distância e hora do pedido.

## Autoria
Molina - estudante de Análise e Desenvolvimento de Sistemas.
