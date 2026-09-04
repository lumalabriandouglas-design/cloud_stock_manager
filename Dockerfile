FROM node:20-slim
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --omit=dev=false

COPY . .
ENV VITE_AUTH_ENABLED=true
ENV NITRO_PRESET=node-server
RUN npm run build

ENV HOST=0.0.0.0
ENV NITRO_HOST=0.0.0.0
ENV NODE_ENV=production
EXPOSE 8080
CMD ["node", ".output/server/index.mjs"]
