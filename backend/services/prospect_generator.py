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

    client_div_names = [DIVISION_DESCRIPTIONS.get(d, d) for d in sorted(client_divisions)[:3]]

    import urllib.request
    import urllib.parse
    import json
    from backend.config import SERPAPI_KEY

    results = []
    
    # Fazemos chamadas para os 3 principais ramos alvo na região
    for sector in client_div_names:
        if len(results) >= limit:
            break
            
        try:
            # Geramos o gatilho de venda cruzando o que o usuario faz com o que esta empresa alvo faz
            # Para evitar estourar limites de LLM, fazemos isso logicamente.
            seller_product = business_description.split()[0:5]
            seller_product_short = " ".join(seller_product)
            motivo_venda = f"Empresas do setor de {sector} costumam demandar '{seller_product_short}...' como insumo operacional, serviço de apoio estratégico ou infraestrutura do negócio."

            query = f"{sector} em {municipio}, {uf}"
            encoded_query = urllib.parse.quote(query)
            # engine=google_maps or engine=google (local)
            url = f"https://serpapi.com/search.json?engine=google_maps&q={encoded_query}&type=search&api_key={SERPAPI_KEY}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.getcode() == 200:
                    data = json.loads(response.read())
                    local_results = data.get("local_results", [])
                    
                    for place in local_results:
                        if len(results) >= limit:
                            break
                        
                        site = place.get("website", "")
                        if not site:
                            site = "Não disponível"
                            
                        # Limpa categorias esquisitas em inglês do Google pra pt-BR do buscador
                        tipo_lugar = place.get("type", sector)
                        if tipo_lugar and isinstance(tipo_lugar, str):
                            tipo_lugar = tipo_lugar.replace("company", "Empresa").replace("Manufacturer", "Indústria").replace("Store", "Loja")
                            
                        results.append({
                            "nome_empresa": place.get("title", ""),
                            "setor": tipo_lugar,
                            "telefone": place.get("phone", "Não disponível"),
                            "endereco": place.get("address", f"{municipio}, {uf}"),
                            "website": site,
                            "motivo_venda": motivo_venda
                        })
        except Exception as e:
            logger.error(f"Erro ao buscar no SerpApi para {sector}: {e}")

    seller_desc = ", ".join([f"{c['description']}" for c in matched_cnae_info[:2]])
    client_desc = ", ".join(client_div_names)

    summary = (
        f"Seu negócio atende: {seller_desc}. "
        f"Efetuamos uma varredura ao vivo na região usando Inteligência Artificial e o Radar de empresas. "
        f"Focamos nos nichos ideais: {client_desc}."
    )

    return {
        "total": len(results),
        "results": results,
        "matched_cnaes": matched_cnae_info,
        "search_summary": summary
    }
