# ProspectaBR 🇧🇷

**Sistema inteligente de prospecção B2B com dados reais da Receita Federal.**

Encontre clientes potenciais para sua empresa em qualquer região do Brasil usando Inteligência Artificial e dados oficiais de mais de 50 milhões de empresas.

---

## 🚀 Como Rodar

### Com Docker (recomendado)
```bash
docker-compose up --build
```

Acesse: [http://localhost:8000](http://localhost:8000)

### Sem Docker
```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## 📋 Como Usar

1. **Crie uma conta** no sistema
2. Vá em **Base de Dados** e importe os dados de pelo menos um estado
   - Os dados são baixados diretamente da Receita Federal (pode demorar)
3. Vá em **Prospectar** e descreva o ramo de atuação da sua empresa
4. Selecione o estado e cidade
5. Receba a lista de potenciais clientes com dados reais!

---

## 🏗️ Arquitetura

| Componente | Tecnologia |
|------------|-----------|
| Backend | Python + FastAPI |
| Banco de dados | SQLite |
| IA | Sentence Transformers (local) |
| Frontend | HTML + CSS + JavaScript |
| Container | Docker |

### Como a IA funciona:

1. **Interpretação semântica**: O modelo `paraphrase-multilingual-MiniLM-L12-v2` interpreta a descrição do seu negócio e encontra os CNAEs mais similares
2. **Mapeamento da cadeia produtiva**: O sistema identifica quais setores (CNAEs) seriam potenciais compradores do seu produto/serviço
3. **Busca geográfica**: Filtra empresas ativas na região selecionada com esses CNAEs
4. **Ranking por relevância**: Ordena os resultados por score de similaridade semântica

### Fonte dos dados:
- [Dados Abertos da Receita Federal - CNPJ](https://dadosabertos.rfb.gov.br/CNPJ/)
- Inclui: razão social, nome fantasia, CNAE, endereço, telefone, e-mail

---

## 📁 Estrutura do Projeto

```
prospectabr/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py             # Configurações
│   ├── database.py           # SQLite/SQLAlchemy
│   ├── models.py             # Modelos do banco
│   ├── schemas.py            # Schemas Pydantic
│   ├── auth.py               # Autenticação JWT
│   ├── routers/
│   │   ├── auth_router.py    # Rotas de autenticação
│   │   ├── prospects_router.py # Rotas de prospecção
│   │   └── data_router.py    # Rotas de importação
│   └── services/
│       ├── ai_matcher.py     # Motor de IA
│       ├── cnae_service.py   # Mapeamento CNAE
│       └── data_importer.py  # Importador Receita Federal
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 📝 Licença

Projeto open source. Dados da Receita Federal são de domínio público.
