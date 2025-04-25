from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from ..services.mongodb_service import MongoDBService

router = APIRouter(
    prefix="/mongodb",
    tags=["mongodb"],
    responses={404: {"description": "Not found"}},
)

# Instanciar o serviço MongoDB
mongodb_service = MongoDBService()

@router.get("/collections", response_model=List[str])
async def get_collections():
    """
    Retorna a lista de todas as coleções no banco de dados MongoDB.
    """
    try:
        collections = mongodb_service.get_all_collections()
        return collections
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar coleções: {str(e)}")

@router.get("/documents/{collection_name}", response_model=List[Dict[str, Any]])
async def get_documents(
    collection_name: str,
    limit: Optional[int] = Query(100, description="Número máximo de documentos a retornar")
):
    """
    Retorna todos os documentos de uma coleção específica.
    
    - **collection_name**: Nome da coleção
    - **limit**: Número máximo de documentos a retornar (padrão: 100)
    """
    try:
        documents = mongodb_service.get_all_documents(collection_name, limit)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar documentos: {str(e)}")

@router.get("/count/{collection_name}", response_model=Dict[str, int])
async def get_document_count(collection_name: str):
    """
    Retorna o número total de documentos em uma coleção.
    
    - **collection_name**: Nome da coleção
    """
    try:
        count = mongodb_service.get_document_count(collection_name)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao contar documentos: {str(e)}") 