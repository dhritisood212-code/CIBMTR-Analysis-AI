# Frontend container for Railway (and any Docker host). Build context = the frontend/ dir.
# Multi-stage: build the Vite bundle with Node, then serve it with nginx.
#
# The backend URL is injected at CONTAINER START from the API_BASE env var (see
# docker-entrypoint.sh), so you can point the deployed frontend at your backend by setting one
# Railway variable — no rebuild. Railway provides $PORT; the entrypoint binds nginx to it.

# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build          # -> /app/dist  (tsc -b && vite build)

# --- serve stage ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/99-cibmtr.sh
RUN chmod +x /docker-entrypoint.d/99-cibmtr.sh
ENV API_BASE=""
# Railway/other hosts inject $PORT; nginx.conf defaults to 8080 and the entrypoint rewrites it.
EXPOSE 8080
