# Spot2 Real Estate Chatbot

Uma aplicação web de IA Conversacional para coleta de informações sobre imóveis comerciais.

## Estrutura do Projeto

```
spot2/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── llm.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── real_estate.py
│   └── services/
│       ├── __init__.py
│       └── chat_service.py
├── frontend/
│   └── streamlit_app.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Configuração

1. Clone o repositório
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   .\venv\Scripts\activate  # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente no arquivo `.env`
5. Execute o backend:
   ```bash
   uvicorn app.api.routes:app --reload
   ```
6. Execute o frontend:
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## Arquitetura

O projeto segue uma arquitetura modular com as seguintes camadas:

1. **API Layer**: FastAPI para endpoints REST
2. **Core Layer**: Configurações e integração com LLM
3. **Models Layer**: Definições de schemas e modelos de dados
4. **Services Layer**: Lógica de negócios e processamento de chat
5. **Frontend Layer**: Interface Streamlit

## Campos Obrigatórios

- Budget
- Total Size Requirement
- Real Estate Type
- City

## Campos Adicionais

O sistema permite a adição de campos extras durante a conversa. 