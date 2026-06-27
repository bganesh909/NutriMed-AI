#!/bin/bash
set -e

# ===========================================
# NutriMed AI - Ollama Model Initialization
# ===========================================
# This script pulls the required LLM models into Ollama.
# Run this after the Ollama container is up and healthy.

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
MAX_RETRIES=30
RETRY_INTERVAL=5

echo "============================================"
echo "  NutriMed AI - Ollama Model Setup"
echo "============================================"

# Wait for Ollama to be ready
echo "Waiting for Ollama service at ${OLLAMA_HOST}..."
retries=0
until curl -sf "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; do
    retries=$((retries + 1))
    if [ "$retries" -ge "$MAX_RETRIES" ]; then
        echo "ERROR: Ollama did not become ready after $((MAX_RETRIES * RETRY_INTERVAL)) seconds."
        exit 1
    fi
    echo "  Ollama not ready yet. Retrying in ${RETRY_INTERVAL}s... (${retries}/${MAX_RETRIES})"
    sleep "$RETRY_INTERVAL"
done
echo "Ollama is ready."

# Pull models
echo ""
echo "Pulling Llama 3 8B..."
ollama pull llama3:8b
echo "Llama 3 8B downloaded successfully."

echo ""
echo "Pulling Mistral 7B..."
ollama pull mistral:7b
echo "Mistral 7B downloaded successfully."

echo ""
echo "============================================"
echo "  All models are ready!"
echo "============================================"
echo ""
echo "Available models:"
ollama list
