from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
import logging
import traceback
import os
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .schemas import ChatRequest, ChatResponse
from ..services.chat_service import ChatService
from ..core.llm import sanitize_input
from ..core.security import (
    check_for_dangerous_content, 
    validate_conversation_history,
    check_rate_limit,
    validate_token,
    sanitize_html
)

# Error response model
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Authentication failed",
                "detail": "Invalid API key provided",
                "status_code": 401
            }
        }

# Configurar o logger
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"api_routes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_routes")

app = FastAPI(title="Spot2 Real Estate Chatbot API")

# Configurar CORS com origens específicas em produção
origins = [
    "http://localhost:8501",  # Streamlit local
    "http://localhost:3000",  # React local
    "https://seu-dominio.com"  # Domínio de produção
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Configurar autenticação por API key
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Inicializar o serviço de chat
chat_service = ChatService()

async def validate_request(request: Request) -> None:
    """
    Middleware to validate incoming requests.
    """
    try:
        # Get client IP
        client_ip = request.client.host
        
        # Check API key
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            logger.warning(f"Missing API key from {client_ip}")
            raise HTTPException(
                status_code=401,
                detail="API key is required"
            )
        
        if not validate_token(api_key):
            logger.warning(f"Invalid API key from {client_ip}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Check rate limit
        if not check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # For POST requests to /chat, validate the request body
        if request.method == "POST" and request.url.path == "/chat":
            body = await request.json()
            
            # Check for dangerous content
            if check_for_dangerous_content(body.get("message", "")):
                logger.warning(f"Dangerous content detected from {client_ip}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid input detected"
                )
            
            # Validate conversation history if present
            if "conversation_history" in body:
                try:
                    validate_conversation_history(body["conversation_history"])
                except ValueError as e:
                    logger.warning(f"Invalid conversation history from {client_ip}: {str(e)}")
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid conversation history"
                    )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during request validation"
        )

# Middleware para adicionar headers de segurança
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware para adicionar headers de segurança.
    """
    response = await call_next(request)
    
    # Adicionar headers de segurança
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    
    return response

async def get_api_key(api_key: Optional[str] = Header(None, alias=API_KEY_NAME)):
    """
    Validar a API key.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is missing")
    
    if not validate_token(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Process a chat message and return the response with collected fields.
    """
    logger.info(f"Recebida requisição de chat com mensagem: {request.message[:50]}...")
    logger.debug(f"Histórico de conversa: {len(request.conversation_history) if request.conversation_history else 0} mensagens")
    
    try:
        # Sanitizar a mensagem do usuário
        sanitized_message = sanitize_input(request.message)
        
        # Sanitizar HTML na mensagem
        sanitized_message = sanitize_html(sanitized_message)
        
        # Validar o histórico de conversa
        validated_history = validate_conversation_history(request.conversation_history)
        
        # Registrar tentativa de ataque se a mensagem foi modificada
        if sanitized_message != request.message:
            logger.warning(f"Tentativa de ataque detectada. Mensagem original: {request.message[:100]}...")
            logger.warning(f"Mensagem sanitizada: {sanitized_message[:100]}...")
        
        result = chat_service.process_message(
            message=sanitized_message,
            conversation_history=validated_history
        )
        logger.info("Requisição de chat processada com sucesso")
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Erro ao processar requisição de chat: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/reset")
async def reset_conversation(api_key: str = Depends(get_api_key)):
    """
    Reset the conversation state.
    """
    logger.info("Recebida requisição para resetar conversa")
    try:
        chat_service.reset()
        logger.info("Conversa resetada com sucesso")
        return {"message": "Conversation reset successfully"}
    except Exception as e:
        logger.error(f"Erro ao resetar conversa: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """
    Endpoint para verificar a saúde da API.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler for HTTPException.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Custom exception handler for general exceptions.
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            status_code=500
        ).dict()
    ) 