import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import ImportStatus
from backend.schemas import ImportRequest, ImportStatusResponse, DataStatsResponse
from backend.services.data_importer import import_data_for_state, get_import_stats
from backend.config import ESTADOS_BRASIL

router = APIRouter(prefix="/api/data", tags=["Data Import"])

_import_tasks = {}


@router.post("/import")
async def start_import(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start data import for a specific state."""
    uf = request.uf.upper()
    if uf not in ESTADOS_BRASIL:
        raise HTTPException(status_code=400, detail="Estado inválido")

    if uf in _import_tasks and not _import_tasks[uf].done():
        raise HTTPException(status_code=409, detail=f"Importação de {uf} já em andamento")

    loop = asyncio.get_event_loop()
    task = loop.create_task(import_data_for_state(uf, request.file_count or 10))
    _import_tasks[uf] = task

    return {
        "message": f"Importação de dados de {ESTADOS_BRASIL[uf]} iniciada",
        "uf": uf,
        "state_name": ESTADOS_BRASIL[uf]
    }


@router.get("/import/status")
def get_import_status(db: Session = Depends(get_db)):
    """Get status of all imports."""
    statuses = db.query(ImportStatus).order_by(ImportStatus.updated_at.desc()).limit(20).all()
    return [
        {
            "file_type": s.file_type,
            "file_index": s.file_index,
            "status": s.status,
            "progress": s.progress,
            "records_imported": s.records_imported,
            "error_message": s.error_message,
            "uf_filter": s.uf_filter
        }
        for s in statuses
    ]


@router.get("/stats", response_model=DataStatsResponse)
def get_data_stats(db: Session = Depends(get_db)):
    """Get current database statistics."""
    return get_import_stats(db)
