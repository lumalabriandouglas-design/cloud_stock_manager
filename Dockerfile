FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
ENV NITRO_PRESET=node-server
RUN npm run build
ENV HOST=0.0.0.0
ENV PORT=8080
EXPOSE 8080
CMD ["node", "scripts/start-railway.mjs"]
