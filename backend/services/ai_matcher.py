"""
AI Matcher Service - Uses semantic matching to find potential clients.
Supports two backends:
  1. Sentence Transformers (when PyTorch is available, e.g. in Docker)
  2. TF-IDF fallback (lightweight, works everywhere)
"""
import logging
from typing import List, Tuple
import numpy as np
from sqlalchemy.orm import Session
from backend.models import Cnae, Company
from backend.services.cnae_service import (
    get_potential_client_cnaes,
    get_cnae_division,
    DIVISION_DESCRIPTIONS,
)

logger = logging.getLogger(__name__)

# Try to import sentence-transformers, fall back to sklearn TF-IDF
_model = None
_use_transformers = False

try:
    from sentence_transformers import SentenceTransformer
    _use_transformers = True
    logger.info("Sentence Transformers disponível — usando modelo de IA avançado")
except ImportError:
    logger.info("Sentence Transformers não disponível — usando TF-IDF como fallback")


class TfidfMatcher:
    """Lightweight TF-IDF based matcher for when PyTorch is not available."""

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=10000,
            lowercase=True
        )
        self.cosine_similarity = cosine_similarity
        self._fitted = False
        self._matrix = None

    def fit_and_compare(self, query: str, documents: list) -> np.ndarray:
        all_texts = [query] + documents
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        similarities = self.cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        return similarities


_tfidf_matcher = None


def get_matcher():
    global _model, _tfidf_matcher
    if _use_transformers:
        if _model is None:
            from backend.config import SENTENCE_MODEL_NAME
            logger.info(f"Carregando modelo de IA: {SENTENCE_MODEL_NAME}...")
            _model = SentenceTransformer(SENTENCE_MODEL_NAME)
            logger.info("Modelo carregado com sucesso!")
        return _model
    else:
        if _tfidf_matcher is None:
            _tfidf_matcher = TfidfMatcher()
        return _tfidf_matcher


def compute_similarities(query: str, documents: list) -> np.ndarray:
    """Compute similarity scores between query and documents."""
    matcher = get_matcher()
    if _use_transformers:
        query_emb = matcher.encode([query])
        doc_embs = matcher.encode(documents)
        return np.dot(query_emb, doc_embs.T)[0]
    else:
        return matcher.fit_and_compare(query, documents)


def match_business_to_cnaes(
    business_description: str,
    db: Session,
    top_k: int = 10
) -> List[Tuple[str, str, float]]:
    """
    Match a business description to the most relevant CNAE codes.
    Returns list of (cnae_code, cnae_description, similarity_score).
    """
    cnaes = db.query(Cnae).all()
    if not cnaes:
        logger.warning("Nenhum CNAE no banco — usando divisões padrão.")
        cnae_texts = [f"{code} - {desc}" for code, desc in DIVISION_DESCRIPTIONS.items()]
        cnae_codes = list(DIVISION_DESCRIPTIONS.keys())
        cnae_descriptions = list(DIVISION_DESCRIPTIONS.values())
    else:
        cnae_texts = [f"{c.codigo} - {c.descricao}" for c in cnaes]
        cnae_codes = [c.codigo for c in cnaes]
        cnae_descriptions = [c.descricao for c in cnaes]

    similarities = compute_similarities(business_description, cnae_texts)

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append((
            cnae_codes[idx],
            cnae_descriptions[idx],
            float(similarities[idx])
        ))

    return results


def find_prospects(
    business_description: str,
    uf: str,
    municipio: str,
    db: Session,
    limit: int = 100
) -> dict:
    """
    Main prospecting function:
    1. Match business description to CNAEs (identify what the user sells)
    2. Find client CNAEs (who would buy from them)
    3. Query companies with those CNAEs in the target region
    """
    matched_cnaes = match_business_to_cnaes(business_description, db, top_k=5)

    client_divisions = set()
    matched_cnae_info = []

    for cnae_code, cnae_desc, score in matched_cnaes:
        division = get_cnae_division(cnae_code)
        potential_clients = get_potential_client_cnaes(division)
        client_divisions.update(potential_clients)

        matched_cnae_info.append({
            "code": cnae_code,
            "description": cnae_desc,
            "score": round(score, 4),
            "potential_client_divisions": potential_clients
        })

    if not client_divisions:
        all_divisions = set(DIVISION_DESCRIPTIONS.keys())
        seller_divisions = {get_cnae_division(c[0]) for c in matched_cnaes}
        client_divisions = all_divisions - seller_divisions

    query = db.query(Company).filter(
        Company.uf == uf.upper(),
        Company.situacao_cadastral == "02"
    )

    if municipio:
        query = query.filter(Company.municipio_nome.ilike(f"%{municipio}%"))

    cnae_filters = [Company.cnae_fiscal.like(f"{div}%") for div in client_divisions]
    if cnae_filters:
        from sqlalchemy import or_
        query = query.filter(or_(*cnae_filters))

    companies = query.limit(limit).all()

    # Score results by relevance
    if companies:
        company_texts = [
            f"{c.cnae_descricao or ''} {c.razao_social or ''}" for c in companies
        ]
        scores = compute_similarities(business_description, company_texts)
        scored_companies = list(zip(companies, scores))
        scored_companies.sort(key=lambda x: x[1], reverse=True)
    else:
        scored_companies = []

    results = []
    for company, score in scored_companies:
        telefone = ""
        if company.ddd_1 and company.telefone_1:
            telefone = f"({company.ddd_1}) {company.telefone_1}"

        results.append({
            "cnpj_full": company.cnpj_full,
            "razao_social": company.razao_social,
            "nome_fantasia": company.nome_fantasia,
            "cnae_fiscal": company.cnae_fiscal,
            "cnae_descricao": company.cnae_descricao,
            "municipio_nome": company.municipio_nome,
            "uf": company.uf,
            "logradouro": company.logradouro,
            "numero": company.numero,
            "bairro": company.bairro,
            "cep": company.cep,
            "telefone": telefone,
            "email": company.email,
            "relevance_score": round(float(score), 4)
        })

    seller_desc = ", ".join([f"{c['description']} ({c['score']:.0%})" for c in matched_cnae_info[:3]])
    client_div_names = [DIVISION_DESCRIPTIONS.get(d, d) for d in sorted(client_divisions)[:5]]
    client_desc = ", ".join(client_div_names)

    summary = (
        f"Seu ramo foi identificado como: {seller_desc}. "
        f"Possíveis clientes nos setores: {client_desc}. "
        f"Encontradas {len(results)} empresas na região."
    )

    return {
        "total": len(results),
        "results": results,
        "matched_cnaes": matched_cnae_info,
        "search_summary": summary
    }
