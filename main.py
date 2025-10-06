# FILE: main.py (Definitive, Corrected & Cleaned Version)

# --- Standard Library Imports ---
import os
import json
import re
import asyncio
from typing import List, Optional

# --- Third-Party Imports ---
from dotenv import load_dotenv
from fastapi import (
    FastAPI, Request, Depends, WebSocket,
    WebSocketDisconnect, HTTPException, Form, Response 
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState
import google.generativeai as genai
from google.cloud import speech

# --- Local Application Imports ---
import database as db_config
import models
from collections import Counter
# FILE: main.py (The Corrected "INITIAL APP SETUP" Section)

from contextlib import asynccontextmanager
from database import engine, Base
import models # Ensure models is imported so Base knows about your tables
from collections import defaultdict
# ... other imports from the top of your file ...

# ==============================================================================
# 1. INITIAL APP SETUP
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup, create all database tables if they don't exist.
    """
    print("--- [STARTUP] Application starting up... ---")
    async with engine.begin() as conn:
        # This line creates the tables from models linked to Base
        await conn.run_sync(Base.metadata.create_all)
    print("--- [STARTUP] Database tables checked/created. ---")
    yield
    print("--- [SHUTDOWN] Application shutting down... ---")

# --- App Instantiation and Configuration ---

# This is the single, definitive creation of the FastAPI app object.
# It MUST come AFTER the lifespan function is defined.
app = FastAPI(lifespan=lifespan)

# Now, configure the app object that was just created.
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load environment variables and configure services.
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("FATAL ERROR: GOOGLE_API_KEY environment variable not found.")
try:
    genai.configure(api_key=google_api_key)
    print("--- [STARTUP] Gemini AI configured successfully. ---")
except Exception as e:
    raise ValueError(f"FATAL ERROR: Failed to configure Gemini AI: {e}")

# ==============================================================================
# 2. HELPER FUNCTIONS & DEPENDENCIES
# (The rest of your file from here on is correct)
# ==============================================================================
# ==============================================================================
# 2. HELPER FUNCTIONS & DEPENDENCIES
# ==============================================================================

async def get_db() -> AsyncSession:
    """Provides a database session for each request."""
    async with db_config.AsyncSessionLocal() as session:
        yield session

def parse_llm_json_output(raw_string: str) -> dict | None:
    """Cleans and parses a JSON string from an LLM response."""
    if not raw_string:
        return None
    match = re.search(r"```(json)?\s*({.*})\s*```", raw_string, re.DOTALL)
    json_string = match.group(2) if match else raw_string
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"--- [JSON_PARSE_ERROR] Failed to decode JSON. Error: {e}")
        return None

async def call_llm_for_json(prompt: str) -> str | None:
    """Analyzes a transcript and returns a structured JSON recipe."""
    print(f"\n--- [LLM_SERVICE] Calling Gemini AI to parse: '{prompt[:100]}...'")
    system_instruction = """
    You are an expert kitchen assistant. Your task is to analyze a chef's transcribed dictation and structure it into a specific JSON format.
    Your entire response MUST be a single, valid JSON object and nothing else.
    Populate the following fields: "recipe_name", "provenance", "chef_notes" (a list of strings), and "items" (a list of objects with "itemName", "quantity", and "unit").
    If any detail is missing, use a reasonable default like null for strings or an empty list [].
    """
    model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=system_instruction)
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json", temperature=0.1)
    try:
        response = await model.generate_content_async(prompt, generation_config=generation_config)
        print("---               AI response received successfully.")
        return response.text
    except Exception as e:
        print(f"--- [LLM_SERVICE] FATAL ERROR: {e} ---")
        return None

# ==============================================================================
# 3. WEBSOCKET ENDPOINT FOR REAL-TIME TRANSCRIPTION
# ==============================================================================

@app.websocket("/ws/transcribe_streaming")
async def websocket_streaming_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = speech.SpeechAsyncClient()
    
    async def audio_request_generator(ws: WebSocket):
        config = speech.RecognitionConfig(encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS, sample_rate_hertz=48000, language_code="en-US", enable_automatic_punctuation=True)
        streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=True)
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        try:
            while True:
                message = await ws.receive()
                if 'bytes' in message:
                    yield speech.StreamingRecognizeRequest(audio_content=message['bytes'])
        except WebSocketDisconnect:
            return

    try:
        streaming_responses = await client.streaming_recognize(requests=audio_request_generator(websocket))
        async for response in streaming_responses:
            if not response.results or not response.results[0].alternatives: continue
            result = response.results[0]
            await websocket.send_json({'is_final': result.is_final, 'transcript': result.alternatives[0].transcript})
    except Exception as e:
        print(f"--- [WEBSOCKET] Error during transcription: {e} ---")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()

# ==============================================================================
# 4. HTTP ENDPOINTS
# ==============================================================================

# --- Full Page Rendering Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serves the main index.html shell for recording."""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "initial_partial": None, "active_page": "home"}
    )
