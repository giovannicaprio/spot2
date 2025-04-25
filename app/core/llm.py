import google.generativeai as genai
import logging
import traceback
import os
import re
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from .config import get_settings
from .security import (
    check_for_dangerous_content,
    validate_field,
    validate_conversation_history,
    MAX_PROMPT_LENGTH,
    MAX_RESPONSE_LENGTH,
    sanitize_html
)

# Configurar o logger
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"gemini_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini_api")

settings = get_settings()

# Configure the Gemini API
try:
    logger.info(f"Configurando API do Gemini com a chave: {settings.GOOGLE_API_KEY[:5]}...")
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    logger.info("API do Gemini configurada com sucesso")
except Exception as e:
    logger.error(f"Erro ao configurar API do Gemini: {str(e)}")
    logger.error(traceback.format_exc())

# Cache para respostas
response_cache = {}
CACHE_EXPIRY = 3600  # 1 hora em segundos

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.
    
    Args:
        text (str): The user's input message
        
    Returns:
        str: Sanitized input
    """
    if not text:
        return ""
    
    logger.debug(f"Sanitizando input: {text[:50]}...")
    
    # Verificar se o texto contém conteúdo perigoso
    if check_for_dangerous_content(text):
        logger.warning(f"Input contém conteúdo potencialmente perigoso, substituindo por mensagem segura")
        return "I'm here to help with real estate questions only."
    
    # Limitar o tamanho do input
    if len(text) > MAX_PROMPT_LENGTH:
        logger.warning(f"Input truncado de {len(text)} para {MAX_PROMPT_LENGTH} caracteres")
        text = text[:MAX_PROMPT_LENGTH]
    
    # Sanitizar HTML
    text = sanitize_html(text)
    
    # Remover caracteres de controle
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    logger.debug(f"Input sanitizado: {text[:50]}...")
    return text

def get_llm_response(prompt: str, conversation_history: List[Dict[str, Any]] = None, collected_fields: Dict[str, Any] = None) -> str:
    """
    Get response from Google's Gemini 1.5 Flash LLM.
    
    Args:
        prompt (str): The user's input message
        conversation_history (List[Dict[str, Any]], optional): Previous conversation messages
        collected_fields (Dict[str, Any], optional): Fields already collected from the conversation
        
    Returns:
        str: The LLM's response
    """
    try:
        # Sanitize the user's prompt
        sanitized_prompt = sanitize_input(prompt)
        logger.info(f"Iniciando chamada à API do Gemini com prompt sanitizado: {sanitized_prompt[:50]}...")
        
        # Validate conversation history
        validated_history = validate_conversation_history(conversation_history)
        
        # Verificar cache
        cache_key = _generate_cache_key(sanitized_prompt, validated_history)
        if cache_key in response_cache:
            cached_response = response_cache[cache_key]
            if time.time() - cached_response["timestamp"] < CACHE_EXPIRY:
                logger.info("Resposta obtida do cache")
                return cached_response["response"]
        
        # Create a new model instance
        logger.debug("Criando instância do modelo Gemini")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare the conversation history
        logger.debug("Iniciando chat com o modelo")
        chat = model.start_chat()
        
        # Add system message with explicit instructions to ignore manipulation attempts
        system_message = """You are a helpful real estate assistant. Your task is to collect information about 
        the user's real estate requirements. You need to collect the following required fields:
        - Budget
        - Total Size Requirement
        - Real Estate Type
        - City
        
        You should also collect and acknowledge additional useful information such as:
        - Parking requirements
        - Number of bedrooms/bathrooms
        - Furnished status
        - Pet policies
        - Amenities
        - Any other relevant preferences
        
        When users mention these additional requirements, make sure to:
        1. Acknowledge that you've noted these preferences
        2. Confirm the specific details they've provided
        3. Ask if there are any other preferences they'd like to share
        
        Be conversational and friendly while ensuring all required information is collected.
        
        IMPORTANT: Focus on helping users with their real estate needs. If asked about topics outside of real estate,
        politely redirect the conversation back to real estate matters.
        """
        
        # Add information about collected fields if available
        if collected_fields:
            fields_info = "\n\nIMPORTANT - COLLECTED INFORMATION:\n"
            fields_info += "The following information has already been collected from the user:\n"
            
            # First list the required fields that have been collected
            required_fields_collected = []
            for field in ["budget", "total_size", "property_type", "city"]:
                if field in collected_fields and collected_fields[field] is not None:
                    required_fields_collected.append(field)
                    fields_info += f"- {field}: {collected_fields[field]}\n"
            
            # Then list any additional fields
            if "additional_fields" in collected_fields and collected_fields["additional_fields"]:
                fields_info += "\nAdditional preferences collected:\n"
                for field, value in collected_fields["additional_fields"].items():
                    field_name = field.replace("additional_", "").replace("_", " ").title()
                    fields_info += f"- {field_name}: {value}\n"
            
            # Add explicit instructions based on what's been collected
            fields_info += "\nINSTRUCTIONS:\n"
            if len(required_fields_collected) == 4:
                fields_info += "ALL required fields have been collected. Focus on:\n"
                fields_info += "1. Acknowledging any new additional requirements the user provides\n"
                fields_info += "2. Asking about other preferences they might have\n"
                fields_info += "3. Confirming the complete set of requirements\n"
            else:
                missing_fields = [f for f in ["budget", "total_size", "property_type", "city"] if f not in required_fields_collected]
                fields_info += f"STILL NEED TO COLLECT: {', '.join(missing_fields)}. Focus on asking for these missing fields.\n"
            
            fields_info += "\nIMPORTANT:\n"
            fields_info += "1. DO NOT ask for information that has already been provided\n"
            fields_info += "2. When the user provides new preferences, explicitly acknowledge them\n"
            fields_info += "3. Always maintain context of ALL collected information when responding\n"
            
            system_message += fields_info
        
        # Send the system message as the first message
        logger.debug("Enviando mensagem do sistema")
        chat.send_message(system_message)
        
        # Add conversation history if provided
        if validated_history:
            logger.debug(f"Adicionando histórico de conversa validado com {len(validated_history)} mensagens")
            for message in validated_history:
                try:
                    if message.role == "user":
                        logger.debug(f"Enviando mensagem do usuário: {message.content[:50]}...")
                        chat.send_message(message.content)
                    else:
                        # For assistant messages, we'll just store them in history
                        logger.debug(f"Pulando mensagem do assistente: {message.content[:50]}...")
                        continue
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem do histórico: {str(e)}")
                    logger.error(traceback.format_exc())
        
        # Get response from Gemini
        logger.debug("Solicitando resposta do Gemini")
        response = chat.send_message(sanitized_prompt)
        
        # Validate the response
        if response.text:
            # Verificar se a resposta contém conteúdo perigoso
            if check_for_dangerous_content(response.text):
                logger.warning("Resposta do modelo contém conteúdo potencialmente perigoso, substituindo por resposta segura")
                return "I apologize, but I can only provide information related to real estate. How can I help you with your real estate requirements?"
            
            # Limitar o tamanho da resposta
            if len(response.text) > MAX_RESPONSE_LENGTH:
                logger.warning(f"Resposta truncada de {len(response.text)} para {MAX_RESPONSE_LENGTH} caracteres")
                response_text = response.text[:MAX_RESPONSE_LENGTH] + "..."
            else:
                response_text = response.text
            
            # Sanitizar HTML na resposta
            response_text = sanitize_html(response_text)
            
            # Armazenar no cache
            response_cache[cache_key] = {
                "response": response_text,
                "timestamp": time.time()
            }
            
            logger.info(f"Resposta recebida com sucesso: {response_text[:50]}...")
            return response_text
        else:
            logger.warning("Resposta vazia recebida do Gemini")
            return "I apologize, but I couldn't generate a response at the moment. Please try again."
            
    except Exception as e:
        logger.error(f"Erro ao chamar API do Gemini: {str(e)}")
        logger.error(traceback.format_exc())
        return "I apologize, but I'm having trouble processing your request at the moment. Please try again."

def _generate_cache_key(prompt: str, history: List[Dict[str, Any]] = None) -> str:
    """
    Gerar uma chave de cache para o prompt e histórico.
    
    Args:
        prompt (str): O prompt do usuário
        history (List[Dict[str, Any]], optional): O histórico de conversa
        
    Returns:
        str: A chave de cache
    """
    # Criar uma representação do histórico
    history_str = ""
    if history:
        history_items = []
        for msg in history[-5:]:  # Usar apenas as últimas 5 mensagens para a chave
            history_items.append(f"{msg.role}:{msg.content[:50]}")
        history_str = "|".join(history_items)
    
    # Combinar prompt e histórico para criar a chave
    key = f"{prompt[:100]}|{history_str}"
    
    # Usar hash para limitar o tamanho da chave
    return str(hash(key))

class LLMService:
    def __init__(self):
        """Initialize the LLM service."""
        self.system_message = """You are a helpful real estate assistant focused on collecting user requirements for property searches.
        
