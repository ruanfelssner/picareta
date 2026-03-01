# 03 - Proposta UI/UX Mobile (fluxo 1 veiculo por vez)

## 1. Objetivo

Maximizar velocidade de decisao no patio/leilao com foco em um unico veiculo ativo por vez, reduzindo ruido visual e a quantidade de toques para chegar no valor de compra e no lucro projetado.

## 2. Principios de UX

- Priorizar tarefa principal: foto frontal -> placa -> FIPE -> custos -> decisao.
- Mostrar apenas o essencial na primeira dobra da tela.
- Tratar recursos avancados (fila e ajustes extras) como secundarios e opcionais.
- Garantir leitura rapida em ambiente externo (contraste alto, cards claros, tipografia forte).
- Padronizar componentes de toque (44px+ de altura util).

## 3. Jornada mobile proposta

1. Usuario abre a home e ja encontra acao principal `Tirar foto`.
2. Captura foto frontal e OCR retorna placa + ate 3 candidatos.
3. Usuario confirma placa no input `PLACA` e toca `Check`.
4. App preenche FIPE/dados e usuario informa `KM`, tipo de monta e custos.
5. Bloco financeiro exibe 4 cards: `Valor compra`, `Media venda`, `Custos`, `Lucro total`.
6. Usuario salva como `Carro atual` (status `em_andamento`) e usa a sequencia operacional: `Adquirir -> Anunciar -> Vender -> Reativar`.

## 4. Estrutura da interface

### 4.1 Home (nova hierarquia)

- Remover a sensacao de "layer dentro de layer" no bloco de foto.
- `Tirar foto` como botao principal grande (ocupando area central).
- `Escolher da galeria` como acao secundaria compacta (icone pequeno + label).
- Fila de processamento oculta por padrao (modo avancado, recolhido).
- Lista simples de `Carros atuais` na propria home com: placa, modelo, lucro, status e botao de abrir.

### 4.2 Bloco "Veiculo atual"

- Linha de placa simplificada:
  - Input `PLACA` sempre editavel.
  - Botao `Check` na mesma linha para consulta/reconsulta.
  - Candidatos OCR abaixo, no maximo 3 chips.
- Remover bloco redundante de "placa + candidatos" dentro de outro container.
- Dados principais em leitura rapida:
  - Marca/Modelo e Ano.
  - Campo novo `KM` no topo da secao.
- Galeria do veiculo:
  - Thumbnail principal = `crop` da placa (resultado OCR).
  - Demais fotos em grade horizontal com adicionar/remover.

### 4.3 Tipo de monta

- Opcoes:
  - `Sem monta` (venda 0% abaixo da FIPE).
  - `Pequena monta` (venda 5% abaixo da FIPE).
  - `Media monta` (venda 20% abaixo da FIPE).
- Regra de custo:
  - Em `sem_monta`, custo padrao `Leilao` nao entra automaticamente.

### 4.4 Custos

- Select de custos com tamanho maior e melhor area de toque.
- Todos os itens com regra por faixa FIPE devem preencher valor sugerido corretamente.
- Total de custos dentro do modulo deve ficar discreto (texto simples), sem box azul de destaque.

### 4.5 Bloco financeiro (decisao)

- Substituir nomenclaturas:
  - `Valor maximo no leilao` -> `Valor compra`.
  - `Valor medio de venda` -> `Media venda`.
- Layout em 4 cards:
  - `Valor compra`: default `FIPE - margem - custos`, com check para habilitar edicao manual.
  - `Media venda`: `FIPE - %` conforme tipo de monta.
  - `Custos`: soma total dos itens.
  - `Lucro total`: `Media venda - (Valor compra + Custos)`.
- Remover secao "Detalhes" e colocar acao de salvar no fluxo principal.

## 5. Modelo de dados impactado

- Novo campo `km: number | null`.
- Novo campo `status: 'em_andamento' | 'adquirido' | 'anunciado' | 'vendido'`.
- Novo campo `plateCropDataUrl?: string` para thumbnail OCR.
- Novo campo `galleryPhotos?: string[]` para fotos adicionais.
- Novo campo `purchaseOverrideEnabled?: boolean` para controlar edicao manual do valor de compra.

## 6. Entregas por fase

### Fase 1 - Ajuste visual e fluxo principal

- Simplificar Home e bloco de captura.
- Esconder fila por padrao.
- Simplificar linha de placa com botao `Check`.
- Renomear cards de decisao e remover bloco de detalhes.

### Fase 2 - Dados e calculo

- Incluir `sem_monta` com regra de custo leilao.
- Incluir campo `KM`.
- Corrigir preenchimento automatico de custos por faixa FIPE.
- Adicionar cards `Custos` e `Lucro total`.

### Fase 3 - Persistencia e operacao

- Migrar "Carros salvos" para "Carros atuais".
- Persistir status na sequencia operacional (`em_andamento`, `adquirido`, `anunciado`, `vendido`), com `Reativar` retornando para `em_andamento`.
- Adicionar galeria de fotos por veiculo e thumbnail de crop OCR.

## 7. Criterios de aceite (UI/UX)

- Fluxo completo (foto -> check placa -> analise -> salvar) concluido sem abrir modal de detalhes.
- Usuario consegue revisar e corrigir placa em um unico ponto da tela.
- Fila nao compete visualmente com o cadastro principal na home.
- Cards financeiros mostram decisao de compra sem texto tecnico redundante.
- Lista de carros atuais permite retomar avaliacao em ate 1 toque.
