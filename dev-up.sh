#!/usr/bin/env bash
set -e
docker compose up -d
until docker compose exec -T postgres pg_isready -U notifyhub -d notifyhub >/dev/null 2>&1; do
  sleep 1
done
echo "Stack ready: Postgres, Redis and Mailpit are up."
