# IPMA Weather Proxy API (FastAPI + Docker)

Uma API REST simples em FastAPI que recolhe previsões meteorológicas do IPMA (open-data)
e expõe endpoints para pesquisar localidades e consultar a previsão diária por dia/local.

> Baseado nos requisitos do exercício “API de Previsão do Tempo (IPMA)”.

## Endpoints

- `GET /health` — healthcheck
- `GET /v1/localities?q=Lisboa&district_id=11` — lista localidades do IPMA com filtros opcionais
- `GET /v1/forecast/daily?locality=Lisboa` — previsão diária (5 dias) para uma localidade
- `GET /v1/forecast/day?forecast_date=2025-09-07&locality=Lisboa` — previsão para um **dia específico**

Também pode usar `global_id_local` diretamente:
- `GET /v1/forecast/daily?global_id_local=1110600`
- `GET /v1/forecast/day?forecast_date=2025-09-07&global_id_local=1110600`

## Como correr com Docker

```bash
docker compose up --build
```

## Notas de implementação

- Os dados vêm de `https://api.ipma.pt/open-data` (lista de localidades, classes de tempo e previsão diária por `globalIdLocal`).
- *Cache in-memory* com TTL reduz load e chamadas redundantes.
- Os parâmetros `locality` e `district_id` permitem selecionar dinamicamente a localidade. Em caso de ambiguidade, é usado match exato; se não existir, tenta contain match.
- A resposta `/v1/forecast/day` enriquece o `idWeatherType` com descrições PT/EN.

## Estrutura

```
app/
  main.py          # roteamento FastAPI
  ipma_client.py   # chamadas HTTP e cache
  schemas.py       # Pydantic models
  settings.py      # config simples
  cache.py         # TTL cache minimalista
Dockerfile
docker-compose.yml
requirements.txt
```

---

> Aviso: esta API é apenas um proxy de leitura. Siga os termos de uso do IPMA.

================================================================
## English

# IPMA Weather Proxy API (FastAPI + Docker)

A small FastAPI REST service that wraps IPMA open-data and exposes endpoints to search localities and fetch daily weather forecasts by day/locality.

> Built to satisfy the “Weather Forecast API (IPMA)” exercise requirements.

## ENDPOINTS
- GET /health — health check
- GET /v1/localities?q=Lisboa&district_id=11 — list IPMA localities with optional filters
- GET /v1/forecast/daily?locality=Lisboa — multi-day forecast (≈5 days) for a locality
- GET /v1/forecast/day?forecast_date=2025-09-07&locality=Lisboa — forecast for a specific day

You can also pass ´global_id_local´ directly:
- GET /v1/forecast/daily?global_id_local=1110600
- GET /v1/forecast/day?forecast_date=2025-09-07&global_id_local=1110600

## RUN WITH DOCKER
```bash
docker compose up --build
```

## IMPLEMENTATION NOTES
- Data source: IPMA open-data (/distrits-islands.json, /weather-type-classe.json, /forecast/meteorology/cities/daily/{globalIdLocal}.json).
- Lightweight in-memory TTL cache reduces latency and external calls:
  - localities & classes: 12h; forecasts: 30min (defaults).
- locality and district_id help resolve globalIdLocal. Exact (case-insensitive) match is preferred; falls back to substring search if needed.
- /v1/forecast/day enriches idWeatherType with PT/EN labels for convenience.
- Interactive docs: Swagger UI at /docs, ReDoc at /redoc.

## PROJECT STRUCTURE
```
app/
  main.py          # FastAPI routes
  ipma_client.py   # HTTP calls + TTL caching
  schemas.py       # Pydantic models
  settings.py      # simple configuration
  cache.py         # minimal TTL cache
Dockerfile
docker-compose.yml
requirements.txt
```

## DISCLAIMER
This service is a read-only proxy over IPMA open-data. Please follow IPMA’s terms of use.