# Stage 1: Build
FROM node:20 AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:18780/ || exit 1

# Unique port: 18780 (avoids conflicts with common web ports like 80/8080)
EXPOSE 18780
CMD ["nginx", "-g", "daemon off;"]