@app.get("/cookbook", response_class=HTMLResponse)
async def serve_cookbook_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Serves the dedicated, full-page view of the entire cookbook."""
    print("\n--- [UI] Serving full cookbook page ---")
    query = select(models.Recipe).order_by(models.Recipe.recipe_name)
    result = await db.execute(query)
    recipes = result.scalars().all()
    return templates.TemplateResponse(
        "cookbook.html", 
        {"request": request, "recipes": recipes, "active_page": "cookbook"}
    )
# --- Transcript & AI Workflow Endpoints ---

class TranscriptCreate(BaseModel):
    full_text: str

@app.post("/transcripts", response_class=HTMLResponse)
async def create_transcript_and_return_editor(request: Request, data: TranscriptCreate, db: AsyncSession = Depends(get_db)):
    """Receives raw text from JS, saves it, and returns the editor partial."""
    print("\n--- [PROCESS] Saving transcript and returning editor partial ---")
    new_transcript = models.Transcript(full_text=data.full_text, status="pending")
    db.add(new_transcript)
    await db.commit()
    await db.refresh(new_transcript)
    return templates.TemplateResponse("partials/transcript_editor.html", {"request": request, "transcript": new_transcript})

@app.post("/transcripts/{transcript_id}/generate-recipe", response_class=HTMLResponse)
async def generate_recipe_from_transcript(request: Request, transcript_id: int, transcript_text: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Takes edited text, calls AI, saves the Recipe, and returns the recipe card."""
    print(f"\n--- [PROCESS] Generating recipe from Transcript ID: {transcript_id} ---")
    result = await db.execute(select(models.Transcript).where(models.Transcript.id == transcript_id))
    transcript_obj = result.scalars().first()
    if not transcript_obj: raise HTTPException(status_code=404, detail="Transcript not found")
    
    transcript_obj.full_text = transcript_text
    raw_ai_output = await call_llm_for_json(transcript_text)
    if not raw_ai_output: raise HTTPException(status_code=500, detail="AI service failed to respond.")
    
    recipe_data = parse_llm_json_output(raw_ai_output)
    if not recipe_data: raise HTTPException(status_code=500, detail="AI returned an invalid recipe structure.")

    new_recipe = models.Recipe(
        recipe_name=recipe_data.get("recipe_name") or "Untitled Recipe",
        provenance=recipe_data.get("provenance") or None,
        items=recipe_data.get("items") or [],
        chef_notes=recipe_data.get("chef_notes") or [])
    
    db.add(new_recipe)
    transcript_obj.recipe = new_recipe
    transcript_obj.status = "processed"
    await db.commit()
    await db.refresh(new_recipe)
    print(f"---         Saved new Recipe ID: {new_recipe.id}, linked to Transcript {transcript_id}")
    
    context = {"request": request, "recipe": new_recipe, "is_new": False}
    if "HX-Request" in request.headers:
        return templates.TemplateResponse("partials/recipe_card.html", context)
    else:
        context["initial_partial"] = "partials/recipe_card.html"
        return templates.TemplateResponse("index.html", context)

# --- Recipe CRUD (Create, Read, Update) Endpoints ---

@app.post("/recipes", response_class=HTMLResponse)
async def create_recipe_from_form(request: Request, db: AsyncSession = Depends(get_db), recipe_name: str = Form(...), provenance: str = Form(""), item_quantity: List[str] = Form(...), item_unit: List[str] = Form(...), item_name: List[str] = Form(...), chef_note: Optional[List[str]] = Form(None)):
    """Handles creating a new recipe from the form and returns the cookbook list."""
    print("\n--- [DB] Creating new recipe from form ---")
    items_data = [{"quantity": qty, "unit": unit, "itemName": name} for qty, unit, name in zip(item_quantity, item_unit, item_name) if name]
    new_recipe = models.Recipe(recipe_name=recipe_name, provenance=provenance, items=items_data, chef_notes=chef_note or [])
    db.add(new_recipe)
    await db.commit()
    
    query = select(models.Recipe).order_by(models.Recipe.recipe_name)
    result = await db.execute(query)
    recipes = result.scalars().all()
    return templates.TemplateResponse("partials/cookbook_list.html", {"request": request, "recipes": recipes})

