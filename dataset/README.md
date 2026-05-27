# Dataset - Localizacao de Facilidades em Goias

Esta pasta contem tudo que e necessario para recriar o dataset usado no problema de localizacao de facilidades em municipios de Goias.

## Estrutura da pasta

- `raw/basededados.zip`: arquivo bruto recebido para o projeto.
- `build_dataset.py`: script standalone de extracao, limpeza, juncao e geracao do dataset final.
- `processed/goias_facility_locations.csv`: dataset final por municipio.
- `processed/distance_matrix_km.npy`: matriz de distancias Haversine entre municipios.
- `processed/problem_config.json`: metadados e parametros padrao do problema.
- `requirements.txt`: dependencias Python minimas.

## Como rodar

No terminal, entre nesta pasta:

```powershell
cd dataset_entrega
```

Instale as dependencias, se necessario:

```powershell
python -m pip install -r requirements.txt
```

Recrie os arquivos processados:

```powershell
python build_dataset.py
```

Para usar caminhos personalizados:

```powershell
python build_dataset.py --raw-zip raw\basededados.zip --output-dir processed
```

## O que o processamento faz

1. Le `consulta.csv` com indicadores municipais de 2022.
2. Le `tabelaIBGE.csv` com codigo IBGE, populacao, area e densidade.
3. Le o shapefile `GO_Municipios_2025.zip` que esta dentro do zip bruto.
4. Calcula centroides dos poligonos municipais sem depender de bibliotecas GIS externas.
5. Junta os dados por codigo/nome de municipio.
6. Cria um custo sintetico de instalacao por municipio.
7. Calcula a matriz de distancia Haversine em quilometros.
8. Salva CSV, matriz `.npy` e JSON de configuracao.

## Colunas principais

- `municipality_code`: codigo IBGE do municipio.
- `municipality`: nome do municipio.
- `latitude`, `longitude`: centroide do poligono municipal.
- `area_km2`: area territorial.
- `population_2022`: populacao residente do Censo 2022.
- `density_2022`: densidade demografica.
- `estimated_population_2022`: populacao estimada na base complementar.
- `enrollments_total`: matriculas totais.
- `hospitals`: quantidade de hospitais.
- `beds`: quantidade de leitos.
- `schools_total`: estabelecimentos de ensino.
- `gdp_per_capita_brl`: PIB per capita.
- `install_cost_brl`: custo sintetico estimado para instalar uma facilidade.
- `demand_weight`: peso populacional do municipio.
- `immediate_region`, `intermediate_region`: regioes geograficas do IBGE.

## Observacoes

O custo de instalacao nao veio diretamente pronto no dataset bruto. Ele foi modelado de forma sintetica para permitir a restricao orcamentaria do problema:

```text
custo = 0.80M + componentes normalizados de log(populacao), log(area) e log(PIB per capita)
```

Essa escolha cria custos maiores para municipios maiores, mais extensos ou economicamente mais caros, mantendo todos os valores em uma escala simples para os experimentos de heuristicas.