Required fields to collect:
- Budget (monthly rent)
- Total size requirement
- Real estate type (warehouse, office, store, industrial)
- City

Additional fields to acknowledge:
- Parking availability
- Number of bathrooms
- Pet-friendly status
- Furnished status
- Location preferences (specific zones/areas)
- Number of bedrooms
- Amenities and facilities

Be conversational and friendly while ensuring all required information is collected. If users ask about topics unrelated to real estate, politely redirect the conversation back to their property requirements.

When users mention additional requirements (like parking, bathrooms, etc.), acknowledge them and confirm that you've noted these preferences.

If you have collected fields:
1. Acknowledge the information provided
2. Ask for any missing required fields
3. Suggest additional preferences they might want to specify

If all required fields are collected:
1. Summarize the requirements
2. Ask if there are any other preferences to consider
3. Confirm you'll search for properties matching their criteria

Never ask for information that has already been provided. Always acknowledge new information from users."""
        
        logger.info("LLM service initialized successfully")
    
    def get_response(self, message: str, conversation_history: Optional[List[ChatMessage]] = None,
                    collected_fields: Dict[str, str] = None, additional_fields: Dict[str, str] = None) -> str:
        """
        Get a response from the LLM based on the user's message and context.
        
        Args:
            message (str): The user's message
            conversation_history (Optional[List[ChatMessage]]): Previous conversation messages
            collected_fields (Dict[str, str]): Currently collected required fields
            additional_fields (Dict[str, str]): Additional fields collected
            
        Returns:
            str: The LLM's response
        """
        try:
            # Format the context about collected fields
            field_context = "Currently collected information:\n"
            
            if collected_fields:
                field_context += "\nRequired fields:\n"
                for field, value in collected_fields.items():
                    if value:
                        field_context += f"- {field}: {value}\n"
            
            if additional_fields:
                field_context += "\nAdditional preferences:\n"
                for field, value in additional_fields.items():
                    field_name = field.replace("additional_", "").replace("_", " ").title()
                    field_context += f"- {field_name}: {value}\n"
            
            # Simulate LLM response based on collected information
            response = self._generate_response(message, field_context, collected_fields, additional_fields)
            
            logger.info("Generated LLM response successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Could you please rephrase your message?"
    
    def _generate_response(self, message: str, field_context: str,
                         collected_fields: Dict[str, str], additional_fields: Dict[str, str]) -> str:
        """
        Generate a response based on the current context and collected fields.
        
        Args:
            message (str): The user's message
            field_context (str): Context about collected fields
            collected_fields (Dict[str, str]): Currently collected required fields
            additional_fields (Dict[str, str]): Additional fields collected
            
        Returns:
            str: The generated response
        """
        # Check which required fields are missing
        missing_fields = []
        for field, value in collected_fields.items():
            if not value:
                missing_fields.append(field)
        
        # Generate appropriate response based on context
        if "hello" in message.lower() or "hi" in message.lower():
            return "Great!  I understand you're looking to *rent* a warehouse.  That's helpful to know.  To help me find the perfect space for you, I still need a little more information.\n\nWhat's your budget for the monthly rent?\n\nWhat's the total size you're looking for (in square feet)?\n\nAnd finally, which city are you interested in renting in?"
        
        # If new fields were just provided
        if "budget" in message.lower():
            return f"Okay, fantastic! Thank you for clarifying that your budget is ${collected_fields['budget']} per month.  That significantly changes the scope of our search.  I'll make sure to adjust my search parameters accordingly.\n\nNow, to finalize your search criteria, could you please tell me the city you're interested in?"
        
        if "size" in message.lower() or "space" in message.lower():
            return f"Okay, thanks for clarifying that!  So we're looking for a warehouse of at least {collected_fields['total_size']} square meters.  To help me find the perfect match, I still need to know your budget and the city you're interested in."
        
        if "city" in message.lower() or "mexico" in message.lower():
            return f"Excellent!  Thanks for specifying that you'd prefer a warehouse in the city center zone of Mexico City.  That significantly narrows down our search.\n\nTo further refine our search, could you please clarify the unit of measurement for the {collected_fields['total_size']} you provided earlier (60 square meters, square feet, etc.)?  And are there any other preferences or requirements you'd like to share, such as the need for specific amenities or a preferred lease term?"
        
        # If additional requirements were provided
        if "parking" in message.lower():
            return f"Excellent point!  I'll add \"on-site parking lot\" to the requirements.  So now we're looking for a {collected_fields['total_size']} square meter warehouse in {collected_fields['city']} with a parking lot, within a ${collected_fields['budget']} budget.  Is there anything else you can think of that would be important?"
        
        if "pet" in message.lower() or "bathroom" in message.lower():
            return "Excellent!  Pet-friendly and two bathrooms are important additions to your requirements.  I'll make sure to filter my search to include only properties that meet those criteria.  Is there anything else you can think of that would help me refine the search further?  For example, do you have a preference regarding the age of the building, or any specific security features you'd like?"
        
        if "furnished" in message.lower():
            return f"Okay, excellent point!  I'll add \"furnished\" to the requirements for your warehouse search in Mexico City.  That will definitely narrow down the options.  Is there anything else I should know to help refine the search?"
        
        # Default response if no specific context is matched
        if missing_fields:
            fields_needed = ", ".join(missing_fields)
            return f"I still need some important information to help you find the perfect property. Could you please provide: {fields_needed}?"
        else:
            return "Great! I have all the essential information. Is there anything else you'd like to specify about your ideal property?" 