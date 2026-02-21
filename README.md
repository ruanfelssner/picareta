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
✅ Cálculo de margem em tempo real  
✅ Operação offline com IndexedDB  
✅ Sincronização com backend quando online

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
- `NUXT_PUBLIC_FLASK_BASE_URL`: URL base do Flask usada pelo frontend (default: http://localhost:5000)
- `NUXT_PUBLIC_FLASK_TIMEOUT_MS`: timeout da chamada OCR Flask em ms (default: 120000)
- `NUXT_MONGO_URI`: Connection string do MongoDB
- `NUXT_PLACA_FIPE_BASE_URL`: base URL do provider de placa/FIPE
- `NUXT_PLACA_FIPE_LOOKUP_PATH`: path de lookup (default: /lookup)
- `NUXT_PLACA_FIPE_LOOKUP_METHOD`: metodo HTTP do provider (`POST` default)
- `NUXT_PLACA_FIPE_REQUEST_PLATE_FIELD`: nome do campo enviado no body/query (`placa` default)
- `NUXT_PLACA_FIPE_DEVICE_TOKEN`: header `DeviceToken` opcional para providers que exigem esse header
- `NUXT_PLACA_FIPE_USER_AGENT`: user-agent da chamada ao provider
- `NUXT_PLACA_FIPE_TOKEN`: Token da API Placa FIPE
- `NUXT_PLACA_FIPE_TIMEOUT_MS`: timeout do lookup Placa/FIPE em ms (default: 8000)
- `NUXT_PLACA_FIPE_LOOKUP_STRATEGY`: estrategia de consulta (`scrape-first` default, `provider-first`, `scrape-only`, `provider-only`)
- `NUXT_PLACA_FIPE_CF_CLEARANCE`: cookie `cf_clearance` opcional para scraping quando Cloudflare bloquear
