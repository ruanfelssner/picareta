# 01 - Requisitos do Produto

## 1. Contexto

O projeto Picareta precisa permitir avaliacao rapida de carros de leilao no celular, com foco em margem e tomada de decisao imediata no patio/leilao.

## 2. Requisitos funcionais

- RF-01: cadastrar carro com dados basicos (placa, marca, modelo, ano, valor de compra, valor FIPE, observacoes).
- RF-02: aceitar foto frontal do carro via camera do celular.
- RF-02.1: expor endpoint de OCR de placa que receba imagem em base64 (string pura ou data URL) e retorne placa/candidatos em JSON.
- RF-02.2: manter endpoint versionado `POST /api/v1/plate/recognize` com payload `imageBase64` para integracao direta com Nuxt.
- RF-02.3: em producao, o frontend deve chamar OCR via mesma origem (`/api/v1/plate/recognize` no Nuxt server), e o Nuxt deve encaminhar para o Flask interno configurado por `NUXT_FLASK_BASE_URL`.
- RF-02.4: quando OCR retornar candidatos ambiguos para a mesma base de placa (ex.: mesmos 6 primeiros caracteres e ultimo digito diferente), o sistema nao deve consultar FIPE automaticamente; deve exigir confirmacao manual da placa no Step 2.
- RF-02.5: em quase empate de confianca entre candidatos `...7` e `...0` no ultimo digito, priorizar `...0` na ordenacao de candidatos para acelerar a confirmacao manual.
- RF-02.6: a fila de fotos deve permitir preview ampliado da imagem antes de preencher o cadastro, para conferir placa visualmente no celular.
- RF-02.7: no Step 2, placa e candidatos do OCR devem aparecer no mesmo bloco de confirmacao para reduzir erro operacional.
- RF-02.8: no Step 2, marca/modelo e ano devem ficar na mesma linha para leitura rapida em campo.
- RF-02.9: no Step 2, o campo da placa deve ficar sempre editavel e o botao de consultar novamente deve ficar na mesma linha dos candidatos OCR.
- RF-02.10: ao apresentar candidatos do OCR, a primeira sugestao deve vir selecionada por padrao.
- RF-02.11: no preview da fila, candidatos OCR devem ficar sobrepostos na imagem e a confirmacao deve ocorrer ao tocar no candidato (sem botao extra de preencher).
- RF-02.12: ao tocar em um candidato de placa (Step 2 ou preview da fila), o sistema deve entrar em loading e consultar Placa FIPE imediatamente.
- RF-02.13: cada foto na fila deve exibir contador de tempo de processamento em tempo real (etapa OCR/FIPE) e duracao final ao concluir.
- RF-02.14: confirmacoes manuais de placa devem alimentar aprendizado compartilhado (persistido no backend em Mongo) para repriorizar candidatos OCR semelhantes em novas imagens.
- RF-02.15: cada confirmacao manual deve registrar: placa reconhecida, placa confirmada, candidatos, `bbox` e `crop` da placa em base64 para formar dataset treinavel.
- RF-02.16: disponibilizar endpoint de perfil agregado de feedback OCR para o frontend consumir pesos de repriorizacao sem depender de `localStorage`.
- RF-02.17: disponibilizar rotina Python diaria para consumir a colecao de feedback OCR e exportar dataset treinavel.
- RF-02.18: persistir apenas feedback util de OCR (correcao real, ambiguidade confirmada ou falha de reconhecimento), descartando confirmacoes redundantes sem ganho de treino.
- RF-02.19: parametros de performance OCR/Gunicorn devem usar perfil fixo de producao no codigo (sem depender de novas env vars de tuning).
- RF-02.20: suportar bootstrap de templates de caracteres a partir de `public/fontes.svg` para reranquear candidatos OCR em cenarios de baixa confianca.
- RF-03: consultar dados de placa/FIPE via API externa (quando configurada).
- RF-03.1: consulta de placa/FIPE deve ocorrer por placa informada manualmente.
- RF-03.2: integrar com `https://api.placafipe.com.br` usando `POST /getplacafipe` como consulta principal da placa + valor FIPE.
- RF-03.3: quando `getplacafipe` nao retornar dados suficientes do veiculo, executar fallback com `POST /getplaca`.
- RF-03.4: extrair no minimo: marca, modelo, ano, ano modelo, cor, cilindrada, potencia, combustivel, chassi, motor, UF, municipio, segmento e sub-segmento.
- RF-03.5: integrar `POST /getquotas` para consultar limite diario sem consumir quota.
- RF-03.6: UI deve exibir buscas restantes do dia (`limite_diario - uso_diario`) e permitir atualizar esse indicador manualmente.
- RF-03.10: indicador de buscas restantes deve ficar no header global ao lado do botao "Carros salvos" (fora do card "Foto do veiculo"), com acao de atualizar.
- RF-03.7: quando provider retornar detalhes da placa sem valor FIPE, esses dados devem ser preservados no retorno da API.
- RF-03.8: resultados de consulta por placa devem ser cacheados em base (`Mongo`) para evitar novo custo em consultas repetidas da mesma placa.
- RF-03.9: disponibilizar modo mock por ambiente (`NUXT_PLACA_FIPE_MOCK=true`) para testes sem consumo de quota da API externa.
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
- RF-08.1: ao abrir um carro salvo para edicao, a UI deve exibir acao explicita de "Fechar edicao" para voltar ao estado inicial da home.
- RF-09: sincronizar registro para API server.
- RF-10: expor API com colecao dedicada para carros de leilao (`auction_cars`).
- RF-11: disponibilizar instalacao do app como PWA no celular (incluindo iPhone via Safari).
- RF-11.1: mostrar modal orientando instalacao quando app nao estiver instalado.
- RF-11.2: quando navegador suportar `beforeinstallprompt`, permitir acao direta de instalacao pela modal.

