#!/usr/bin/env python3
"""Script simple para arrancar el backend de AuraFit AI."""
import uvicorn
from app.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
