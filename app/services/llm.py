from typing import List, Dict
import openai
from log import logger

def get_llm_response(message: str, conversation_history: List[Dict[str, str]], collected_fields: Dict[str, str] = None) -> str:
    """
    Get a response from the LLM based on the message and conversation history.
    
    Args:
        message (str): The user's message
        conversation_history (List[Dict[str, str]]): List of previous messages
        collected_fields (Dict[str, str]): Dictionary of collected fields
        
    Returns:
        str: The LLM's response
    """
    logger.debug(f"Getting LLM response for message: {message[:50]}...")
    
    # Format the conversation history
    formatted_history = format_conversation_history(conversation_history)
    
    # Build the system message
    system_message = """You are a helpful real estate agent assistant. Your goal is to help users find commercial properties that match their needs.
Please collect the following required information:
- Budget (monthly)
- Total size (in square meters)
- Property type (warehouse, office, store, industrial)
- City

Once you have all required information, you can search for properties. Be friendly and professional."""

    # Add collected fields to system message if available
    if collected_fields:
        system_message += "\n\nInformation collected so far:"
        for field, value in collected_fields.items():
            if field == "budget":
                system_message += f"\n- Budget: ${value}/month"
            elif field == "total_size":
                system_message += f"\n- Total size: {value} m²"
            elif field == "property_type":
                system_message += f"\n- Property type: {value}"
            elif field == "city":
                system_message += f"\n- City: {value}"
            elif field == "additional_requirements":
                system_message += f"\n- Additional requirements: {value}"
        
        # Add guidance based on what's missing
        missing_fields = []
        required_fields = ["budget", "total_size", "property_type", "city"]
        for field in required_fields:
            if field not in collected_fields:
                missing_fields.append(field)
        
        if missing_fields:
            system_message += "\n\nPlease collect the following missing information:"
            for field in missing_fields:
                system_message += f"\n- {field.replace('_', ' ').title()}"
        else:
            system_message += "\n\nAll required information has been collected. You can now search for properties."
    
    # Get response from OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                *formatted_history,
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        # Extract and return the response text
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"LLM response received: {response_text[:50]}...")
        return response_text
        
    except Exception as e:
        logger.error(f"Error getting LLM response: {str(e)}")
        return "I apologize, but I'm having trouble processing your request. Could you please try again?"

def format_conversation_history(conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format the conversation history for the LLM.
    
    Args:
        conversation_history (List[Dict[str, str]]): List of previous messages
        
    Returns:
        List[Dict[str, str]]: Formatted conversation history
    """
    formatted_history = []
    for message in conversation_history:
        if message["role"] in ["user", "assistant"]:
            formatted_history.append({
                "role": message["role"],
                "content": message["content"]
            })
    return formatted_history 