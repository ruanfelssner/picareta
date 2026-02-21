# Picareta

Aplicacao Nuxt para cadastrar carros de leilao, estimar custos de recuperacao e calcular margem com base no valor FIPE.

## Stack

- Nuxt 4 + Vue 3
- IndexedDB no front para operacao offline/no celular
- API server (Nitro) para sincronizacao opcional em MongoDB

## Setup

```bash
node -v # recomendado >= 20
pnpm install
cp .env.example .env
```

## Desenvolvimento

```bash
pnpm dev
```

Aplicacao local: `http://localhost:3000`

## OCR de Placa (Python)

- Engine ativa: `NUXT_PLATE_OCR_ENGINE=python`
- Script: `server/scripts/plate_ocr.py`
- Check rapido:

```bash
pnpm ocr:python:check
```

No Docker/Railway, as dependencias Python e Tesseract sao instaladas pelo `Dockerfile`.

## Documentacao

- Requisitos: `docs/01-requisitos.md`
- Arquitetura: `docs/02-arquitetura-nuxt-indexeddb.md`
- Plano funcional + UI mobile: `docs/03-plano-funcionalidades-ui-mobile.md`
