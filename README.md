# RAG-based AI Travel Planner

A portfolio project that generates structured travel itineraries using retrieval-augmented generation.

## Overview

This project is an AI travel planning assistant. Users can enter a destination, travel dates, budget level, travel intensity, companions and personal preferences. The system retrieves relevant information from a local travel knowledge base and generates a structured itinerary.

## Features

- Travel itinerary generation based on destination and user preferences
- Retrieval-augmented generation with local travel knowledge base
- FAISS-based semantic search
- Streamlit user interface
- FastAPI backend
- Structured output including daily itinerary, attractions, food, transportation and travel tips
- Fallback generation when knowledge base context is insufficient

## Tech Stack

- Python
- Streamlit
- FastAPI
- FAISS
- Sentence Transformers
- LangChain
- Gemini API

## Project Structure

```text
.
├── streamlit_app.py
├── single_main.py
├── single_trip_agent.py
├── rag_processor.py
├── api_routes.py
├── knowledge_base/
├── faiss_store/
├── requirements.txt
├── .env.example
└── README.md