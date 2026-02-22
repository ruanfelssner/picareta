# 02 - Arquitetura Nuxt + IndexedDB

## 1. Visao geral

A aplicacao usa Nuxt 4 com quatro camadas principais:

- Frontend (`app/`): UI mobile-first e fluxo de cadastro.
- Persistencia local (`IndexedDB`): operacao offline imediata no celular.
- Backend Node.js (`server/api` + Mongo): sincronizacao opcional e integracao externa de placa/FIPE.
- Backend Python (`flask/`): API Flask para futura integração.

## 2. Estrutura de pastas

```text
app/
  assets/css/main.css
  composables/
    useIndexedAuctionCars.ts
    useAuctionCarsApi.ts
  layouts/default.vue
  pages/index.vue

shared/
  types/auction.ts
  valuation.ts

server/
  api/v1/
    auction-cars/
      index.get.ts
      index.post.ts
      [id].delete.ts
    plate/
      recognize.post.ts
    plate-fipe/
      lookup.post.ts
  repositories/
    auctionCarsRepo.ts
  utils/
    mongo.ts

flask/                    # Backend Python
  app.py                  # API Flask
  config.py
  requirements.txt
```

## 3. Colecao dedicada

- Nome da colecao Mongo: `auction_cars`.
- Responsabilidade: armazenar snapshot sincronizado dos carros avaliados no dispositivo.
- Chave primaria: `_id` string (mesmo valor de `id` no front).

## 4. Fluxo de dados

1. Usuario preenche dados no celular e opcionalmente tira foto frontal.
2. UI calcula margem em tempo real usando `shared/valuation.ts`.
3. Registro e salvo em `IndexedDB` (`useIndexedAuctionCars`).
4. Quando houver internet e backend configurado, UI sincroniza via `POST /api/v1/auction-cars`.
5. OCR de placa acontece via `POST /api/v1/plate/recognize` (Nuxt server).
6. Nuxt server encaminha OCR para Flask interno via `NUXT_FLASK_BASE_URL` (padrao `127.0.0.1:5000`).
7. Consulta placa/FIPE acontece via `POST /api/v1/plate-fipe/lookup`.

## 5. Decisoes tecnicas

- Calculo no cliente: reduz latencia no patio e permite decisao imediata.
- IndexedDB: evita perda de dados em campo sem conectividade.
- `shared/valuation.ts`: mesma regra de margem no front e backend.
- **Flask**: API Python simples e leve para futuras integrações.
- **Proxy Nuxt para OCR**: evita chamada browser -> `localhost:5000` em producao e elimina dependencia de CORS para OCR interno.
- **Supervisor**: gerencia múltiplos processos (Nuxt + Flask) em um único container Docker (produção).
- Fallback mock da API de placa/FIPE: nao bloqueia prototipo enquanto credenciais reais nao estiverem disponiveis.

## 6. Infraestrutura

### Desenvolvimento Local

Execute em terminais separados:

```bash
# Terminal 1: Nuxt
pnpm dev

# Terminal 2: Flask
pnpm service:flask
```

### Produção (Docker)

A aplicação roda em containers Docker orquestrados via docker-compose:

- **app**: Container principal com Nuxt (porta 3000) e Flask (porta 5000)
- **mongo**: MongoDB para persistência (porta 27017)
- **redis**: Redis para filas/cache (porta 16379)

Processos no container `app` são gerenciados por `supervisord`.
