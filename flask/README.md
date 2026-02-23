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
- `GET /test` - Testa reconhecimento com imagem local em `data/test`
- `POST /recognize-base64` - Reconhece placa a partir de imagem em base64
- `POST /api/v1/plate/recognize` - Endpoint padrao para consumo direto do Nuxt

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
- `MAX_IMAGE_BYTES` - Limite de bytes aceito no endpoint base64 (default: 12582912)

Parametros de tuning de OCR/Gunicorn ficam fixos no codigo com perfil padrao de producao (nao dependem de env):

- OCR: `MAX_PROCESS_SIDE=1280`, `OCR_MAX_PROCESS_MS=30000`, `OCR_MAX_VARIANTS=2`, `OCR_MAX_FALLBACK_REGIONS=3`, `OCR_NO_YOLO_MAX_FALLBACK_REGIONS=2`, `OCR_MIN_TEXT_CONFIDENCE=0.18`, `OCR_PRELOAD_MODELS=true`.
- YOLO: `imgsz=640`, `max_det=3`.
- Gunicorn: `1 worker`, `gthread`, `2 threads`, `timeout=180`, `graceful-timeout=45`, `max-requests=200`, `jitter=30`.

## Exemplo do endpoint base64

```bash
curl -X POST "http://localhost:5000/recognize-base64" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "nivus.jpeg",
    "base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
  }'
```

## Exemplo (Nuxt direto)

```bash
curl -X POST "http://localhost:5000/api/v1/plate/recognize" \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "req-123",
    "filename": "nivus.jpeg",
    "imageBase64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
  }'
```
