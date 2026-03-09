"""
CNAE Service - Maps business relationships between CNAE codes.
Determines which CNAEs are potential clients for a given business sector.
"""

# CNAE Section mapping (first 2 digits indicate the section/division)
CNAE_SUPPLY_CHAIN = {
    # Manufacturing supplies to...
    "10": ["46", "47", "56"],  # Food manufacturing -> wholesale, retail, restaurants
    "11": ["46", "47", "56"],  # Beverages -> wholesale, retail, restaurants
    "13": ["14", "46", "47"],  # Textiles -> clothing, wholesale, retail
    "14": ["46", "47"],        # Clothing -> wholesale, retail
    "15": ["46", "47"],        # Leather/footwear -> wholesale, retail
    "16": ["41", "42", "43"],  # Wood -> construction
    "17": ["18", "46", "47", "58"],  # Paper -> printing, wholesale, retail, publishing
    "20": ["10", "11", "21", "22", "23", "24", "25", "41", "43", "46"],  # Chemicals -> many sectors
    "21": ["46", "47", "86"],  # Pharma -> wholesale, retail, healthcare
    "22": ["25", "28", "29", "30", "41", "43", "46"],  # Rubber/plastic -> metalwork, machinery, vehicles, construction
    "23": ["41", "42", "43", "46"],  # Non-metallic minerals -> construction, wholesale
    "24": ["25", "28", "29", "30", "41", "43"],  # Metallurgy -> metalwork, machinery, vehicles, construction
    "25": ["10", "11", "24", "28", "29", "30", "41", "42", "43", "46"],  # Metal products -> many sectors
    "26": ["27", "46", "47", "61", "62"],  # Electronics -> electrical, wholesale, retail, telecom, IT
    "27": ["26", "41", "43", "46", "47"],  # Electrical equipment -> electronics, construction
    "28": ["01", "02", "03", "10", "11", "20", "24", "25", "41", "42", "43"],  # Machinery -> agriculture, food, chemicals, construction
    "29": ["45", "46", "49", "77"],  # Vehicles -> vehicle trade, transport, rental
    "30": ["46", "49", "50", "51"],  # Other transport equip -> wholesale, transport
    "31": ["41", "43", "46", "47", "55"],  # Furniture -> construction, wholesale, retail, hospitality
    
    # Wholesale/distribution supplies to...
    "46": ["10", "11", "14", "20", "21", "22", "23", "24", "25", "26", "27", "28", "41", "43", "47", "55", "56"],
    
    # IT/Tech supplies to...
    "62": ["10", "11", "20", "24", "25", "28", "29", "46", "47", "49", "50", "51", "55", "56", "64", "65", "66", "69", "86"],
    "63": ["46", "47", "62", "64", "69", "73"],
    
    # Professional services supply to...
    "69": ["01", "10", "20", "24", "25", "28", "29", "41", "46", "47", "55", "62", "64", "86"],  # Legal/accounting
    "70": ["10", "20", "24", "28", "29", "41", "46", "47", "62", "64"],  # Management consulting
    "71": ["10", "20", "24", "28", "41", "42", "43"],  # Architecture/engineering
    "73": ["10", "11", "14", "20", "21", "29", "46", "47", "55", "56", "62", "64"],  # Advertising
    
    # Construction supplies to / needs from...
    "41": ["42", "43", "46", "68"],  # Building construction -> infrastructure, specialized, wholesale, real estate
    "42": ["41", "43", "46", "49"],  # Infrastructure -> building, specialized, wholesale, transport
    "43": ["41", "42", "46"],        # Specialized construction -> building, infrastructure, wholesale
}

# Reverse mapping: given a CNAE, who might be your supplier (and thus you are their client)
def get_potential_client_cnaes(cnae_division: str) -> list:
    """Given a CNAE division (2 digits), return divisions that could be clients."""
    clients = set()
    
    # Direct mapping: if we sell, these are our clients
    if cnae_division in CNAE_SUPPLY_CHAIN:
        clients.update(CNAE_SUPPLY_CHAIN[cnae_division])
    
    # Reverse mapping: who lists us as their client? They could also be our client
    for supplier, their_clients in CNAE_SUPPLY_CHAIN.items():
        if cnae_division in their_clients:
            clients.add(supplier)
    
    return sorted(list(clients))


def get_cnae_division(cnae_code: str) -> str:
    """Extract the division (first 2 digits) from a CNAE code."""
    return cnae_code[:2] if cnae_code else ""


