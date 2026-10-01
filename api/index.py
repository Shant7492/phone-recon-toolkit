import sys
from pathlib import Path

# Root aur numscope directory ko Python path me inject karna
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "numscope"))

from numscope.web.app import app
