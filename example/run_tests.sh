#!/bin/bash

echo "Starting API Integration Tests"
echo "==============================="
echo ""
echo "Prerequisites:"
echo "1. API server running at http://0.0.0.0:8002"
echo "2. Ollama running with llama3.2:3b model"
echo ""

# Check if API is running
if ! curl -s http://0.0.0.0:8002/ > /dev/null; then
    echo "❌ API server not running at http://0.0.0.0:8002"
    echo "Start it with: uv run main.py"
    exit 1
fi

echo "✓ API server is running"
echo ""

# Run tests
pytest test_api.py -v -s --tb=short

echo ""
echo "Tests completed!"
