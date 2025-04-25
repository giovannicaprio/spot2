import requests
import json
import time
import logging
import os
from datetime import datetime

# Configuração de logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"simple_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simple_bot")

class SimpleBot:
    def __init__(self, api_url="http://localhost:8000", api_key="12345678901234567890123456789012"):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        self.conversation_history = []
        logger.info(f"Bot inicializado com API URL: {api_url}")
    
    def send_message(self, message: str) -> dict:
        """Envia uma mensagem para a API e retorna a resposta."""
        try:
            logger.info(f"Enviando mensagem: {message}")
            
            response = requests.post(
                f"{self.api_url}/chat",
                headers=self.headers,
                json={
                    "message": message,
                    "conversation_history": self.conversation_history
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Erro ao enviar mensagem. Status code: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                return None
            
            data = response.json()
            logger.info(f"Resposta recebida: {data['response'][:100]}...")
            
            # Atualizar histórico de conversa
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": data["response"]})
            
            return data
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return None
    
    def reset_conversation(self):
        """Reseta a conversa."""
        try:
            logger.info("Resetando conversa")
            requests.post(f"{self.api_url}/reset", headers=self.headers)
            self.conversation_history = []
            logger.info("Conversa resetada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao resetar conversa: {str(e)}")

def main():
    # Inicializar o bot
    bot = SimpleBot()
    
    # Resetar a conversa para começar do zero
    bot.reset_conversation()
    
    # Mensagens para testar a extração de campos
    messages = [
        "Hello, I'm looking for a warehouse to rent",
        "I need a space of at least 60 square meters",
        "My budget is $15,000 per month",
        "I'm looking in Mexico City, preferably in the city center zone",
        "Add that it must have parking lot"

    ]
    
    # Enviar cada mensagem e exibir os campos coletados
    for message in messages:
        print(f"\nUser: {message}")
        response = bot.send_message(message)
        
        if response:
            print(f"Assistant: {response['response']}")
            print(f"Collected fields: {response['collected_fields']}")
            print(f"Conversation complete: {response['is_complete']}")
        else:
            print(f"Error sending message: {message}")
        
        # Aguardar 5 segundos entre as mensagens
        time.sleep(5)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main() 