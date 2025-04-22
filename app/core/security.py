import re
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Configurar o logger
logger = logging.getLogger("security")

# Padrões de conteúdo potencialmente perigoso
DANGEROUS_PATTERNS = [
    # Tentativas de executar código
    r'(?i)(execute|run|eval|exec|import|require|include)\s*\([^)]*\)',
    r'(?i)(function|def|class|module|package)\s*\([^)]*\)',
    r'(?i)(bash|shell|terminal|command|cmd)\s*\([^)]*\)',
    
    # Tentativas de acessar arquivos ou sistema
    r'(?i)(file:|open:|read:|write:|delete:|remove:|system:|os\.|subprocess)\s*\([^)]*\)',
    r'(?i)(path|directory|folder|drive|volume)\s*\([^)]*\)',
    r'(?i)(/etc|/var|/usr|/bin|/sbin|/opt)\s*\([^)]*\)',
    
    # Tentativas de acessar variáveis de ambiente
    r'(?i)(env:|environment:|process\.env)\s*\([^)]*\)',
    r'(?i)(config|settings|configuration)\s*\([^)]*\)',
    
    # Tentativas de acessar chaves de API ou segredos
    r'(?i)(api key|secret|password|token|credential)\s*\([^)]*\)',
    r'(?i)(private|confidential|sensitive)\s*\([^)]*\)',
    
    # Tentativas de injeção de código
    r'(?i)(<script|javascript:|data:|vbscript:|onload=|onerror=)\s*\([^)]*\)',
    r'(?i)(<iframe|<embed|<object|<applet)\s*\([^)]*\)',
    
    # Tentativas de injeção SQL
    r'(?i)(union|select|insert|update|delete|drop|alter|create)\s*\([^)]*\)',
    r'(?i)(--|;|/\*|\*/)\s*\([^)]*\)',
    
    # Tentativas de ataques de prompt injection avançados
    r'(?i)(base64|hex|binary|encode|decode)\s*\([^)]*\)',
    r'(?i)(regex|pattern|match|search)\s*\([^)]*\)',
    r'(?i)(memory|buffer|stack|heap)\s*\([^)]*\)',
    r'(?i)(overflow|underflow|leak)\s*\([^)]*\)',
]

# Limites de tamanho
MAX_PROMPT_LENGTH = 1000
MAX_RESPONSE_LENGTH = 5000
MAX_FIELD_LENGTH = 100
MAX_HISTORY_LENGTH = 20

# Configurações de rate limiting
RATE_LIMIT_WINDOW = 3600  # segundos (1 hora)
MAX_REQUESTS_PER_WINDOW = 100  # requisições por janela
MIN_TOKEN_LENGTH = 32  # Minimum length for API tokens

# Configurações de validação de campos
FIELD_VALIDATION = {
    "budget": {
        "pattern": r'^\d+(\.\d{1,2})?$',
        "max_length": 10,
        "min_value": 10000,
        "max_value": 1000000000,
        "description": "Budget in currency units (no currency symbol)"
    },
    "total_size": {
        "pattern": r'^\d+(\.\d{1,2})?$',
        "max_length": 10,
        "min_value": 10,
        "max_value": 10000,
        "description": "Total size in square meters"
    },
    "property_type": {
        "pattern": r'^(apartment|house|commercial)$',
        "max_length": 20,
        "allowed_values": ["apartment", "house", "commercial"],
        "description": "Type of property"
    },
    "city": {
        "pattern": r'^[a-zA-Z\s\-\']+$',
        "max_length": 50,
        "description": "City name"
    },
}

# Armazenamento para rate limiting
rate_limit_store: Dict[str, List[float]] = {}

