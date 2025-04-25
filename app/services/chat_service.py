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
from pydantic import create_model

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
        """Initialize the ChatService with required fields and patterns."""
        self.required_fields = {
            "budget": None,
            "total_size": None,
            "property_type": None,
            "city": None
        }
        
        self.additional_fields = {}
        
        # Regex patterns for required fields
        self.patterns = {
            "budget": [
                r"budget.*?(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:per month|monthly|/month)",
                r"up to\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"maximum.*?(\d+(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "total_size": [
                r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:square\s*(?:meters?|m²|feet?|ft²)|m²|ft²)",
                r"(?:size|space).*?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:square\s*(?:meters?|m²|feet?|ft²)|m²|ft²)",
                r"at\s*least\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:square\s*(?:meters?|m²|feet?|ft²)|m²|ft²)"
            ],
            "property_type": [
                r"(?:looking\s*for|need|want)\s*(?:a|an)?\s*(\w+(?:\s+\w+)*)\s*(?:to\s*rent|for\s*rent)",
                r"rent\s*(?:a|an)?\s*(\w+(?:\s+\w+)*)",
                r"(\w+(?:\s+\w+)*)\s*(?:property|space|building)"
            ],
            "city": [
                r"(?:in|at|near)\s*([A-Za-z\s]+(?:City)?)",
                r"looking\s*in\s*([A-Za-z\s]+(?:City)?)",
                r"interested\s*in\s*([A-Za-z\s]+(?:City)?)"
            ]
        }
        
        # Initialize schema for validation
        self.schema = create_model(
            "PropertyRequirements",
            budget=(Optional[str], None),
            total_size=(Optional[str], None),
            property_type=(Optional[str], None),
            city=(Optional[str], None)
        )
        
        # Initialize LLM service
        self.llm = LLMService()
        
        logger.info("ChatService initialized successfully")
    
    def extract_fields(self, message: str) -> Dict[str, str]:
        """
        Extract fields from a message using regex patterns.
        
        Args:
            message (str): The message to extract fields from
            
        Returns:
            Dict[str, str]: The extracted fields
        """
        extracted_fields = {}
        
        # Extract required fields
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    extracted_fields[field] = match.group(1)
                    logger.debug(f"Campo extraído: {field} = {match.group(1)}")
                    break
        
        # Additional field patterns with improved regex
        additional_patterns = {
            "additional_parking": r"(?:must\s+have|with|need|requires?)\s+(?:a\s+)?parking(?:\s+lot)?",
            "additional_bathrooms": r"(?:with|has|have|need)\s+(\d+)\s+bath(?:room)?s?",
            "additional_pet_friendly": r"(?:must\s+be\s+)?pet[\s-]friendly",
            "additional_furnished": r"(?:must\s+be\s+)?furnished",
            "additional_location": r"(?:in|at|near)\s+the\s+(\w+(?:\s+\w+)*)\s+(?:zone|area|district)",
            "additional_bedrooms": r"(?:with|has|have|need)\s+(\d+)\s+bed(?:room)?s?",
            "additional_amenities": r"(?:with|include|has|have)\s+(\w+(?:\s+\w+)*)\s+(?:amenities|facilities)"
        }
        
        # Extract additional fields with improved handling
        for field, pattern in additional_patterns.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                if len(match.groups()) > 0:
                    # For fields that capture a value (like number of bathrooms)
                    value = match.group(1)
                    # Try to convert numeric values
                    try:
                        if field in ["additional_bathrooms", "additional_bedrooms"]:
                            value = int(value)
                    except (ValueError, TypeError):
                        continue
                else:
                    # For boolean fields (like pet-friendly)
                    value = True
                
                extracted_fields[field] = value
                logger.debug(f"Campo adicional extraído: {field} = {value}")
        
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
                # Clean up the field name and value
                clean_field = field.replace("additional_", "")
                clean_value = value.strip() if isinstance(value, str) else value
                
                # Special handling for boolean fields
                if clean_field in ["parking", "pet_friendly", "furnished"]:
                    clean_value = True
                
                # Special handling for numeric fields
                elif clean_field in ["bathrooms", "bedrooms"]:
                    try:
                        clean_value = int(clean_value)
                    except (ValueError, TypeError):
                        clean_value = None
                
                # Store the cleaned field and value
                if clean_value is not None:
                    self.additional_fields[clean_field] = clean_value
                    logger.debug(f"Campo adicional atualizado: {clean_field} = {clean_value}")
    
    def process_message(self, message: str, conversation_history: Optional[List[ChatMessage]] = None) -> Dict:
        """
        Process a user message and return a response.
        
        Args:
            message (str): The user's message
            conversation_history (Optional[List[ChatMessage]]): The conversation history
            
        Returns:
            Dict: The response containing the assistant's message and collected fields
        """
        # Sanitize the message
        sanitized_message = self._sanitize_input(message)
        if sanitized_message != message:
            logger.warning(f"Potential attack detected. Original message: {message}")
        
        # Extract fields from the message
        extracted_fields = self.extract_fields(sanitized_message)
        logger.info(f"Extracted {len(extracted_fields)} fields from message")
        
        # Update fields with extracted values
        self.update_fields(extracted_fields)
        
        # Get response from LLM
        response = self.llm.get_response(
            message=sanitized_message,
            conversation_history=conversation_history,
            collected_fields=self.required_fields,
            additional_fields=self.additional_fields
        )
        
        # Validate collected fields
        try:
            self.schema(**self.required_fields)
            is_complete = True
        except ValidationError:
            is_complete = False
        
        # Clean up additional fields for display
        display_additional_fields = {}
        for field, value in self.additional_fields.items():
            # Format boolean values
            if isinstance(value, bool):
                display_additional_fields[field] = "Yes"
            # Format numeric values
            elif isinstance(value, (int, float)):
                display_additional_fields[field] = str(value)
            # Format string values
            else:
                display_additional_fields[field] = value
        
        # Prepare the result
        result = {
            "response": response,
            "collected_fields": self.required_fields,
            "is_complete": is_complete,
            "additional_fields": display_additional_fields
        }
        
        logger.info(f"Processed message. Fields collected: {len(self.required_fields)}")
        return result
    
    def reset(self):
        """Reset the conversation state."""
        logger.info("Resetando estado da conversa")
        self.required_fields = {field: None for field in self.required_fields}
        self.additional_fields = {}
        logger.info("Estado da conversa resetado com sucesso") 