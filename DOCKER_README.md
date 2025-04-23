# Dockerização do Projeto Spot2

Este documento descreve como executar o projeto Spot2 usando Docker.

## Pré-requisitos

- Docker
- Docker Compose

## Estrutura de Arquivos

- `Dockerfile.backend`: Configuração para o container do backend (FastAPI)
- `Dockerfile.frontend`: Configuração para o container do frontend (Streamlit)
- `docker-compose.yml`: Configuração para orquestrar os serviços
- `.dockerignore`: Lista de arquivos a serem ignorados durante o build

## Configuração

1. Certifique-se de que o arquivo `.env` existe na raiz do projeto com a variável `GOOGLE_API_KEY` configurada:

```
GOOGLE_API_KEY=sua_chave_api_aqui
```

## Executando o Projeto

### Construir e Iniciar os Containers

```bash
docker-compose up --build
```

Isso irá:
- Construir as imagens Docker para o backend e frontend
- Iniciar os containers
- Expor o backend na porta 8000
- Expor o frontend na porta 8501

### Acessando a Aplicação

- Backend (API): http://localhost:8000
- Frontend (Streamlit): http://localhost:8501

### Parar os Containers

```bash
docker-compose down
```

## Desenvolvimento

### Reconstruir um Serviço Específico

```bash
docker-compose up --build <service_name>
```

Onde `<service_name>` pode ser `backend` ou `frontend`.

### Ver Logs

```bash
docker-compose logs -f
```

Para ver logs de um serviço específico:

```bash
docker-compose logs -f <service_name>
```

## Volumes

- Os logs são persistidos através de um volume montado em `./logs:/app/logs`

## Variáveis de Ambiente

As variáveis de ambiente são passadas do arquivo `.env` para os containers através do `docker-compose.yml`. 