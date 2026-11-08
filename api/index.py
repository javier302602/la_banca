"""Entrada serverless para Vercel: expone `app`."""
from app.main import app

__all__ = ["app"]
