from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db, seed_demo_rfx_if_missing, seed_vendors_if_empty
from app.routers import health, rfx

app = FastAPI(title="Agentic RFx API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(rfx.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_vendors_if_empty()
    seed_demo_rfx_if_missing()
