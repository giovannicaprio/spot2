from typing import Dict, List, Optional, Any
import re
import logging
import traceback
import os
import time
from datetime import datetime
from ..core.llm import get_llm_response, sanitize_input
from ..core.security import (
    validate_field, 
    check_for_dangerous_content,
    sanitize_html,
    validate_json_schema
)
from ..api.schemas import ChatMessage, RealEstateRequirements

# Configurar o logger
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"chat_service_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("chat_service")

# Schema para validação de campos
FIELD_SCHEMA = {
    "budget": {
        "type": "string",
        "pattern": r'^\d+(?:,\d+)*(?:\.\d+)?$',
        "required": True
    },
    "total_size": {
        "type": "string",
        "pattern": r'^\d+(?:,\d+)*(?:\.\d+)?$',
        "required": True
    },
    "property_type": {
        "type": "string",
        "pattern": r'^[a-zA-Z\s-]+$',
        "required": True
    },
    "city": {
        "type": "string",
        "pattern": r'^[a-zA-Z\s-]+$',
        "required": True
    }
}

class ChatService:
    def __init__(self):
        logger.info("Inicializando ChatService")
        self.required_fields = {
            "budget": None,
            "total_size": None,
            "property_type": None,
            "city": None
        }
        self.additional_fields = {}
        
        # Patterns for field extraction
        self.patterns = {
            "budget": r"(?:budget|price|cost|\$|USD|EUR|€|£|R\$)\s*(?:is|:)?\s*(\d+(?:\.|,)\d+|\d+)\s*(?:per month|monthly|/month|al mes|por mes)?",
            "total_size": r"(?:size|area|space|square meters|square feet|sq ft|m²|metros?)\s*(?:of|is|:)?\s*(?:at least|minimum|approximately|about|al menos|mínimo|aproximadamente)?\s*(\d+(?:\.|,)\d+|\d+)",
            "property_type": r"(?:looking for|need|want|searching for|busco|necesito|quiero)\s+(?:a|an|el|la|un|una)?\s*([a-zA-ZÀ-ú\s-]+?)(?:\s+(?:to|with|that|for|para|con|que|in|\.|\n|$))",
            "city": r"(?:in|at|near|en|cerca de|próximo a)\s+([A-Za-zÀ-ú\s-]+?)(?:\s*(?:,|\.|$|\s+(?:preferably|specifically|zone|area|región|zona|área|area)))"
        }
        logger.info("ChatService initialized successfully")
    
    def extract_fields(self, text: str) -> Dict[str, str]:
        """
        Extract fields from text using regex patterns.
        
        Args:
            text (str): Text to extract fields from
            
        Returns:
            Dict[str, str]: Dictionary of extracted fields
        """
        logger.debug(f"Extracting fields from text: {text[:50]}...")
        extracted_fields = {}
        
        # Extract required fields
        for field, pattern in self.patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up the extracted value
                if field == "budget":
                    # Remove currency symbols and normalize
                    value = re.sub(r'[^\d.]', '', value)
                elif field == "total_size":
                    # Remove units and normalize
                    value = re.sub(r'[^\d.]', '', value)
                elif field == "property_type":
                    # Clean up property type and normalize to English
                    value = value.strip().lower()
                    # Normalize common variations
                    if any(term in value for term in ["warehouse", "galpão", "galpao", "almacén", "almacen", "storage"]):
                        value = "warehouse"
                    elif any(term in value for term in ["office", "escritório", "escritorio", "oficina"]):
                        value = "office"
                    elif any(term in value for term in ["store", "loja", "tienda", "retail"]):
                        value = "store"
                    elif any(term in value for term in ["industrial", "factory", "manufacturing"]):
                        value = "industrial"
                elif field == "city":
                    # Clean up city name and handle common formats
                    value = value.strip().title()
                    # Remove common suffixes in multiple languages
                    value = re.sub(r'\s+(?:zone|area|región|zona|área|area).*$', '', value, flags=re.IGNORECASE)
                    
                    # Skip if the value looks like a sentence fragment
                    if len(value.split()) > 3 or any(word.lower() in value.lower() for word in ["the", "and", "or", "but", "with", "for", "that", "this", "these", "those", "meet", "need", "want", "look", "search", "find"]):
                        continue
                
                # Validate the field value
                validated_value = validate_field(field, value)
                if validated_value is not None:
                    # Only update if the new value is valid and either:
                    # 1. The field doesn't exist yet, or
                    # 2. The new value is more specific/complete than the existing one
                    if (field not in extracted_fields or 
                        len(validated_value) > len(extracted_fields[field]) or
                        (field == "city" and "Mexico City" in validated_value)):
                        extracted_fields[field] = validated_value
                        logger.debug(f"Field extracted: {field} = {validated_value}")
        
        
        logger.info(f"Total de campos extraídos: {len(extracted_fields)}")
        return extracted_fields
    
    def update_fields(self, extracted_fields: Dict[str, str]):
        """
        Update the fields with newly extracted values.
        
        Args:
            extracted_fields (Dict[str, str]): Newly extracted fields
        """
        logger.debug(f"Atualizando campos com {len(extracted_fields)} valores extraídos")
        
        # Update required fields
        for field in self.required_fields:
            if field in extracted_fields:
                self.required_fields[field] = extracted_fields[field]
                logger.debug(f"Campo obrigatório atualizado: {field} = {extracted_fields[field]}")
        
        # Update additional fields
        for field, value in extracted_fields.items():
            if field.startswith("additional_"):
                self.additional_fields[field] = value
                logger.debug(f"Campo adicional atualizado: {field} = {value}")
    
    def process_message(self, message: str, conversation_history: Optional[List[ChatMessage]] = None) -> Dict:
        """
        Process a user message and return the response with collected fields.
        
        Args:
            message (str): The user's message
            conversation_history (List[ChatMessage], optional): Previous conversation messages
            
        Returns:
            Dict: Contains response, collected fields, and completion status
        """
        logger.info(f"Processando mensagem: {message[:50]}...")
        
        try:
            # Sanitize the user's message
            sanitized_message = sanitize_input(message)
            
            # Sanitizar HTML na mensagem
            sanitized_message = sanitize_html(sanitized_message)
            
            # Registrar tentativa de ataque se a mensagem foi modificada
            if sanitized_message != message:
                logger.warning(f"Tentativa de ataque detectada. Mensagem original: {message[:100]}...")
                logger.warning(f"Mensagem sanitizada: {sanitized_message[:100]}...")
            
            # Extract fields from user message
            logger.debug("Extraindo campos da mensagem do usuário")
            extracted_fields = self.extract_fields(sanitized_message)
            
            # Update fields with extracted values
            logger.debug("Atualizando campos com valores extraídos")
            self.update_fields(extracted_fields)
            
            # Get LLM response with collected fields
            logger.debug("Obtendo resposta do LLM")
            collected_fields = {**self.required_fields, **self.additional_fields}
            llm_response = get_llm_response(sanitized_message, conversation_history, collected_fields)
            
            # Extract fields from LLM response
            logger.debug("Extraindo campos da resposta do LLM")
            extracted_fields.update(self.extract_fields(llm_response))
            
            # Update fields with extracted values from LLM response
            logger.debug("Atualizando campos com valores extraídos da resposta do LLM")
            self.update_fields(extracted_fields)
            
            # Check if all required fields are collected
            is_complete = all(value is not None for value in self.required_fields.values())
            logger.info(f"Todos os campos obrigatórios coletados: {is_complete}")
            
            # Validar campos coletados contra o schema
            collected_fields = {**self.required_fields, **self.additional_fields}
            if not validate_json_schema(collected_fields, FIELD_SCHEMA):
                logger.warning("Campos coletados não passaram na validação do schema")
            
            result = {
                "response": llm_response,
                "collected_fields": collected_fields,
                "is_complete": is_complete
            }
            
            logger.info("Processamento de mensagem concluído com sucesso")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def reset(self):
        """Reset the conversation state."""
        logger.info("Resetando estado da conversa")
        self.required_fields = {field: None for field in self.required_fields}
        self.additional_fields = {}
        logger.info("Estado da conversa resetado com sucesso") 