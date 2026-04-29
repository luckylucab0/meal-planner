# Multi-Stage: Vite-Build im Node-Image, Auslieferung über schlankes nginx.
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Glob-Muster kopiert nginx.htpasswd wenn vorhanden, schlägt aber nicht fehl
# wenn nur die .example-Datei existiert (Build bleibt lauffähig ohne Auth-File).
COPY ./nginx.htpasswd* /etc/nginx/
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
