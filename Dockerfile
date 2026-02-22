FROM node:20-slim

WORKDIR /app

# Instalar dependências do sistema para Node e Python
RUN corepack enable && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      supervisor \
      python3 \
      python3-pip \
      python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Node.js
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --no-frozen-lockfile

# Copiar e instalar dependências Python
COPY flask/requirements.txt ./flask/
RUN pip3 install --break-system-packages --no-cache-dir -r flask/requirements.txt && \
    python3 -c "import ultralytics; print('ultralytics:', ultralytics.__version__)"

# Copiar código fonte
COPY . .

# Build Nuxt
RUN pnpm build

# Variáveis de ambiente
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1

# Expor portas (3000 para Nuxt, 5000 para Flask)
EXPOSE 3000 5000

# Copiar configuração do supervisor
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
