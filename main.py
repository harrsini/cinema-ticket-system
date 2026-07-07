"""
main.py — FastAPI backend for CineBot
--------------------------------------
Run with:  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from bson import ObjectId

from tools.cinema_tool import cinema_tool

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def sanitize_response(obj):
    """
    Recursively converts MongoDB ObjectId to string so FastAPI can serialize.
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: sanitize_response(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_response(item) for item in obj]
    return obj

# --------------------------------------------------
# App
# --------------------------------------------------

app = FastAPI(title="CineBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Schemas
# --------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
def root():
    return {"status": "CineBot API is running"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    """
    Single entry point — accepts user message, returns structured response.
    Response types:
      text | theatre_selection | show_selection |
      seat_selection | awaiting_email | booking_confirmed
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = cinema_tool(req.message)
    return sanitize_response(result)


@app.get("/api/ticket/{filename}")
def download_ticket(filename: str):
    """
    Serves the generated PDF ticket for download.
    filename: just the file name, e.g. '6a46478d80c8ba8b90eef121.pdf'
    """
    import os
    # Tickets are saved by generate_ticket.py into ticket/tickets/
    ticket_dir = os.path.join(os.path.dirname(__file__), "ticket", "tickets")
    filepath   = os.path.normpath(os.path.join(ticket_dir, filename))

    # Guard against path traversal
    if not filepath.startswith(os.path.normpath(ticket_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")

    print(f"[download_ticket] looking for: {filepath}")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Ticket not found: {filename}")

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=filename,
    )