@app.get("/recipes/{recipe_id}", response_class=HTMLResponse)
async def get_recipe_editor(request: Request, recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches a single recipe and returns the recipe_card.html editor partial."""
    print(f"\n--- [DB] Fetching recipe {recipe_id} for editing ---")
    result = await db.execute(select(models.Recipe).where(models.Recipe.id == recipe_id))
    recipe = result.scalars().first()
    if not recipe: raise HTTPException(status_code=404, detail="Recipe not found")
    return templates.TemplateResponse("partials/recipe_card.html", {"request": request, "recipe": recipe, "is_new": False})

@app.api_route("/recipes/{recipe_id}", methods=["PUT", "POST"], response_class=HTMLResponse)
async def update_recipe_and_return_cookbook(request: Request, recipe_id: int, db: AsyncSession = Depends(get_db), recipe_name: str = Form(...), provenance: str = Form(""), item_quantity: List[str] = Form(...), item_unit: List[str] = Form(...), item_name: List[str] = Form(...), chef_note: Optional[List[str]] = Form(None)):
    """Handles updating an existing recipe and returns the updated cookbook list."""
    print(f"\n--- [DB] Updating Recipe ID: {recipe_id} ---")
    result = await db.execute(select(models.Recipe).where(models.Recipe.id == recipe_id))
    db_recipe = result.scalars().first()
    if not db_recipe: raise HTTPException(status_code=404, detail="Recipe not found")

    db_recipe.recipe_name = recipe_name
    db_recipe.provenance = provenance
    db_recipe.items = [{"quantity": qty, "unit": unit, "itemName": name} for qty, unit, name in zip(item_quantity, item_unit, item_name) if name]
    db_recipe.chef_notes = chef_note or []
    await db.commit()
    
    query = select(models.Recipe).order_by(models.Recipe.recipe_name)
    result = await db.execute(query)
    recipes = result.scalars().all()
    return templates.TemplateResponse("partials/cookbook_list.html", {"request": request, "recipes": recipes})



@app.delete("/recipes/{recipe_id}")
async def delete_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Finds a recipe by its ID and deletes it from the database.
    Returns an empty response on success, which HTMX uses to remove the element.
    """
    print(f"\n--- [DB] Deleting Recipe ID: {recipe_id} ---")
    
    # Step 1: Find the recipe object in the database.
    result = await db.execute(select(models.Recipe).where(models.Recipe.id == recipe_id))
    recipe_to_delete = result.scalars().first()
    
    # Step 2: If the recipe doesn't exist, return a 404 error.
    if not recipe_to_delete:
        print(f"---      Error: Recipe {recipe_id} not found.")
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    # Step 3: If found, delete it and commit the change.
    await db.delete(recipe_to_delete)
    await db.commit()
    print(f"---      Recipe {recipe_id} deleted successfully.")
    
    # Step 4: Return an empty 200 OK response.
    # HTMX will use this to replace the `<li>`, effectively removing it from the page.
    return Response(status_code=200, content="")
# Create this new helper function just above your endpoint
def parse_quantity(quantity_str: str) -> float | None:
    """
    Parses a quantity string (e.g., "2", "1/2", "1.5") into a float.
    Returns None if parsing fails.
    """
    if not quantity_str:
        return None
    try:
        # Handle simple numbers like "2" or "1.5"
        return float(quantity_str)
    except (ValueError, TypeError):
        # Handle fractions like "1/2"
        if isinstance(quantity_str, str) and "/" in quantity_str:
            try:
                num, den = quantity_str.split("/")
                return float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                return None
    return None

# Now, replace your existing /ingredients endpoint with this
@app.get("/ingredients", response_class=HTMLResponse)
async def serve_ingredients_page(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Fetches all recipes, aggregates the QUANTITIES of every ingredient by unit,
    and serves a dedicated page showing the totals.
    """
    print("\n--- [PROCESS] Aggregating all ingredient quantities ---")
    
    query = select(models.Recipe)
    result = await db.execute(query)
    all_recipes = result.scalars().all()
    
    # Use a defaultdict for convenient aggregation.
    # Structure: { "flour": { "cup": 10.5, "gram": 500 }, "sugar": { "cup": 2 } }
    aggregated_ingredients = defaultdict(lambda: defaultdict(float))

    for recipe in all_recipes:
        for item in recipe.items:
            name = item.get('itemName')
            quantity = item.get('quantity')
            # Default to 'count' if unit is missing or empty, normalize to lowercase.
            unit = (item.get('unit') or 'count').strip().lower()
            
            if name and quantity:
                # Parse the string quantity into a number
                numeric_quantity = parse_quantity(str(quantity))
                
                if numeric_quantity is not None:
                    # Normalize the name and add to the total for that specific unit
                    normalized_name = name.strip().lower()
                    aggregated_ingredients[normalized_name][unit] += numeric_quantity

    # Convert to a regular dict and sort alphabetically for display
    sorted_ingredients = sorted(aggregated_ingredients.items())
    print(f"---           Aggregated {len(sorted_ingredients)} unique ingredients.")
    
    return templates.TemplateResponse(
        "ingredients.html", 
        {"request": request, "ingredients": sorted_ingredients, "active_page": "ingredients"}
    )