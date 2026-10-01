import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.analyzer import analyze_phone
import os

app = FastAPI(title="numscope API")

# Mount static files for HTML/CSS/JS
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class LookupRequest(BaseModel):
    number: str
    region: str = "IN"

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/lookup")
async def lookup(request: LookupRequest):
    try:
        result = analyze_phone(request.number, request.region)
        if not result.get("valid"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid number"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
