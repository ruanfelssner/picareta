# AGENTS.md

## Objetivo

Criar uma estrutura para utilizar indexedDB de front/api em nuxt para poder cadastrar carros de leilão e imaginar preço do carro feito e a margem.

- integração com api placa fipe ( através da imagem de frente ) pegar a placa, buscar no placa fipe e trazer os dados daquele carro, como valor da fipe, e vir adicionando custos como portas, pintura, mecanica, suspensão, vidros etc. no final soma tudo e compara com o valor da fipe e uma porcentagem.

## Regras de documentacao

- Toda documentacao do produto e arquitetura fica em `docs/`.
- Arquivos devem seguir prefixo numerico: `01-...`, `02-...`, `03-...`.
- Atualize `docs/01-requisitos.md` quando surgir/alterar requisito.
- Evite criar novos .md fora de `docs/` (exceto `README.md`).

## Regras de arquitetura (resumo)

## Diretrizes operacionais

- Evitar criar novas env vars para tuning de OCR/Gunicorn.
- Parametros de performance de producao devem ficar fixos no codigo (zero-config em PRD).

## Nomenclaturas
