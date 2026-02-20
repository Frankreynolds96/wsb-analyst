"""Vercel serverless entry point — mounts the FastAPI app."""

import sys
import os

# Add the project root to Python path so backend imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
