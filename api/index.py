import os
import sys
from pathlib import Path

# Add project root to sys.path so 'backend' can be found
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from backend.main import app

# This is the entry point for Vercel
