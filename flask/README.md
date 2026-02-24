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

## Template de caracteres (fontes.svg)

Para aproveitar `public/fontes.svg` no OCR de baixa confianca:

```bash
python flask/scripts/build_char_templates_from_svg.py --debug-preview
```

Isso gera `flask/models/char_templates.json` (consumido automaticamente pelo Flask para `template_rerank`).
Com esse arquivo versionado no deploy, nao precisa rodar o script em PRD.

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

- OCR: `MAX_PROCESS_SIDE=1280`, `OCR_MAX_PROCESS_MS=30000`, `OCR_MAX_VARIANTS=3`, `OCR_MAX_FALLBACK_REGIONS=3`, `OCR_NO_YOLO_MAX_FALLBACK_REGIONS=3`, `OCR_MIN_TEXT_CONFIDENCE=0.14`, `OCR_PRELOAD_MODELS=true`.
- Etapa intermediaria: tentativa por contornos de placa (`contour_plate_regions`) antes do fallback amplo, limitada a 3 regioes/2 variantes para conter latencia.
- Rescue (sem YOLO e sem candidato): `OCR_RESCUE_MAX_VARIANTS=4`, `OCR_RESCUE_MIN_TEXT_CONFIDENCE=0.08`.
- Priorizacao adicional: empate em `...7` vs `...0` no ultimo digito e empate em letra/digito no 5o caractere (ex.: `KRS2102` vs `KRS2I02`).
- Ambiguidade de letras usa custo ponderado por substituicao (nao apenas contagem inteira) para melhorar prefixos confusos como `ATU` vs `RYO`.
- Em baixa confianca, backend aplica `template_rerank` com base em `flask/models/char_templates.json` (extraido de `public/fontes.svg`).
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
