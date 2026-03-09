import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db
from backend.routers import auth_router, prospects_router, data_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="ProspectaBR",
    description="Sistema de prospecção B2B com dados reais da Receita Federal",
    version="1.0.0"
)

# Routers
app.include_router(auth_router.router)
app.include_router(prospects_router.router)
app.include_router(data_router.router)

# Static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
async def startup():
    init_db()
    logging.info("ProspectaBR iniciado com sucesso!")


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "app": "ProspectaBR"}