def check_for_dangerous_content(text: str) -> bool:
    """
    Verificar se o texto contém conteúdo potencialmente perigoso.
    
    Args:
        text (str): O texto a ser verificado
        
    Returns:
        bool: True se o texto contém conteúdo perigoso, False caso contrário
    """
    if not text:
        return False
        
    # Verificar padrões perigosos
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text):
            logger.warning(f"Conteúdo potencialmente perigoso detectado: {pattern}")
            return True
    
    # Verificar tentativas de injeção de prompt mais avançadas
    if _check_advanced_injection(text):
        return True
            
    return False

def _check_advanced_injection(text: str) -> bool:
    """
    Verificar tentativas avançadas de injeção de prompt.
    
    Args:
        text (str): O texto a ser verificado
        
    Returns:
        bool: True se detectada tentativa avançada de injeção, False caso contrário
    """
    # Verificar tentativas de usar caracteres especiais para contornar filtros
    if re.search(r'(?i)(\\u|\\x|\\0|\\n|\\r|\\t)', text):
        logger.warning("Tentativa de injeção usando caracteres de escape detectada")
        return True
    
    # Verificar tentativas de usar Unicode para contornar filtros
    if re.search(r'(?i)(U\+[0-9a-f]{4,6}|&#x?[0-9a-f]+;)', text):
        logger.warning("Tentativa de injeção usando Unicode detectada")
        return True
    
    # Verificar tentativas de usar comentários para contornar filtros
    if re.search(r'(?i)(/\*.*?\*/|<!--.*?-->|#.*?$)', text):
        logger.warning("Tentativa de injeção usando comentários detectada")
        return True
    
    # Verificar tentativas de usar concatenação para contornar filtros
    if re.search(r'(?i)(\+|concat|join|append)', text):
        logger.warning("Tentativa de injeção usando concatenação detectada")
        return True
    
    return False

def validate_field(field_name: str, value: str) -> Optional[str]:
    """
    Validar um valor de campo com base nas regras definidas.
    
    Args:
        field_name (str): O nome do campo
        value (str): O valor do campo
        
    Returns:
        Optional[str]: O valor validado ou None se inválido
    """
    if not value:
        return value
        
    # Verificar se o campo tem regras de validação
    if field_name in FIELD_VALIDATION:
        rules = FIELD_VALIDATION[field_name]
        
        # Verificar o padrão
        if not re.match(rules["pattern"], value):
            logger.warning(f"Valor inválido para o campo {field_name}: {value}")
            return None
            
        # Verificar o tamanho
        if len(value) > rules["max_length"]:
            logger.warning(f"Valor muito longo para o campo {field_name}: {value}")
            return value[:rules["max_length"]]
        
        # Verificar valores numéricos
        if "min_value" in rules and "max_value" in rules:
            try:
                num_value = float(value)
                if num_value < rules["min_value"] or num_value > rules["max_value"]:
                    logger.warning(f"Valor fora do intervalo para o campo {field_name}: {value}")
                    return None
            except ValueError:
                logger.warning(f"Valor não numérico para o campo {field_name}: {value}")
                return None
        
        # Verificar valores permitidos
        if "allowed_values" in rules and value.lower() not in rules["allowed_values"]:
            logger.warning(f"Valor não permitido para o campo {field_name}: {value}")
            return None
    
    # Para campos adicionais, aplicar regras genéricas
    elif field_name.startswith("additional_"):
        if len(value) > MAX_FIELD_LENGTH:
            logger.warning(f"Valor muito longo para o campo adicional {field_name}: {value}")
            return value[:MAX_FIELD_LENGTH]
    
    # Verificar se o valor contém conteúdo perigoso
    if check_for_dangerous_content(value):
        logger.warning(f"Valor do campo {field_name} contém conteúdo perigoso")
        return None
    
    return value

