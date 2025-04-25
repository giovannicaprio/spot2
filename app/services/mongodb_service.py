import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId

# Configurar o logger
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"mongodb_service_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mongodb_service")

class MongoDBService:
    def __init__(self):
        logger.info("Inicializando MongoDBService")
        self.client = None
        self.db = None
        self.connect()
        logger.info("MongoDBService initialized successfully")
    
    def connect(self):
        """Estabelece conexão com o MongoDB"""
        try:
            # Obter a URI do MongoDB do ambiente ou usar o valor padrão
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://admin:password123@mongodb:27017/admin?authSource=admin")
            logger.info(f"Conectando ao MongoDB: {mongo_uri}")
            
            # Criar cliente MongoDB
            self.client = MongoClient(mongo_uri)
            
            # Obter o banco de dados
            db_name = os.getenv("MONGO_DB_NAME", "spotify_clone")
            self.db = self.client[db_name]
            
            # Verificar a conexão
            self.client.server_info()
            logger.info(f"Conexão estabelecida com o banco de dados: {db_name}")
        except Exception as e:
            logger.error(f"Erro ao conectar ao MongoDB: {str(e)}")
            raise
    
    def get_all_collections(self) -> List[str]:
        """Retorna a lista de todas as coleções no banco de dados"""
        try:
            collections = self.db.list_collection_names()
            logger.info(f"Coleções encontradas: {collections}")
            return collections
        except Exception as e:
            logger.error(f"Erro ao listar coleções: {str(e)}")
            raise
    
    def get_all_documents(self, collection_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna todos os documentos de uma coleção específica"""
        try:
            collection = self.db[collection_name]
            documents = list(collection.find().limit(limit))
            
            # Converter ObjectId para string para serialização JSON
            for doc in documents:
                doc["_id"] = str(doc["_id"])
            
            logger.info(f"Documentos encontrados na coleção {collection_name}: {len(documents)}")
            return documents
        except Exception as e:
            logger.error(f"Erro ao buscar documentos da coleção {collection_name}: {str(e)}")
            raise
    
    def get_document_count(self, collection_name: str) -> int:
        """Retorna o número total de documentos em uma coleção"""
        try:
            count = self.db[collection_name].count_documents({})
            logger.info(f"Total de documentos na coleção {collection_name}: {count}")
            return count
        except Exception as e:
            logger.error(f"Erro ao contar documentos da coleção {collection_name}: {str(e)}")
            raise
    
    def save_collected_info(self, collected_info: Dict[str, Any]) -> str:
        """
        Salva as informações coletadas na coleção 'collected_info'.
        
        Args:
            collected_info (Dict[str, Any]): Dicionário com as informações coletadas
            
        Returns:
            str: ID do documento salvo
        """
        try:
            collection = self.db["collected_info"]
            
            # Adicionar timestamps
            collected_info["created_at"] = datetime.utcnow()
            collected_info["updated_at"] = datetime.utcnow()
            
            # Inserir documento
            result = collection.insert_one(collected_info)
            logger.info(f"Informações coletadas salvas com ID: {result.inserted_id}")
            
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Erro ao salvar informações coletadas: {str(e)}")
            raise
    
    def update_collected_info(self, doc_id: str, collected_info: Dict[str, Any]) -> bool:
        """
        Update collected information in MongoDB.
        
        Args:
            doc_id (str): The document ID to update
            collected_info (Dict[str, Any]): The updated collected information
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            # Add updated_at timestamp
            collected_info["updated_at"] = datetime.now()
            
            # Update the document
            result = self.db["collected_info"].update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": collected_info}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating collected info: {str(e)}")
            return False
    
    def get_collected_info(self, doc_id: str) -> Dict[str, Any]:
        """
        Recupera as informações coletadas por ID.
        
        Args:
            doc_id (str): ID do documento a ser recuperado
            
        Returns:
            Dict[str, Any]: Documento com as informações coletadas
        """
        try:
            collection = self.db["collected_info"]
            document = collection.find_one({"_id": ObjectId(doc_id)})
            
            if document:
                document["_id"] = str(document["_id"])
                logger.info(f"Informações coletadas recuperadas com sucesso: {doc_id}")
                return document
            else:
                logger.warning(f"Documento não encontrado: {doc_id}")
                return None
        except Exception as e:
            logger.error(f"Erro ao recuperar informações coletadas: {str(e)}")
            raise
    
    def close(self):
        """Fecha a conexão com o MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Conexão com o MongoDB fechada") 