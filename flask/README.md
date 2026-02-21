# Flask API

API Flask básica do Picareta.

## Setup

⚠️ **Importante**: Instale as dependências Python antes de rodar o servidor!

```bash
# Na pasta flask/
pip install -r requirements.txt
```

## Desenvolvimento

```bash
# Opção 1: Direto na pasta flask/
cd flask
python app.py

# Opção 2: Via pnpm da raiz do projeto
pnpm service:flask
```

O servidor estará disponível em `http://localhost:5000`

## Endpoints

- `GET /` - Endpoint principal, retorna status da API

**Exemplo de resposta:**

```json
{
  "message": "Picareta Flask API",
  "status": "ok",
  "version": "1.0.0"
}
```

## Configuração

Via variáveis de ambiente:

- `FLASK_PORT` - Porta do servidor (default: 5000)
- `FLASK_DEBUG` - Modo debug (default: False)
