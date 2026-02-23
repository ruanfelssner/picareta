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
- `PLATE_OCR_MAX_SIDE` - Lado maximo da imagem para processamento OCR (default: 1440)
- `PLATE_OCR_MAX_FALLBACK_REGIONS` - Quantidade maxima de regioes de fallback OCR (default: 4)
- `PLATE_OCR_STRONG_CONFIDENCE` - Limiar para parar pipeline cedo quando candidato forte aparece (default: 0.72)
- `PLATE_OCR_UPSCALE_MAX_SIDE` - Lado maximo para aplicar upscale OCR (default: 900)
- `PLATE_OCR_PREPROCESS_MAX_PIXELS` - Limite de pixels para preprocessamentos mais pesados (default: 1400000)
- `PLATE_OCR_PRELOAD_MODELS` - Precarrega YOLO/EasyOCR no boot (default: false)
- `PLATE_OCR_AMBIGUOUS_DELTA` - Delta maximo de confianca para considerar top-2 ambiguos (default: 0.06)
- `PLATE_OCR_ZERO_PRIORITY_DELTA` - Delta maximo para priorizar `...0` quando disputar com `...7` no ultimo digito (default: 0.05)

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
