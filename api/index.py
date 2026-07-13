import os
import sys
from pathlib import Path

# Add project root to sys.path so 'backend' can be found
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from backend.main import app  # noqa: E402 - FastAPI ASGI app

# Vercel expects a variable named `app` (ASGI handler)
