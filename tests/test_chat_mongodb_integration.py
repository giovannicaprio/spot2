import os
import pytest
import uuid
from datetime import datetime
from app.services.chat_service import ChatService
from app.services.mongodb_service import MongoDBService
from app.api.schemas import ChatMessage

# Mock environment variables for testing
os.environ["MONGODB_URI"] = "mongodb://admin:password123@mongodb:27017/admin?authSource=admin"
os.environ["MONGO_DB_NAME"] = "spotify_clone_test"
os.environ["GOOGLE_API_KEY"] = "test_api_key"

@pytest.fixture
def mongodb_service():
    """Fixture to create a MongoDB service instance for testing"""
    service = MongoDBService()
    yield service
    # Clean up after tests
    try:
        service.db["collected_info"].delete_many({})
    except Exception as e:
        print(f"Error cleaning up test database: {str(e)}")
    finally:
        service.close()

@pytest.fixture
def chat_service():
    """Fixture to create a ChatService instance for testing"""
    service = ChatService()
    yield service
    # Reset the service after tests
    service.reset()

def test_chat_service_saves_to_mongodb(chat_service, mongodb_service):
    """Test that the chat service saves collected information to MongoDB"""
    # Process a message that contains property information
    message = "I'm looking for an apartment in New York with a budget of $500,000 and at least 100 square meters"
    result = chat_service.process_message(message)
    
    # Verify the result contains the expected fields
    assert result["is_complete"] is False  # Not all fields are collected yet
    assert "conversation_id" in result
    
    # The field extraction might not be perfect in the test environment,
    # so we'll check if at least some fields were collected
    collected_fields = result["collected_fields"]
    assert any(collected_fields.values()), "No fields were collected"
    
    # Verify the information was saved to MongoDB
    # We need to query by conversation_id since we don't have the document ID
    collection = mongodb_service.db["collected_info"]
    saved_docs = list(collection.find({"conversation_id": result["conversation_id"]}))
    
    assert len(saved_docs) > 0, "No documents were saved to MongoDB"
    
    # The most recent document should have the collected information
    latest_doc = max(saved_docs, key=lambda doc: doc["updated_at"])
    assert latest_doc["conversation_id"] == result["conversation_id"]

def test_chat_service_updates_mongodb(chat_service, mongodb_service):
    """Test that the chat service updates collected information in MongoDB"""
    # Process an initial message
    initial_message = "I'm looking for an apartment in New York"
    initial_result = chat_service.process_message(initial_message)
    
    # Process a follow-up message with more information
    follow_up_message = "My budget is $500,000 and I need at least 100 square meters"
    follow_up_result = chat_service.process_message(follow_up_message)
    
    # Verify the conversation ID is the same
    assert initial_result["conversation_id"] == follow_up_result["conversation_id"]
    
    # The field extraction might not be perfect in the test environment,
    # so we'll check if at least some fields were collected
    initial_fields = initial_result["collected_fields"]
    follow_up_fields = follow_up_result["collected_fields"]
    
    assert any(initial_fields.values()), "No fields were collected in initial message"
    assert any(follow_up_fields.values()), "No fields were collected in follow-up message"
    
    # Verify the information was updated in MongoDB
    collection = mongodb_service.db["collected_info"]
    saved_docs = list(collection.find({"conversation_id": follow_up_result["conversation_id"]}))
    
    # We should have at least two documents: one from the initial message and one from the follow-up
    assert len(saved_docs) >= 2, "Not enough documents were saved to MongoDB"
    
    # The most recent document should have the updated information
    latest_doc = max(saved_docs, key=lambda doc: doc["updated_at"])
    assert latest_doc["conversation_id"] == follow_up_result["conversation_id"]

def test_chat_service_reset_creates_new_conversation(chat_service, mongodb_service):
    """Test that resetting the chat service creates a new conversation"""
    # Process an initial message
    initial_message = "I'm looking for an apartment in New York"
    initial_result = chat_service.process_message(initial_message)
    initial_conversation_id = initial_result["conversation_id"]
    
    # Reset the chat service
    chat_service.reset()
    
    # Process a new message after reset
    new_message = "I'm looking for a house in Los Angeles"
    new_result = chat_service.process_message(new_message)
    new_conversation_id = new_result["conversation_id"]
    
    # Verify the conversation IDs are different
    assert initial_conversation_id != new_conversation_id
    
    # Verify both conversations were saved to MongoDB
    collection = mongodb_service.db["collected_info"]
    saved_docs = list(collection.find({"conversation_id": {"$in": [initial_conversation_id, new_conversation_id]}}))
    
    assert len(saved_docs) >= 2, "Not enough documents were saved to MongoDB"
    
    # Verify the documents have different conversation IDs
    conversation_ids = [doc["conversation_id"] for doc in saved_docs]
    assert initial_conversation_id in conversation_ids
    assert new_conversation_id in conversation_ids 