from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Endpoint para verificar a saúde da aplicação
    """
    return {"status": "healthy"} 