# AI Content Transformation Platform - Backend

Backend service for the AI-powered content transformation platform developed for Smart India Hackathon 2026.

## Overview

This backend accepts source content such as text and documents, applies user-defined transformation parameters, uses AI to generate the requested communication artefact, and returns the generated output in the selected format.

## Architecture

Frontend
↓
FastAPI
↓
Input Processing
↓
Unified Source Text
↓
Prompt Builder
↓
LLM
↓
Generated Content
↓
Output Generator
↓
PDF / DOCX / PNG

## Features

- Text-based content transformation
- PDF and DOCX document processing
- Configurable target audience
- Configurable communication objective
- Configurable tone
- Configurable language
- Configurable detail level
- Configurable content style
- Multiple output types
- PDF, DOCX and PNG output
- AI-powered content generation using Groq
- Image understanding using Hugging Face vision models
- AI-generated visual output using Hugging Face image generation
- SHA-256 hashing for content integrity
- Hash-chained transformation records stored in MongoDB Atlas

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Groq API
- GPT-OSS 120B
- Hugging Face
- Qwen2.5-VL
- FLUX.1-schnell
- PyPDF
- python-docx
- ReportLab
- MongoDB Atlas
- SHA-256
- python-dotenv

## Project Structure

```text
backend/
├── main.py
├── config.py
├── instructions.py
├── input_processor.py
├── ai_engine.py
├── output_generator.py
├── gemini_engine.py
├── hashing.py
├── database.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md