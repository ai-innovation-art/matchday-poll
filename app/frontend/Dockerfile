# syntax=docker/dockerfile:1
# Build (from the repository root):  docker build -t poll-frontend:1.0 app/frontend
#
# Runs as a non-root user (uid 101) and listens on 8080.
# It forwards /api/* to a Service named "backend" on port 8000, resolved when nginx starts:
# if that Service does not exist yet, the container exits with "host not found in upstream".
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 8080
