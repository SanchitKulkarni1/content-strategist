from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dependencies import get_pipeline_graph
from api.routes.health import router as health_router
from api.routes.strategy import router as strategy_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm pipeline graph at startup to reduce first-request latency.
    get_pipeline_graph()
    yield


app = FastAPI(title="Content Strategy API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTPException", "detail": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": exc.__class__.__name__, "detail": str(exc)},
    )


app.include_router(health_router)
app.include_router(strategy_router)
