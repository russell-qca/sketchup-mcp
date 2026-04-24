#!/bin/bash
# Start the Deck Designer API server

set -e

echo "========================================="
echo "Deck Designer API Server"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "Please edit .env and add your ANTHROPIC_API_KEY"
    echo "Then run this script again."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo "Starting FastAPI server..."
echo "API will be available at: http://localhost:${API_PORT:-8000}"
echo "API docs at: http://localhost:${API_PORT:-8000}/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the server
PYTHONPATH=./src uvicorn deck_designer.api:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --reload
