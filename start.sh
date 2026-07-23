#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run the RAG processor to ensure the vector store is created
echo "--- Running RAG Processor to build vector store ---"
python rag_processor.py

# Now that the vector store is guaranteed to exist, start the main application.
# Use the PORT environment variable provided by Render.
echo "--- Starting FastAPI Backend Server ---"
uvicorn single_main:app --host 0.0.0.0 --port $PORT
