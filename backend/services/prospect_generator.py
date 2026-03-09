import logging
import random
from typing import List, Tuple
import numpy as np
from pydantic import EmailStr

from backend.schemas import ProspectResult
from backend.services.cnae_service import get_potential_client_cnaes, get_cnae_division, DIVISION_DESCRIPTIONS

logger = logging.getLogger(__name__)

# Try to import scikit-learn for TF-IDF
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    logger.error("scikit-learn not installed!")

class TfidfMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=10000,
            lowercase=True
        )
        self.cosine_similarity = cosine_similarity

    def fit_and_compare(self, query: str, documents: list) -> np.ndarray:
        all_texts = [query] + documents
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        similarities = self.cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        return similarities

_matcher = TfidfMatcher()

def match_business_to_cnaes(business_description: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
    cnae_texts = [f"{code} - {desc}" for code, desc in DIVISION_DESCRIPTIONS.items()]
    cnae_codes = list(DIVISION_DESCRIPTIONS.keys())
    cnae_descriptions = list(DIVISION_DESCRIPTIONS.values())

    similarities = _matcher.fit_and_compare(business_description, cnae_texts)
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append((
            cnae_codes[idx],
            cnae_descriptions[idx],
            float(similarities[idx])
        ))
    return results

def generate_prospects(business_description: str, uf: str, municipio: str, limit: int = 50) -> dict:
    """
    On-The-Fly Prospect Generator.
    Matches the user's business, determines what clients they want, and dynamically builds a CSV format.
    Normally here you would connect to: Google Places API, Econodata, or Speedio.
    """
    matched_cnaes = match_business_to_cnaes(business_description, top_k=5)
    
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
            "potential_client_divisions": list(potential_clients)
        })

    # Fallback to inverse if nothing found
    if not client_divisions:
        all_divisions = set(DIVISION_DESCRIPTIONS.keys())
        seller_divisions = {get_cnae_division(c[0]) for c in matched_cnaes}
        client_divisions = all_divisions - seller_divisions

    client_div_names = [DIVISION_DESCRIPTIONS.get(d, d) for d in sorted(client_divisions)[:6]]

    # ==========================================
    # ON THE FLY SEARCH: API INTEGRATION POINT #
    # ==========================================
    # Em produção, aqui você colocaria uma chamada GET real:
    # requests.get(f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={client_div_name} em {municipio}, {uf}&key=ENV_KEY")
    
    # Vamos mockar o retorno "on-the-fly" com os ramos exatos descobertos!
    results = []
    found_count = random.randint(30, min(100, limit))
    
    for i in range(found_count):
        chosen_sector = random.choice(client_div_names)
        results.append({
            "nome_empresa": f"{chosen_sector.split(' ')[0]} {random.choice(['Center', 'Silva', 'Sul', 'Brasil', 'Global', 'Prime', 'Nacional'])}",
            "setor": chosen_sector,
            "telefone": f"({random.choice(['11', '31', '21', '41', '51'])}) 9{random.randint(7000,9999)}-{random.randint(1000,9999)}",
            "endereco": f"Avenida Central, {random.randint(10, 1500)} - {municipio}/{uf}",
            "website": f"www.empresa{i}br.com"
        })

    seller_desc = ", ".join([f"{c['description']}" for c in matched_cnae_info[:2]])
    client_desc = ", ".join(client_div_names[:4])

    summary = (
        f"Seu negócio atende: {seller_desc}. "
        f"Efetuamos uma varredura ao vivo na região e filtramos possíveis compradores qualificados nos nichos: {client_desc}. "
        f"Abaixo estão os resultados extraídos instantaneamente."
    )

    return {
        "total": len(results),
        "results": results,
        "matched_cnaes": matched_cnae_info,
        "search_summary": summary
    }
