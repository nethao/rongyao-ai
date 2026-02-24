# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Production
FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/frontend/nginx-frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
