from pydantic import BaseModel, EmailStr
from typing import Optional, List

class ProspectSearch(BaseModel):
    business_sector: str
    uf: str
    municipio: str
    email: str  # Email para envio do CSV

class ProspectResult(BaseModel):
    nome_empresa: Optional[str]
    setor: Optional[str]
    telefone: Optional[str]
    endereco: Optional[str]
    website: Optional[str]

class ProspectSearchResponse(BaseModel):
    message: str
    search_summary: str
    results_found: int
