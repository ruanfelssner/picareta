# Picareta

Aplicacao Nuxt para cadastrar carros de leilao, estimar custos de recuperacao e calcular margem com base no valor FIPE.

## Stack

- **Frontend**: Nuxt 4 + Vue 3 + TailwindCSS
- **Backend Node.js**: Nitro (server API) + MongoDB
- **Backend Python**: Flask
- **Persistência**: IndexedDB (offline) + MongoDB (sincronização)

## Funcionalidades

✅ Cadastro de carros de leilão com fotos  
✅ Integração com API Placa FIPE  
✅ Indicador de quotas restantes na UI  
✅ Cache por placa no Mongo para reduzir custo de consulta  
✅ Cálculo de margem em tempo real  
✅ Operação offline com IndexedDB  
✅ Sincronização com backend quando online
✅ Instalação como PWA (Android/iPhone)

## Setup

### Pré-requisitos

- Node.js >= 20
- pnpm
- Python 3.8+
- MongoDB (via Docker ou local)
- Redis (via Docker ou local)

### Instalação

```bash
# Instalar dependências Node.js
pnpm install

# Instalar dependências Python
cd flask
pip install -r requirements.txt
cd ..

# Copiar variáveis de ambiente
cp .env.example .env
```

### Iniciar MongoDB e Redis (via Docker)

```bash
docker-compose up -d mongo redis
```

## Desenvolvimento

```bash
# Terminal 1: Nuxt
pnpm dev

# Terminal 2: Flask
pnpm service:flask
```

**URLs:**

- Nuxt Frontend: http://localhost:3000
- Flask API: http://localhost:5000

## Docker (Produção)

```bash
# Iniciar todos os serviços
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

## Instalacao no iPhone (PWA)

1. Abra o sistema no Safari.
2. Toque no botao **Compartilhar**.
3. Escolha **Adicionar a Tela de Inicio**.
4. Confirme em **Adicionar**.

Quando o app abrir no navegador e ainda nao estiver instalado, uma modal de convite sera exibida.

## Diagnostico OCR em producao

- Endpoint de health interno: `GET /api/v1/plate/health`
- Esse endpoint testa a conexao Nuxt -> Flask e retorna:
  - `targetBaseUrl` (base efetiva usada para o Flask)
  - `ok` (true/false)
  - `cause` quando houver falha (`ECONNREFUSED`, timeout etc.)

## Documentacao

- **Requisitos**: [docs/01-requisitos.md](docs/01-requisitos.md)
- **Arquitetura**: [docs/02-arquitetura-nuxt-indexeddb.md](docs/02-arquitetura-nuxt-indexeddb.md)
- **Plano funcional + UI mobile**: [docs/03-plano-funcionalidades-ui-mobile.md](docs/03-plano-funcionalidades-ui-mobile.md)

## Estrutura do Projeto

```
├── app/                      # Frontend Nuxt
│   ├── composables/         # Vue composables
│   ├── pages/               # Páginas/rotas
│   └── layouts/             # Layouts
├── server/                   # Backend Node.js (Nitro)
│   ├── api/v1/              # Endpoints API
│   ├── repositories/        # Camada de dados
│   └── utils/               # Utilitários (MongoDB, etc)
├── flask/                    # Backend Python (Flask)
│   ├── app.py               # API Flask
│   ├── config.py            # Configuração
│   └── requirements.txt     # Dependências Python
├── shared/                   # Código compartilhado
│   ├── types/               # TypeScript types
│   └── valuation.ts         # Lógica de cálculo de margem
└── docs/                     # Documentação
```

## Scripts npm/pnpm

```bash
pnpm dev              # Inicia Nuxt em modo dev
pnpm service:flask    # Inicia serviço Flask
pnpm build            # Build de produção do Nuxt
pnpm lint             # Lint do código
```

## Variáveis de Ambiente

Ver [.env.example](.env.example) para todas as opções.

Principais:

- `FLASK_PORT`: Porta do serviço Flask (default: 5000)
- `NUXT_FLASK_BASE_URL`: URL base do Flask usada pelo servidor Nuxt (default: http://127.0.0.1:5000). Em deploy unico, nao use o dominio publico do Nuxt para evitar loop de requisicao.
- `NUXT_FLASK_TIMEOUT_MS`: timeout da chamada OCR Flask em ms (default: 120000)
- `NUXT_MONGO_URI`: Connection string do MongoDB
- `NUXT_PLACA_FIPE_BASE_URL`: base URL do provider de placa/FIPE
- `NUXT_PLACA_FIPE_TOKEN`: token de autorizacao do provider
- `NUXT_PLACA_FIPE_MOCK`: quando `true`, usa resposta mock local e nao consome a API externa

### Exemplo de configuracao para API oficial

```bash
NUXT_PLACA_FIPE_BASE_URL=https://api.placafipe.com.br
NUXT_PLACA_FIPE_TOKEN=seu_token_aqui
NUXT_PLACA_FIPE_MOCK=false
```

Obs.: para nao consumir quota da API durante testes, use `NUXT_PLACA_FIPE_MOCK=true`.
Quando desativado, o backend usa os endpoints `POST /getplacafipe`, `POST /getplaca` (fallback) e `POST /getquotas`.