### 2.1 Ajustes UX Mobile (ciclo 2026-02)

- RF-12: fluxo padrao deve priorizar avaliacao de 1 veiculo por vez (sem dependencia da fila visivel na home).
- RF-12.1: o bloco "Foto do veiculo" deve ocupar a largura util da tela, sem camada interna adicional que reduza area de captura.
- RF-12.2: "Tirar foto" deve ser acao primaria e "Escolher da galeria" deve ser acao secundaria compacta (icone + texto curto).
- RF-12.3: a imagem principal apos OCR deve priorizar o `crop` da placa como thumbnail; fotos completas devem ficar na galeria do carro.
- RF-12.4: fila de processamento deve ficar oculta por padrao; quando habilitada, deve funcionar como modo avancado sem ocupar area fixa.
- RF-12.5: sugestoes OCR para confirmacao manual devem exibir no maximo 3 candidatos.
- RF-12.6: no bloco de dados, placa deve ser `input` sempre editavel com botao unico `Check` para consultar/reconsultar FIPE.
- RF-12.7: apos editar manualmente a placa, o usuario deve conseguir executar novo `Check` sem trocar de tela.
- RF-12.8: incluir campo dedicado de quilometragem (`KM`) no topo dos dados do veiculo.
- RF-12.9: permitir anexar multiplas fotos adicionais no proprio bloco de dados do veiculo.
- RF-12.10: a home deve listar "Carros atuais" em lista simples para retomada rapida.
- RF-13: tipo de monta deve suportar tres opcoes: `sem_monta`, `pequena`, `media`.
- RF-13.1: em `sem_monta`, o desconto de venda sobre FIPE deve ser de 0%.
- RF-13.2: em `sem_monta`, o custo padrao `Leilao` nao deve ser adicionado automaticamente.
- RF-13.3: seletor de custos deve ter area de toque ampliada e legibilidade mobile.
- RF-13.4: custos com valor sugerido por faixa FIPE devem preencher valor automaticamente em todas as opcoes configuradas.
- RF-13.5: o total de custos dentro do bloco de custos deve ser exibido em texto discreto (sem card de destaque visual).
- RF-13.6: deve existir item automatico de custo por tipo de monta (`Tipo monta`), recalculado dinamicamente ao trocar entre `sem_monta`, `pequena` e `media` e ao alterar a FIPE.
- RF-14: bloco de decisao financeira deve exibir 4 cards: `Valor compra`, `Media venda`, `Custos`, `Lucro total`.
- RF-14.1: substituir o rotulo "Valor maximo no leilao" por "Valor compra".
- RF-14.2: `Valor compra` padrao deve seguir `FIPE - margem alvo - custos`.
- RF-14.3: `Valor compra` deve permitir edicao manual por check/toggle no proprio card.
- RF-14.4: substituir o rotulo "Valor medio de venda" por "Media venda".
- RF-14.5: remover a secao "Detalhes" e manter salvamento no fluxo principal da tela.
- RF-15: conceito de "Carros salvos" deve migrar para "Carros atuais".
- RF-15.1: cada carro deve possuir status operacional minimo (`em_andamento`, `adquirido`, `anunciado`, `vendido`).
- RF-15.2: a acao rapida na lista deve seguir a sequencia operacional: `em_andamento -> Adquirir -> Anunciar -> Vender -> Vendido -> Reativar -> em_andamento`.
- RF-15.3: quando status for `vendido`, o card em "Carros atuais" deve usar visual em tons de cinza para indicar encerramento.

