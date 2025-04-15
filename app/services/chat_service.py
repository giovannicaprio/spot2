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
        
        # Regex patterns for field extraction
        self.patterns = {
            "budget": r"(?:budget|spend|cost|price|USD|EUR|€|\$)\s*(?:of|is|:)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:USD|EUR|€|\$)?",
            "total_size": r"(?:size|area|space|m²|sqm|square meters|square metres)\s*(?:of|is|:)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:m²|sqm|square meters|square metres)?",
            "property_type": r"(?:looking for|need|want|type|property|space)\s+(?:a|an)?\s+([a-zA-Z\s]+?)(?:\s+(?:in|at|for|with|that|which))",
            "city": r"(?:in|at|near|around|close to)\s+([A-Za-z\s]+?)(?:\s+(?:with|that|which|,|\.|$))"
        }
        logger.info("ChatService inicializado com sucesso")
    
    def extract_fields(self, text: str) -> Dict[str, str]:
        """
        Extract fields from text using regex patterns.
        
        Args:
            text (str): Text to extract fields from
            
        Returns:
            Dict[str, str]: Dictionary of extracted fields
        """
        logger.debug(f"Extraindo campos do texto: {text[:50]}...")
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
                    # Clean up property type
                    value = value.strip().lower()
                elif field == "city":
                    # Clean up city name
                    value = value.strip().title()
                
                # Validate the field value
                validated_value = validate_field(field, value)
                if validated_value is not None:
                    extracted_fields[field] = validated_value
                    logger.debug(f"Campo extraído: {field} = {validated_value}")
        
        # Look for additional fields
        # This is a simple implementation that looks for key-value pairs
        # Format: "field: value" or "field is value"
        additional_pattern = r"([a-zA-Z\s]+?)(?:\s*:|\s+is)\s+([^,.]+?)(?=,|\.|$)"
        additional_matches = re.finditer(additional_pattern, text, re.IGNORECASE)
        
        for match in additional_matches:
            field = match.group(1).strip().lower().replace(" ", "_")
            value = match.group(2).strip()
            
            # Skip if it's one of our required fields
            if field not in self.required_fields:
                # Sanitize the field name
                field = re.sub(r'[^a-z_]', '', field)
                
                # Validate the field value
                validated_value = validate_field(f"additional_{field}", value)
                if validated_value is not None:
                    extracted_fields[f"additional_{field}"] = validated_value
                    logger.debug(f"Campo adicional extraído: {field} = {validated_value}")
        
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
            
            # Get LLM response
            logger.debug("Obtendo resposta do LLM")
            llm_response = get_llm_response(sanitized_message, conversation_history)
            
            # Extract fields from both user message and LLM response
            logger.debug("Extraindo campos da mensagem do usuário")
            extracted_fields = self.extract_fields(sanitized_message)
            
            logger.debug("Extraindo campos da resposta do LLM")
            extracted_fields.update(self.extract_fields(llm_response))
            
            # Update fields with extracted values
            logger.debug("Atualizando campos com valores extraídos")
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