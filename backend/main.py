import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.routers import prospects_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="ProspectaBR",
    description="Sistema de prospecção com Geração on-the-fly de Leads B2B/B2C",
    version="2.0.0"
)

# Routers
app.include_router(prospects_router.router)

# Static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.on_event("startup")
async def startup():
    logging.info("ProspectaBR v2 iniciado com sucesso!")

@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/health")
async def health():
    return {"status": "ok", "app": "ProspectaBR"}
