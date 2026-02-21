# 02 - Arquitetura Nuxt + IndexedDB

## 1. Visao geral

A aplicacao usa Nuxt 4 com tres camadas principais:

- Frontend (`app/`): UI mobile-first e fluxo de cadastro.
- Persistencia local (`IndexedDB`): operacao offline imediata no celular.
- Backend (`server/api` + Mongo): sincronizacao opcional e integracao externa de placa/FIPE.

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
    plate-fipe/
      lookup.post.ts
  repositories/
    auctionCarsRepo.ts
  utils/
    mongo.ts
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
5. Consulta placa/FIPE acontece via `POST /api/v1/plate-fipe/lookup`.

## 5. Decisoes tecnicas

- Calculo no cliente: reduz latencia no patio e permite decisao imediata.
- IndexedDB: evita perda de dados em campo sem conectividade.
- `shared/valuation.ts`: mesma regra de margem no front e backend.
- Fallback mock da API de placa/FIPE: nao bloqueia prototipo enquanto credenciais reais nao estiverem disponiveis.
