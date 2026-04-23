#!/usr/bin/env bash
# Entrypoint for Modal-hosted test deployments. Brings up the DB via the
# upstream docker-entrypoint.sh, waits for it to accept connections, then
# runs the ZenML server in the foreground so the sandbox lifecycle tracks it.
set -euo pipefail

: "${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD must be set}"
: "${MYSQL_DATABASE:=zenml}"
: "${ZENML_SERVER_PORT:=8080}"

echo "[modal-entrypoint] starting database daemon in background..."
/usr/local/bin/docker-entrypoint.sh mysqld &
DB_PID=$!

echo "[modal-entrypoint] waiting for database to accept connections..."
for _ in $(seq 1 60); do
    if mysqladmin ping --silent \
        -h 127.0.0.1 \
        -uroot \
        -p"${MYSQL_ROOT_PASSWORD}" 2>/dev/null; then
        break
    fi
    if ! kill -0 "${DB_PID}" 2>/dev/null; then
        echo "[modal-entrypoint] database daemon exited before becoming ready" >&2
        exit 1
    fi
    sleep 2
done

if ! mysqladmin ping --silent -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" 2>/dev/null; then
    echo "[modal-entrypoint] database did not become ready in time" >&2
    exit 1
fi

echo "[modal-entrypoint] database ready; starting ZenML server on :${ZENML_SERVER_PORT}..."
exec uvicorn zenml.zen_server.zen_server_api:app \
    --host 0.0.0.0 \
    --port "${ZENML_SERVER_PORT}" \
    --log-level info
