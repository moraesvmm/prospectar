from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# --- Auth ---
class UserCreate(BaseModel):
    company_name: str
    email: str
    password: str
    business_sector: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    company_name: str
    email: str
    business_sector: Optional[str]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# --- Prospect Search ---
class ProspectSearch(BaseModel):
    business_sector: str
    uf: str
    municipio: str


class ProspectResult(BaseModel):
    cnpj_full: Optional[str]
    razao_social: Optional[str]
    nome_fantasia: Optional[str]
    cnae_fiscal: Optional[str]
    cnae_descricao: Optional[str]
    municipio_nome: Optional[str]
    uf: Optional[str]
    logradouro: Optional[str]
    numero: Optional[str]
    bairro: Optional[str]
    cep: Optional[str]
    telefone: Optional[str]
    email: Optional[str]
    relevance_score: Optional[float]

    class Config:
        from_attributes = True


class ProspectSearchResponse(BaseModel):
    total: int
    results: List[ProspectResult]
    matched_cnaes: List[dict]
    search_summary: str


# --- Data Import ---
class ImportRequest(BaseModel):
    uf: str
    file_count: Optional[int] = 10


class ImportStatusResponse(BaseModel):
    file_type: str
    file_index: int
    status: str
    progress: float
    records_imported: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class DataStatsResponse(BaseModel):
    total_companies: int
    total_cnaes: int
    total_municipalities: int
    states_imported: List[str]
