# Stage 1: Build
FROM node:20 AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
# VITE_API_BASE_URL can be set at build time (default: /api/v1 for nginx proxy)
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Default port: 18780 (override via NGINX_PORT env var for Easypanel or other deployments)
# Backend port: 18700 (override via BACKEND_PORT for Easypanel: 19100)
ENV NGINX_PORT=18780
ENV BACKEND_PORT=18700
EXPOSE ${NGINX_PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:${NGINX_PORT}/ || exit 1

# Use envsubst to inject NGINX_PORT and BACKEND_PORT into the config at runtime
CMD ["/bin/sh", "-c", "envsubst '${NGINX_PORT} ${BACKEND_PORT}' < /etc/nginx/conf.d/default.conf > /tmp/nginx.conf && mv /tmp/nginx.conf /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