def validate_conversation_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validar o histórico de conversa.
    
    Args:
        history (List[Dict[str, Any]]): O histórico de conversa
        
    Returns:
        List[Dict[str, Any]]: O histórico de conversa validado
    """
    if not history:
        return []
        
    # Limitar o tamanho do histórico
    if len(history) > MAX_HISTORY_LENGTH:
        logger.warning(f"Histórico de conversa muito longo, truncando de {len(history)} para {MAX_HISTORY_LENGTH}")
        history = history[-MAX_HISTORY_LENGTH:]
    
    validated_history = []
    
    for message in history:
        # Verificar se a mensagem tem os campos necessários
        if "role" not in message or "content" not in message:
            logger.warning(f"Mensagem inválida ignorada: {message}")
            continue
            
        # Verificar se o papel é válido
        if message["role"] not in ["user", "assistant"]:
            logger.warning(f"Papel inválido ignorado: {message['role']}")
            continue
            
        # Verificar se o conteúdo contém conteúdo perigoso
        if check_for_dangerous_content(message["content"]):
            logger.warning(f"Conteúdo perigoso detectado na mensagem, substituindo por mensagem segura")
            message["content"] = "I apologize, but I can only assist with real estate inquiries."
            
        validated_history.append(message)
    
    return validated_history

def check_rate_limit(client_ip: str) -> bool:
    """
    Check if the client has exceeded the rate limit.
    """
    current_time = time.time()
    
    # Clean up old entries
    if client_ip in rate_limit_store:
        rate_limit_store[client_ip] = [
            timestamp for timestamp in rate_limit_store[client_ip]
            if current_time - timestamp < RATE_LIMIT_WINDOW
        ]
    
    # Initialize or get existing timestamps
    timestamps = rate_limit_store.get(client_ip, [])
    
    # Check if limit is exceeded
    if len(timestamps) >= MAX_REQUESTS_PER_WINDOW:
        return False
    
    # Add current timestamp
    timestamps.append(current_time)
    rate_limit_store[client_ip] = timestamps
    
    return True

def validate_token(token: str) -> bool:
    """
    Validate an API token.
    In production, this should be replaced with proper token validation.
    """
    if not token or len(token) < MIN_TOKEN_LENGTH:
        return False
    return True

def sanitize_html(text: str) -> str:
    """
    Sanitizar texto para remover HTML potencialmente perigoso.
    
    Args:
        text (str): O texto a ser sanitizado
        
    Returns:
        str: O texto sanitizado
    """
    # Remover tags HTML
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remover atributos de eventos
    text = re.sub(r'on\w+="[^"]*"', '', text)
    
    # Remover URLs de javascript
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validar dados JSON contra um schema.
    
    Args:
        data (Dict[str, Any]): Os dados a serem validados
        schema (Dict[str, Any]): O schema de validação
        
    Returns:
        bool: True se os dados são válidos, False caso contrário
    """
    # Implementação básica - em produção, use uma biblioteca como jsonschema
    try:
        # Verificar campos obrigatórios
        for field, field_schema in schema.items():
            if field_schema.get("required", False) and field not in data:
                logger.warning(f"Campo obrigatório ausente: {field}")
                return False
            
            if field in data:
                # Verificar tipo
                if "type" in field_schema:
                    expected_type = field_schema["type"]
                    if expected_type == "string" and not isinstance(data[field], str):
                        logger.warning(f"Campo {field} deve ser string")
                        return False
                    elif expected_type == "number" and not isinstance(data[field], (int, float)):
                        logger.warning(f"Campo {field} deve ser número")
                        return False
                    elif expected_type == "boolean" and not isinstance(data[field], bool):
                        logger.warning(f"Campo {field} deve ser booleano")
                        return False
                
                # Verificar enum
                if "enum" in field_schema and data[field] not in field_schema["enum"]:
                    logger.warning(f"Valor inválido para campo {field}: {data[field]}")
                    return False
                
                # Verificar padrão
                if "pattern" in field_schema and not re.match(field_schema["pattern"], str(data[field])):
                    logger.warning(f"Valor não corresponde ao padrão para campo {field}: {data[field]}")
                    return False
        
        return True
    except Exception as e:
        logger.error(f"Erro ao validar schema JSON: {str(e)}")
        return False 