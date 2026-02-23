# 01 - Requisitos do Produto

## 1. Contexto

O projeto Picareta precisa permitir avaliacao rapida de carros de leilao no celular, com foco em margem e tomada de decisao imediata no patio/leilao.

## 2. Requisitos funcionais

- RF-01: cadastrar carro com dados basicos (placa, marca, modelo, ano, valor de compra, valor FIPE, observacoes).
- RF-02: aceitar foto frontal do carro via camera do celular.
- RF-02.1: expor endpoint de OCR de placa que receba imagem em base64 (string pura ou data URL) e retorne placa/candidatos em JSON.
- RF-02.2: manter endpoint versionado `POST /api/v1/plate/recognize` com payload `imageBase64` para integracao direta com Nuxt.
- RF-02.3: em producao, o frontend deve chamar OCR via mesma origem (`/api/v1/plate/recognize` no Nuxt server), e o Nuxt deve encaminhar para o Flask interno configurado por `NUXT_FLASK_BASE_URL`.
- RF-03: consultar dados de placa/FIPE via API externa (quando configurada).
- RF-03.1: consulta de placa/FIPE deve ocorrer por placa informada manualmente.
- RF-03.2: integrar com `https://api.placafipe.com.br` usando `POST /getplacafipe` como consulta principal da placa + valor FIPE.
- RF-03.3: quando `getplacafipe` nao retornar dados suficientes do veiculo, executar fallback com `POST /getplaca`.
- RF-03.4: extrair no minimo: marca, modelo, ano, ano modelo, cor, cilindrada, potencia, combustivel, chassi, motor, UF, municipio, segmento e sub-segmento.
- RF-03.5: integrar `POST /getquotas` para consultar limite diario sem consumir quota.
- RF-03.6: UI deve exibir buscas restantes do dia (`limite_diario - uso_diario`) e permitir atualizar esse indicador manualmente.
- RF-03.7: quando provider retornar detalhes da placa sem valor FIPE, esses dados devem ser preservados no retorno da API.
- RF-03.8: resultados de consulta por placa devem ser cacheados em base (`Mongo`) para evitar novo custo em consultas repetidas da mesma placa.
- RF-04: quando API externa nao estiver configurada, manter fallback local mock para nao bloquear o fluxo.
- RF-05: cadastrar custos por item (pintura, mecanica, suspensao, vidros, portas e outros).
- RF-05.1: fluxo de custos deve iniciar com item padrao `Leilao` no valor de `R$ 800`, mantendo edicao livre.
- RF-05.2: novos custos devem ser adicionados por seletor (select), com opcao `Outros` abrindo campo de descricao manual.
- RF-06: calcular em tempo real custo total, investimento total, lucro estimado e margem percentual.
- RF-06.1: operar em fluxo direto na mesma tela, com foto e consulta no topo, custos no meio e salvar carro no final.
- RF-06.2: usar logica reversa para estimar compra maxima no leilao: `compra maxima = FIPE - margem alvo - custos`.
- RF-06.3: margem alvo deve ser editavel e vir predefinida por faixa FIPE:
  - ate R$ 30.000 -> R$ 5.000
  - ate R$ 80.000 -> R$ 10.000
  - ate R$ 120.000 -> R$ 30.000
  - ate R$ 160.000 -> R$ 40.000
  - acima disso, progressao continua por faixas.
- RF-07: permitir salvar e listar carros localmente no aparelho (IndexedDB) para uso offline.
- RF-08: permitir reabrir e editar registros salvos localmente.
- RF-09: sincronizar registro para API server.
- RF-10: expor API com colecao dedicada para carros de leilao (`auction_cars`).
- RF-11: disponibilizar instalacao do app como PWA no celular (incluindo iPhone via Safari).
- RF-11.1: mostrar modal orientando instalacao quando app nao estiver instalado.
- RF-11.2: quando navegador suportar `beforeinstallprompt`, permitir acao direta de instalacao pela modal.

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

- API Placa/FIPE (configurada por `NUXT_PLACA_FIPE_BASE_URL` e `NUXT_PLACA_FIPE_TOKEN`).
- MongoDB opcional para sincronizacao server-side.
