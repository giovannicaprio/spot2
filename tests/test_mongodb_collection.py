import os
import pytest
import uuid
from datetime import datetime
from bson import ObjectId
from app.services.mongodb_service import MongoDBService
from app.models.collected_info import CollectedInfo

# Mock environment variables for testing
os.environ["MONGODB_URI"] = "mongodb://admin:password123@mongodb:27017/admin?authSource=admin"
os.environ["MONGO_DB_NAME"] = "spotify_clone_test"

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
def sample_collected_info():
    """Fixture to create a sample collected info dictionary"""
    return {
        "budget": "500000",
        "total_size": "100",
        "property_type": "apartment",
        "city": "New York",
        "additional_fields": {
            "bedrooms": "2",
            "bathrooms": "1"
        },
        "conversation_id": str(uuid.uuid4())
    }

def test_save_collected_info(mongodb_service, sample_collected_info):
    """Test saving collected information to MongoDB"""
    # Save the collected info
    doc_id = mongodb_service.save_collected_info(sample_collected_info)
    
    # Verify the document was saved
    assert doc_id is not None
    
    # Retrieve the document
    retrieved_doc = mongodb_service.get_collected_info(doc_id)
    
    # Verify the retrieved document matches the original
    assert retrieved_doc is not None
    assert retrieved_doc["budget"] == sample_collected_info["budget"]
    assert retrieved_doc["total_size"] == sample_collected_info["total_size"]
    assert retrieved_doc["property_type"] == sample_collected_info["property_type"]
    assert retrieved_doc["city"] == sample_collected_info["city"]
    assert retrieved_doc["additional_fields"] == sample_collected_info["additional_fields"]
    assert retrieved_doc["conversation_id"] == sample_collected_info["conversation_id"]
    
    # Verify timestamps were added
    assert "created_at" in retrieved_doc
    assert "updated_at" in retrieved_doc
    assert isinstance(retrieved_doc["created_at"], datetime)
    assert isinstance(retrieved_doc["updated_at"], datetime)

def test_update_collected_info(mongodb_service, sample_collected_info):
    """Test updating collected information in MongoDB"""
    # Save the initial collected info
    doc_id = mongodb_service.save_collected_info(sample_collected_info)
    
    # Update the collected info
    updated_info = sample_collected_info.copy()
    updated_info["budget"] = "600000"
    updated_info["additional_fields"]["bedrooms"] = "3"
    
    # Perform the update
    success = mongodb_service.update_collected_info(doc_id, updated_info)
    
    # Verify the update was successful
    assert success is True
    
    # Retrieve the updated document
    retrieved_doc = mongodb_service.get_collected_info(doc_id)
    
    # Verify the retrieved document has the updated values
    assert retrieved_doc["budget"] == "600000"
    assert retrieved_doc["additional_fields"]["bedrooms"] == "3"
    
    # Verify the updated_at timestamp was updated
    assert retrieved_doc["updated_at"] > retrieved_doc["created_at"]

def test_get_collected_info_not_found(mongodb_service):
    """Test retrieving a non-existent document"""
    # Try to retrieve a non-existent document
    non_existent_id = str(ObjectId())
    retrieved_doc = mongodb_service.get_collected_info(non_existent_id)
    
    # Verify the result is None
    assert retrieved_doc is None

def test_collected_info_model():
    """Test the CollectedInfo model"""
    # Create a CollectedInfo instance
    collected_info = CollectedInfo(
        budget="500000",
        total_size="100",
        property_type="apartment",
        city="New York",
        additional_fields={"bedrooms": "2", "bathrooms": "1"},
        conversation_id=str(uuid.uuid4())
    )
    
    # Verify the model has the expected fields
    assert collected_info.budget == "500000"
    assert collected_info.total_size == "100"
    assert collected_info.property_type == "apartment"
    assert collected_info.city == "New York"
    assert collected_info.additional_fields == {"bedrooms": "2", "bathrooms": "1"}
    assert collected_info.conversation_id is not None
    
    # Verify timestamps were automatically set
    assert collected_info.created_at is not None
    assert collected_info.updated_at is not None
    assert isinstance(collected_info.created_at, datetime)
    assert isinstance(collected_info.updated_at, datetime)
    
    # Verify the model can be converted to a dictionary
    collected_info_dict = collected_info.model_dump()
    assert "budget" in collected_info_dict
    assert "total_size" in collected_info_dict
    assert "property_type" in collected_info_dict
    assert "city" in collected_info_dict
    assert "additional_fields" in collected_info_dict
    assert "conversation_id" in collected_info_dict
    assert "created_at" in collected_info_dict
    assert "updated_at" in collected_info_dict 