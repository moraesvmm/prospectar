from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Company, Municipality
from backend.schemas import ProspectSearch, ProspectSearchResponse
from backend.auth import get_current_user
from backend.services.ai_matcher import find_prospects
from backend.config import ESTADOS_BRASIL

router = APIRouter(prefix="/api/prospects", tags=["Prospects"])


@router.post("/search", response_model=ProspectSearchResponse)
def search_prospects(
    search: ProspectSearch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for potential clients based on business sector and location."""
    if search.uf.upper() not in ESTADOS_BRASIL:
        raise HTTPException(status_code=400, detail="Estado inválido")

    result = find_prospects(
        business_description=search.business_sector,
        uf=search.uf,
        municipio=search.municipio,
        db=db
    )
    return result


@router.get("/states")
def get_states():
    """Get list of Brazilian states."""
    return [{"uf": k, "name": v} for k, v in sorted(ESTADOS_BRASIL.items(), key=lambda x: x[1])]


@router.get("/cities/{uf}")
def get_cities(uf: str, db: Session = Depends(get_db)):
    cities = db.query(Municipality.nome).filter(Municipality.nome.isnot(None)).distinct().order_by(Municipality.nome).all()
    
    # Se IBGE nao estiver baixado, retorna vazio para não quebrar a UI
    if not cities:
        # Fallback para as empresas importadas caso a tabela de municípios esteja vazia
        cities = (
            db.query(Company.municipio_nome)
            .filter(Company.uf == uf.upper(), Company.municipio_nome.isnot(None))
            .distinct()
            .order_by(Company.municipio_nome)
            .all()
        )
    return [{"name": city[0]} for city in cities if city[0]]
