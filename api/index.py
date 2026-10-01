import sys
from pathlib import Path
from starlette.responses import FileResponse

# Root aur package path inject karna
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "numscope"))

from numscope.web.app import app

STATIC_INDEX = ROOT_DIR / "numscope" / "web" / "static" / "index.html"

@app.get("/")
@app.get("/api/index.py")
@app.get("/api")
async def root():
    return FileResponse(str(STATIC_INDEX))
    
