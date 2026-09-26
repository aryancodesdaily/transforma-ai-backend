# AI Content Transformation Platform - Backend

Backend service for the AI-powered content transformation platform developed for Smart India Hackathon 2026.

## Overview

This backend accepts source content such as text, documents, presentations and images, applies user-defined transformation parameters, uses AI to generate the requested communication artefact, and returns the generated output in the selected format.

## Architecture

Frontend
↓
FastAPI
↓
Input Processing (text / PDF / DOCX / PPTX / image)
↓
Unified Source Text
↓
Prompt Builder
↓
LLM (Groq)
↓
Generated Content
↓
Output Generator
↓
PDF / DOCX / PPTX / PNG

## Features

- Text-based content transformation
- PDF, DOCX and PPTX document processing
- Image content understanding (extracts text and visual context from uploaded images)
- Configurable target audience
- Configurable communication objective
- Configurable tone
- Configurable language
- Configurable detail level
- Configurable content style
- Multiple output types, including social media formats (LinkedIn, Twitter/X, Instagram)
- PDF, DOCX, PPTX and PNG output
- AI-powered content generation using Groq
- Image understanding using Gemini vision
- AI-generated visual output using Hugging Face image generation

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Groq API (GPT-OSS 120B)
- Google Gemini API (vision)
- Hugging Face Inference API (image generation)
- PyPDF
- python-docx
- python-pptx
- ReportLab
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
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```