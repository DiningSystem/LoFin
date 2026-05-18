#!/usr/bin/env bash
set -euo pipefail
cp -n .env.example .env || true
docker compose up -d postgres redis qdrant ollama
printf 'Pulling default Ollama models (this can take a while)\n'
docker compose exec ollama ollama pull llama3.1 || true
docker compose exec ollama ollama pull nomic-embed-text || true
