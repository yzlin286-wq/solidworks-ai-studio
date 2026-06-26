from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sw_ai_backend.api.routes import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SolidWorks AI Studio API",
        version="0.1.0",
        description="Localhost-only API for SolidWorks automation, AI planning, skill indexing, execution, and MCP management.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()


def main() -> None:
    host = os.environ.get("SWAI_API_HOST", "127.0.0.1")
    port = int(os.environ.get("SWAI_API_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
