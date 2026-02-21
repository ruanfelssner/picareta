# 01 - Requisitos do Produto

## 1. Contexto

O projeto Picareta precisa permitir avaliacao rapida de carros de leilao no celular, com foco em margem e tomada de decisao imediata no patio/leilao.

## 2. Requisitos funcionais

- RF-01: cadastrar carro com dados basicos (placa, marca, modelo, ano, valor de compra, valor FIPE, observacoes).
- RF-02: aceitar foto frontal do carro via camera do celular.
- RF-03: consultar dados de placa/FIPE via API externa (quando configurada).
- RF-04: quando API externa nao estiver configurada, manter fallback local mock para nao bloquear o fluxo.
- RF-05: cadastrar custos por item (pintura, mecanica, suspensao, vidros, portas e outros).
- RF-06: calcular em tempo real custo total, investimento total, lucro estimado e margem percentual.
- RF-07: permitir salvar e listar carros localmente no aparelho (IndexedDB) para uso offline.
- RF-08: permitir reabrir e editar registros salvos localmente.
- RF-09: sincronizar registro para API server.
- RF-10: expor API com colecao dedicada para carros de leilao (`auction_cars`).

## 3. Requisitos nao funcionais

- RNF-01: UI mobile-first com navegacao por toque e leitura rapida em tela pequena.
- RNF-02: operacao local deve funcionar sem internet para cadastro e calculo.
- RNF-03: tempo de resposta percebido deve ser imediato para calculo de margem (sem roundtrip para API).
- RNF-04: validacao de payload no backend para reduzir dados inconsistentes.
- RNF-05: arquitetura deve separar camada de UI, regras de calculo e integracao externa.

## 4. Regras de negocio

- RB-01: margem percentual = `(lucro estimado / valor FIPE) * 100`.
- RB-02: lucro estimado = `valor FIPE - (valor compra + custos totais)`.
- RB-03: custos negativos nao sao permitidos.
- RB-04: placa deve ser normalizada para formato alfanumerico uppercase com ate 7 caracteres.

## 5. Dependencias externas

- API Placa/FIPE (configurada por variaveis `NUXT_PLACA_FIPE_*`).
- MongoDB opcional para sincronizacao server-side.