## 3. Requisitos nao funcionais

- RNF-01: UI mobile-first com navegacao por toque e leitura rapida em tela pequena.
- RNF-02: operacao local deve funcionar sem internet para cadastro e calculo.
- RNF-03: tempo de resposta percebido deve ser imediato para calculo de margem (sem roundtrip para API).
- RNF-04: validacao de payload no backend para reduzir dados inconsistentes.
- RNF-05: arquitetura deve separar camada de UI, regras de calculo e integracao externa.
- RNF-06: fluxo principal deve reduzir friccao para no maximo 2 a 3 toques entre foto inicial e analise de margem.
- RNF-07: inputs, selects e botoes interativos devem respeitar area minima de toque de 44px no mobile.
- RNF-08: componentes secundarios (fila avancada/modais de sugestao) devem ser opcionais e nao competir com a tarefa principal de avaliacao.

## 4. Regras de negocio

- RB-01: margem percentual = `(lucro estimado / valor venda estimado) * 100`.
- RB-02: lucro estimado = `valor venda estimado - (valor compra + custos totais)`.
- RB-03: custos negativos nao sao permitidos.
- RB-04: placa deve ser normalizada para formato alfanumerico uppercase com ate 7 caracteres.
- RB-05: valor venda estimado deve aplicar fator por tipo de monta (`sem_monta=100% FIPE`, `pequena=95% FIPE`, `media=80% FIPE`).
- RB-06: valor compra padrao deve ser calculado por `FIPE - margem alvo - custos`, com opcao de override manual quando habilitada.
- RB-07: custo padrao `Leilao` deve ser automatico apenas quando tipo de monta for diferente de `sem_monta`.
- RB-08: novo registro deve iniciar com status `em_andamento`.
- RB-09: custo automatico `Tipo monta` deve permanecer sincronizado com o tipo de monta selecionado e com a faixa FIPE vigente.
- RB-10: OCR deve priorizar placas no formato Mercosul `AAA0A00` (padrao principal), mantendo suporte ao formato antigo `AAA0000` como fallback raro.
- RB-11: quando candidatos de OCR divergirem apenas no prefixo por ambiguidade visual (ex.: `Y`/`V`) e estiverem proximos de confianca, o sistema deve marcar como ambiguo e exigir confirmacao manual.
- RB-12: quando OCR apresentar baixa robustez (pouco suporte entre candidatos, decoder de beam em baixa confianca ou empate curto entre top-2), o sistema nao deve confirmar automaticamente a placa; deve exigir confirmacao manual.
- RB-13: em leitura OCR baseada em `yolo_box`, o texto reconhecido deve passar por validacao de plausibilidade geometrica do bounding box (aspect ratio/cobertura minima no crop) antes de entrar no ranking final.
- RB-14: deteccoes YOLO com geometria improvavel para placa (aspect ratio, area relativa e posicao no frame) devem ser descartadas antes da etapa de OCR para evitar capturar chassis/VIN no vidro.

## 5. Dependencias externas

- API Placa/FIPE (configurada por `NUXT_PLACA_FIPE_BASE_URL` e `NUXT_PLACA_FIPE_TOKEN` quando `NUXT_PLACA_FIPE_MOCK=false`).
- MongoDB opcional para sincronizacao server-side.
