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
    # ==========================
    # Nova Inteligência (NLP Básico + Heurística)
    # Substitui a velha TF-IDF cega por análise do funil B2B.
    # ==========================
    desc_lower = business_description.lower().strip()
    
    # Remove acentuações simples se quiser, mas SerpApi/Google é resiliente.
    target_focus = ""
    
    # 1. Extração estruturada (Ex: "peças PARA maquinários")
    if " para " in desc_lower:
        target_focus = desc_lower.split(" para ", 1)[1].strip()
    elif " voltado a " in desc_lower:
        target_focus = desc_lower.split(" voltado a ", 1)[1].strip()
    elif " focado em " in desc_lower:
        target_focus = desc_lower.split(" focado em ", 1)[1].strip()

    # Filtra palavras inúteis do alvo final
    for word in [' de ', ' em ', ' com ', ' a ', ' o ', ' as ', ' os ']:
        if target_focus:
            target_focus = target_focus.replace(word, ' ')
    
    client_div_names = []
    
    if target_focus:
        # O usuário supre uma necessidade do "target" (Ex: maquinários). Seus clientes constroem, mantêm ou utilizam esse alvo.
        words = target_focus.split()[:4] # Pegamos apenas as palavras centrais para não confundir o Google
        core_product = " ".join(words)
        
        client_div_names = [
            f"Fabricante de {core_product}",
            f"Fábricas de {core_product}",
            f"Indústria de {core_product}",
            f"Montadora de {core_product}",
            f"Manutenção de {core_product}"
        ]
    else:
        # Se a pessoa só colocou "Fabricante de Plástico" ou "Distribuidora de Alimentos"
        for word in [' de ', ' em ', ' com ', ' a ', ' o ', ' as ', ' os ']:
            desc_lower = desc_lower.replace(word, ' ')
            
        words = desc_lower.split()
        product_keywords = [w for w in words if w not in ['distribuidora', 'distribuidor', 'fabricante', 'fábrica', 'fabrica', 'serviço', 'manutenção', 'consultoria', 'venda', 'vendedor', 'atacado', 'varejo', 'loja', 'comércio', 'agência', 'agencia']]
        core_product = " ".join(product_keywords[:3]) if product_keywords else business_description
        
        # Regras de Funil B2B Inverso:
        if "distribuidor" in desc_lower or "atacado" in desc_lower:
            client_div_names = [
                f"Lojas de {core_product}",
                f"Comércio de {core_product}",
                f"Manutenção de {core_product}",
                f"Fábricas de {core_product}",
                f"Indústrias de {core_product}"
            ]
        elif "fabricante" in desc_lower or "fábrica" in desc_lower or "fabrica" in desc_lower or "indústria" in desc_lower:
            client_div_names = [
                f"Distribuidores de {core_product}",
                f"Comércio atacadista de {core_product}",
                f"Revendas de {core_product}",
                f"Lojas de {core_product}"
            ]
        elif "manutenção" in desc_lower or "serviço" in desc_lower or "consultoria" in desc_lower:
            client_div_names = [
                f"Empresas de {core_product}",
                f"Indústrias de {core_product}",
                f"Escritórios de {core_product}"
            ]
        else:
            client_div_names = [
                f"Empresas de {core_product}",
                f"Fábricas de {core_product}",
                f"Lojas de {core_product}",
                f"Comércio de {core_product}"
            ]
        
    # Limita para as 3 melhores queries (garantindo diversidade)
    client_div_names = list(dict.fromkeys(client_div_names))[:3]
    matched_cnae_info = [{"description": core_product, "score": 0.99}]

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
            motivo_venda = f"Perfil ideal B2B porque atua como '{sector}', podendo demandar '{core_product}' para sua linha de produção, serviço ou revenda."

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

    client_desc = ", ".join(client_div_names)

    summary = (
        f"Alvo principal da sua pesquisa: {core_product}. "
        f"Efetuamos uma varredura cruzada usando Inteligência Semântica B2B focando nos nichos-alvo diretos: {client_desc}."
    )

    return {
        "total": len(results),
        "results": results,
        "matched_cnaes": matched_cnae_info,
        "search_summary": summary
    }
