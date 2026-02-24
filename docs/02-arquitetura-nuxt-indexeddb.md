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
  components/
    PwaInstallModal.vue
  composables/
    useIndexedAuctionCars.ts
    useAuctionCarsApi.ts
    usePwaInstall.ts
  layouts/default.vue
  plugins/
    pwa.client.ts
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
      quotas.get.ts
  repositories/
    auctionCarsRepo.ts
    plateLookupCacheRepo.ts
  utils/
    placafipe.ts
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
- Nome da colecao Mongo para cache de consultas: `plate_lookup_cache`.
- Responsabilidade: armazenar retorno da API por placa normalizada para evitar custo repetido de quota.
- Chave primaria: `_id` igual a placa normalizada.

## 4. Fluxo de dados

1. Usuario preenche dados no celular e opcionalmente tira foto frontal.
2. UI calcula margem em tempo real usando `shared/valuation.ts`.
3. Registro e salvo em `IndexedDB` (`useIndexedAuctionCars`).
4. Quando houver internet e backend configurado, UI sincroniza via `POST /api/v1/auction-cars`.
5. OCR de placa acontece via `POST /api/v1/plate/recognize` (Nuxt server).
6. Nuxt server encaminha OCR para Flask interno via `NUXT_FLASK_BASE_URL` (padrao `127.0.0.1:5000`).
6.1. Se OCR retornar candidatos ambiguos (mesma base de placa, digito final diferente), o frontend abre edicao de placa e bloqueia consulta FIPE automatica ate confirmacao manual.
6.2. Quando houver disputa `0` x `7` no ultimo digito com confianca quase empatada, o backend prioriza `...0` na lista de candidatos (limiar fixo de producao), sem remover a confirmacao manual.
6.3. Em baixa confianca, backend aplica `template_rerank` com templates de caracteres gerados do `public/fontes.svg` (`flask/models/char_templates.json`), carregados no boot do Flask.
7. Consulta placa/FIPE acontece via `POST /api/v1/plate-fipe/lookup`.
7.0. Quando `NUXT_PLACA_FIPE_MOCK=true`, backend responde com mock deterministico por placa e nao chama provider externo.
7.1. Backend chama `POST /getplacafipe` na API oficial `api.placafipe.com.br` e usa `POST /getplaca` apenas como fallback de dados do veiculo.
7.2. Consulta de quota acontece via `GET /api/v1/plate-fipe/quotas`, que encapsula `POST /getquotas` (sem consumo de limite).
7.3. Resultado de consulta por placa e cacheado na colecao `plate_lookup_cache` (Mongo) para evitar custo repetido.
7.4. Quando o provider retorna apenas dados cadastrais da placa (sem FIPE), a API preserva esses metadados no payload de resposta para uso no front.
8. Quando app abre no navegador mobile, composable de PWA avalia instalacao e pode abrir modal de convite.

## 5. Decisoes tecnicas

- Calculo no cliente: reduz latencia no patio e permite decisao imediata.
- IndexedDB: evita perda de dados em campo sem conectividade.
- `shared/valuation.ts`: mesma regra de margem no front e backend.
- **Flask**: API Python simples e leve para futuras integrações.
- **Proxy Nuxt para OCR**: evita chamada browser -> `localhost:5000` em producao e elimina dependencia de CORS para OCR interno.
- **Supervisor**: gerencia múltiplos processos (Nuxt + Flask) em um único container Docker (produção).
- **Perfil OCR/Gunicorn fixo**: tuning de producao embutido no codigo para reduzir configuracao manual de ambiente.
- **Bootstrap por fonte vetorial**: templates A-Z/0-9 extraidos de `fontes.svg` reforcam o rerank de candidatos em OCR fraco.
- **PWA com service worker**: permite instalacao no celular e suporte de uso em modo app (standalone).
- Cache por placa no backend: reduz custo de quota ao reaproveitar consultas anteriores.
- Modo mock por env (`NUXT_PLACA_FIPE_MOCK`): habilita testes sem custo de quota.
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
