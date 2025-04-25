import requests
import json
import time
import random
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

# Configuração de logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"test_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_bot")

class TestBot:
    def __init__(self, api_url="http://localhost:8000", api_key="12345678901234567890123456789012"):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        self.conversation_history = []
        self.collected_fields = {}
        logger.info(f"Bot inicializado com API URL: {api_url}")
    
    def send_message(self, message: str) -> Optional[Dict]:
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
            
            # Atualizar campos coletados
            self.collected_fields = data["collected_fields"]
            
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
            self.collected_fields = {}
            logger.info("Conversa resetada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao resetar conversa: {str(e)}")
    
    def simulate_conversation(self, messages: List[str], delay: float = 5.0):
        """Simula uma conversa enviando uma série de mensagens com um delay entre elas."""
        for i, message in enumerate(messages):
            # Adicionar um delay maior entre as mensagens para evitar atingir o limite de requisições
            if i > 0:
                logger.info(f"Aguardando {delay} segundos antes de enviar a próxima mensagem...")
                time.sleep(delay)
            
            response = self.send_message(message)
            if response:
                print(f"\nUsuário: {message}")
                print(f"Assistente: {response['response']}")
                print(f"Campos coletados: {response['collected_fields']}")
                print(f"Conversa completa: {response['is_complete']}")
            else:
                print(f"\nErro ao enviar mensagem: {message}")
            
            # Adicionar um delay aleatório para simular um usuário real
            time.sleep(1 + random.uniform(0, 2))

def main():
    # Inicializar o bot
    bot = TestBot()
    
    # Simular uma conversa sobre busca de imóveis comerciais/industriais
    messages = [
        "Hello, I'm looking for a warehouse to rent",
        "I need a space of at least 1000 square meters",
        "My budget is $15,000 per month",
        "I'm looking in Guadalajara, preferably in the south zone",
        "The ceiling height must be at least 6 meters",
        "I need a space with an attached office",
        "I want a warehouse in good condition, it doesn't need to be new",
        "I need a space with parking for at least 5 cars",
        "I want a warehouse with three-phase power available"
    ]
    
    # Iniciar a simulação
    print("Starting conversation simulation...")
    bot.simulate_conversation(messages, delay=5.0)  # Aumentando o delay para 5 segundos
    print("\nSimulation completed!")

if __name__ == "__main__":
    main() 