DIVISION_DESCRIPTIONS = {
    "01": "Agricultura, pecuária e serviços relacionados",
    "02": "Produção florestal",
    "03": "Pesca e aquicultura",
    "05": "Extração de carvão mineral",
    "06": "Extração de petróleo e gás natural",
    "07": "Extração de minerais metálicos",
    "08": "Extração de minerais não-metálicos",
    "09": "Atividades de apoio à extração de minerais",
    "10": "Fabricação de produtos alimentícios",
    "11": "Fabricação de bebidas",
    "12": "Fabricação de produtos do fumo",
    "13": "Fabricação de produtos têxteis",
    "14": "Confecção de artigos do vestuário e acessórios",
    "15": "Preparação de couros e fabricação de artefatos de couro",
    "16": "Fabricação de produtos de madeira",
    "17": "Fabricação de celulose, papel e produtos de papel",
    "18": "Impressão e reprodução de gravações",
    "19": "Fabricação de coque, derivados do petróleo e biocombustíveis",
    "20": "Fabricação de produtos químicos",
    "21": "Fabricação de produtos farmoquímicos e farmacêuticos",
    "22": "Fabricação de produtos de borracha e de material plástico",
    "23": "Fabricação de produtos de minerais não-metálicos",
    "24": "Metalurgia",
    "25": "Fabricação de produtos de metal",
    "26": "Fabricação de equipamentos de informática e eletrônicos",
    "27": "Fabricação de máquinas, aparelhos e materiais elétricos",
    "28": "Fabricação de máquinas e equipamentos",
    "29": "Fabricação de veículos automotores",
    "30": "Fabricação de outros equipamentos de transporte",
    "31": "Fabricação de móveis",
    "32": "Fabricação de produtos diversos",
    "33": "Manutenção, reparação e instalação de máquinas e equipamentos",
    "35": "Eletricidade, gás e outras utilidades",
    "36": "Captação, tratamento e distribuição de água",
    "37": "Esgoto e atividades relacionadas",
    "38": "Coleta, tratamento e disposição de resíduos",
    "39": "Descontaminação e outros serviços de gestão de resíduos",
    "41": "Construção de edifícios",
    "42": "Obras de infraestrutura",
    "43": "Serviços especializados para construção",
    "45": "Comércio e reparação de veículos automotores e motocicletas",
    "46": "Comércio por atacado",
    "47": "Comércio varejista",
    "49": "Transporte terrestre",
    "50": "Transporte aquaviário",
    "51": "Transporte aéreo",
    "52": "Armazenamento e atividades auxiliares dos transportes",
    "53": "Correio e outras atividades de entrega",
    "55": "Alojamento",
    "56": "Alimentação",
    "58": "Edição e edição integrada à impressão",
    "59": "Atividades cinematográficas, produção de vídeos e de programas de televisão",
    "60": "Atividades de rádio e de televisão",
    "61": "Telecomunicações",
    "62": "Atividades dos serviços de tecnologia da informação",
    "63": "Atividades de prestação de serviços de informação",
    "64": "Atividades de serviços financeiros",
    "65": "Seguros, resseguros, previdência complementar e planos de saúde",
    "66": "Atividades auxiliares dos serviços financeiros",
    "68": "Atividades imobiliárias",
    "69": "Atividades jurídicas, de contabilidade e de auditoria",
    "70": "Atividades de sedes de empresas e de consultoria em gestão empresarial",
    "71": "Serviços de arquitetura e engenharia",
    "72": "Pesquisa e desenvolvimento científico",
    "73": "Publicidade e pesquisa de mercado",
    "74": "Outras atividades profissionais, científicas e técnicas",
    "75": "Atividades veterinárias",
    "77": "Aluguéis não-imobiliários e gestão de ativos intangíveis",
    "78": "Seleção, agenciamento e locação de mão-de-obra",
    "79": "Agências de viagens, operadores turísticos e serviços de reservas",
    "80": "Atividades de vigilância, segurança e investigação",
    "81": "Serviços para edifícios e atividades paisagísticas",
    "82": "Serviços de escritório e apoio administrativo",
    "84": "Administração pública, defesa e seguridade social",
    "85": "Educação",
    "86": "Atividades de atenção à saúde humana",
    "87": "Atividades de atenção à saúde humana integradas com assistência social",
    "88": "Serviços de assistência social sem alojamento",
    "90": "Atividades artísticas, criativas e de espetáculos",
    "91": "Atividades ligadas ao patrimônio cultural e ambiental",
    "92": "Atividades de exploração de jogos de azar e apostas",
    "93": "Atividades esportivas e de recreação e lazer",
    "94": "Atividades de organizações associativas",
    "95": "Reparação e manutenção de equipamentos de informática e comunicação",
    "96": "Outras atividades de serviços pessoais",
}
