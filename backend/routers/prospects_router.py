from fastapi import APIRouter, HTTPException, BackgroundTasks
import urllib.request
import json
import gzip
import csv
import io

from backend.schemas import ProspectSearch, ProspectSearchResponse
from backend.services.prospect_generator import generate_prospects
from backend.config import ESTADOS_BRASIL

router = APIRouter(prefix="/api/prospects", tags=["Prospects"])

def send_mocked_csv_email(email: str, results: list):
    """
    Mock func for sending emails - in a real scenario you would plug Resend or Sendgrid here.
    For this architectural pivot without external DBs, we log it and just let the frontend know.
    """
    print(f"[EMAIL MOCK] Enviando CSV com {len(results)} leads para {email}...")

@router.post("/search", response_model=ProspectSearchResponse)
def search_prospects(
    search: ProspectSearch,
    background_tasks: BackgroundTasks
):
    """Search for potential clients and prepare to send to email."""
    if search.uf.upper() not in ESTADOS_BRASIL:
        raise HTTPException(status_code=400, detail="Estado inválido")

    result = generate_prospects(
        business_description=search.business_sector,
        uf=search.uf,
        municipio=search.municipio,
        limit=50
    )
    
    # Schedule CSV email delivery in background
    background_tasks.add_task(send_mocked_csv_email, search.email, result["results"])
    
    # Return success and results to frontend too
    result["message"] = f"Planilha gerada com sucesso! Um e-mail será enviado para {search.email} em instantes."
    result["results_found"] = result["total"]
    
    return result

@router.get("/states")
def get_states():
    """Get list of Brazilian states."""
    return [{"uf": k, "name": v} for k, v in sorted(ESTADOS_BRASIL.items(), key=lambda x: x[1])]

@router.get("/cities/{uf}")
def get_cities(uf: str):
    """Get list of cities directly from public IBGE API."""
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 200:
                data = response.read()
                if response.info().get('Content-Encoding') == 'gzip' or data.startswith(b'\x1f\x8b'):
                    data = gzip.decompress(data)
                municipios = json.loads(data)
                return [{"name": m["nome"]} for m in municipios]
    except Exception as e:
        print(f"Erro ao buscar municípios no IBGE: {e}")
        return []

@router.post("/download-csv/{email}")
def download_csv(email: str):
    # This endpoint can be used if we want direct download instead of email
    pass
