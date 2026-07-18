#!/bin/sh
# Runs before nginx starts (dropped into nginx:alpine's /docker-entrypoint.d/).
# 1) Inject the backend URL from the API_BASE env var into the runtime config.
# 2) Bind nginx to the platform-provided $PORT (Railway/Fly/etc.).
set -e

: "${API_BASE:=}"
: "${PORT:=8080}"

printf 'window.__APP_CONFIG__ = { apiBase: "%s" };\n' "$API_BASE" \
  > /usr/share/nginx/html/config.js

sed -i "s/listen 8080;/listen ${PORT};/" /etc/nginx/conf.d/default.conf

echo "[cibmtr] serving on :${PORT}  apiBase='${API_BASE:-<demo mode>}'"
