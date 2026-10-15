import asyncio
import os
import time

import joblib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers import config, scenarios, users, transactions
from app import cache
from app.db import init_db, warm_pool
from app.service.risk import reload_forever
from contextlib import asynccontextmanager
from app.logger import get_logger

logger = get_logger(__name__)


model = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    init_db()
    warm_pool()
    model_path = "model/fraud_model.pkl"
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        logger.info("Loaded trained model successfully")

    else:
        logger.warning("Model not loaded: %s missing", model_path)
    reloader = asyncio.create_task(reload_forever())
    yield
    reloader.cancel()
    await cache.redis.aclose()

app = FastAPI(title="sentinelPay API", version="1.0", lifespan=lifespan)
# app = FastAPI()

@app.middleware("http")
async def log_ms(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    logger.info("%s %s %d %.2fms", request.method, request.url.path, response.status_code,
                (time.perf_counter() - start) * 1000)
    return response


@app.get("/")
async def root():
    return {"message": "Sentinal is here"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(NotImplementedError)
async def not_implemented(_: Request, __: NotImplementedError):
    return JSONResponse({"detail": "not implemented yet"}, status_code=501)


for rt in (users.router, scenarios.router, config.router, transactions.router):
    app.include_router(rt)