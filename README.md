🍳 The Digital Cookbook: An AI-Powered Recipe Manager
![alt text](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![alt text](https://img.shields.io/badge/FastAPI-0.110-darkgreen?logo=fastapi)
![alt text](https://img.shields.io/badge/SQLAlchemy-2.0-blue?logo=sqlalchemy)
![alt text](https://img.shields.io/badge/HTMX-1.9-blue)
![alt text](https://img.shields.io/badge/License-MIT-green)
The Digital Cookbook is a modern, full-stack web application designed to transform spoken or transcribed recipes into a structured, editable, and queryable digital format. The application leverages a powerful backend built with FastAPI, SQLAlchemy 2.0 (async), and Google Gemini Pro, with a dynamic, server-rendered frontend powered by Jinja2 and HTMX.
The core feature is its ability to process real-time audio streams from a user's microphone, transcribe them, and use an LLM to automatically structure the unstructured text into a complete, editable recipe card.
Core Features
Real-Time Audio Transcription: Utilizes WebSockets and the Google Cloud Speech-to-Text API for live, streaming transcription directly in the browser.
AI-Powered Recipe Parsing: Employs Google's Gemini 1.5 Pro model to analyze transcribed text and intelligently extract key recipe components (name, ingredients, quantities, units, chef's notes) into a structured JSON format.
Asynchronous CRUD Operations: A fully asynchronous API built with FastAPI and SQLAlchemy 2.0 for creating, reading, updating, and deleting recipes without blocking.
Dynamic, Server-Rendered UI: The frontend uses HTMX to provide a rich, single-page-application feel without writing complex JavaScript. All UI updates are handled by swapping HTML partials rendered on the server.
Full Recipe Management: A "Cookbook" view allows users to browse all saved recipes, edit them in place, or delete them.
Ingredient Aggregation: A dedicated "Pantry" or "Ingredients" page that queries all saved recipes, aggregates the total quantity of each ingredient by unit, and provides a comprehensive shopping list.
Persistent Storage: Uses a robust database backend (configurable for SQLite or PostgreSQL) with Alembic for handling schema migrations.
Tech Stack & Key Libraries
Category	Technologies & Libraries
Backend Framework	FastAPI
Database & ORM	SQLAlchemy 2.0 (with asyncio), Alembic (for migrations)
AI & NLP	Google Gemini 1.5 Pro, Google Cloud Speech-to-Text
Frontend	Jinja2 (Templating), HTMX (Dynamic UI)
Data Validation	Pydantic
WebSockets	FastAPI WebSockets
Environment Mgmt	python-dotenv
System Architecture
The application is architected around a modern, asynchronous Python stack:
Database (database.py, models.py): Defines the database connection (async_engine), session management (AsyncSessionLocal), and the SQLAlchemy ORM models (Recipe, Transcript). It's configured to be easily switchable between async SQLite for development and async PostgreSQL for production.
Data Schemas (schemas.py): Uses Pydantic to define the strict data shapes for API requests and responses, ensuring robust data validation and clear API documentation.
The FastAPI Core (main.py):
WebSocket Endpoint (/ws/transcribe_streaming): Manages the real-time connection with the browser, streaming audio data to the Google Speech API and sending transcriptions back to the user.
AI Workflow Endpoints: A series of HTMX-driven endpoints handle the process of taking raw text, saving it as a Transcript, sending it to the Gemini API for parsing, and saving the final structured data as a Recipe.
CRUD Endpoints: A full suite of RESTful endpoints (/recipes, /recipes/{id}) for managing recipes, all designed to return HTML partials for HTMX to swap into the DOM.
Templates (/templates): A collection of Jinja2 templates. This includes the main index.html shell and a partials directory containing the modular HTML snippets that HTMX uses to dynamically update the page.
