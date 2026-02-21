FROM node:20-slim

WORKDIR /app

RUN corepack enable
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    supervisor \
    python3 \
    python3-pip \
    tesseract-ocr \
    libglib2.0-0 \
    libgl1 \
  && rm -rf /var/lib/apt/lists/*

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --no-frozen-lockfile

RUN mkdir -p /app/server/scripts
COPY server/scripts/requirements-plate-ocr.txt ./server/scripts/requirements-plate-ocr.txt
RUN python3 -m pip install --no-cache-dir -r server/scripts/requirements-plate-ocr.txt

COPY . .
RUN pnpm build

ENV NODE_ENV=production

EXPOSE 3000

COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
