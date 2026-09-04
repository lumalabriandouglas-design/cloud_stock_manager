FROM node:22-bookworm-slim
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --include=dev

COPY . .
ENV VITE_AUTH_ENABLED=true
ENV NPM_CONFIG_PRODUCTION=false
ENV NPM_CONFIG_ENGINE_STRICT=false
RUN npm run build

ENV HOST=0.0.0.0
ENV NITRO_HOST=0.0.0.0
ENV NODE_ENV=production
EXPOSE 8080
CMD ["node", "scripts/start-railway.mjs"]
