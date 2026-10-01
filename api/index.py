import sys
from pathlib import Path
from fastapi import Request

# Root aur numscope directory add karna
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "numscope"))

from numscope.web.app import app

# Vercel rewrite ke path mismatch ko handle karne ke liye route aliases
@app.get("/api/index.py")
@app.get("/api")
async def vercel_root_handler(request: Request):
    from starlette.responses import FileResponse
    import os
    static_file = ROOT_DIR / "numscope" / "web" / "static" / "index.html"
    return FileResponse(str(static_file))
  
