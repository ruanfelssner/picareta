# 03 - Plano de Funcionalidades e UI Mobile

## 1. Objetivo do plano

Colocar o app para uso real no celular, com cadastro e analise de margem em poucos toques.

## 2. Entregas por fase

### Fase 1 - Rodar hoje (MVP funcional)

- Tela unica de cadastro rapido.
- Captura de foto frontal pela camera (`capture="environment"`).
- Campos de placa, FIPE, compra e custos variaveis.
- Calculo imediato de margem na tela.
- Salvamento local em IndexedDB e lista de registros no aparelho.
- Botao de sincronizacao para API.

### Fase 2 - Operacao de campo

- Enriquecimento automatico de marca/modelo/ano/FIPE.
- Filtros locais (hoje, com lucro, abaixo da meta).
- Indicador de status da sincronizacao por registro.

### Fase 3 - Escala e gestao

- Login e multiusuario.
- Painel com historico de margens e ticket medio por periodo.
- Exportacao CSV/PDF para prestacao de contas.
- Regras de aprovacao (ex.: margem minima obrigatoria).

## 3. Fluxo de UI no celular

1. Abrir app em `index`.
2. Tirar foto frontal do carro (opcional no MVP) e usar preview ampliado da fila para conferir imagem/placa.
3. Confirmar placa sugerida pelo OCR; se houver ambiguidade, editar/selecionar manualmente no Step 2 antes da primeira consulta FIPE.
4. Ajustar valor de compra e custos de recuperacao.
5. Ler bloco "Analise de margem" em tempo real.
6. Tocar "Salvar local" para nao perder o registro.
7. Tocar "Sincronizar API" quando tiver internet.

## 4. Requisitos de usabilidade mobile

- Campos grandes e espacamento para dedo (minimo 44px altura util).
- Botoes principais sempre visiveis no fim do formulario.
- Feedback de acao imediato (sucesso, alerta, erro).
- Contraste forte para leitura em ambiente externo.
- Lista local simples para "Abrir" e "Excluir" sem navegar em varias telas.

## 5. Checklist para rodar em campo

- Definir `.env` com `NUXT_PUBLIC_SITE_URL`.
- Se usar sync, configurar `NUXT_MONGO_URI` e `NUXT_MONGO_DB_NAME`.
- Para testes sem custo de API, usar `NUXT_PLACA_FIPE_MOCK=true`.
- Se usar integracao real, configurar `NUXT_PLACA_FIPE_BASE_URL`, `NUXT_PLACA_FIPE_TOKEN` e `NUXT_PLACA_FIPE_MOCK=false`.
- Executar `pnpm dev` e abrir no celular na mesma rede local.
