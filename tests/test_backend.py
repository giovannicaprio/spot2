import pytest
import requests
import pymongo
import os
from time import sleep

def test_backend_health():
    """Test if the backend is running and responding"""
    # Wait for the backend to start
    sleep(5)
    
    try:
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    except requests.exceptions.ConnectionError:
        pytest.fail("Backend is not running or not accessible")

def test_database_connection():
    """Test if we can connect to MongoDB"""
    try:
        # Get MongoDB connection string from environment or use default
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://admin:password123@localhost:27017/admin?authSource=admin")
        
        # Try to connect to MongoDB
        client = pymongo.MongoClient(mongo_uri)
        
        # Test the connection by getting server info
        server_info = client.server_info()
        
        # Check if we got a valid response
        assert "version" in server_info
        
        # Close the connection
        client.close()
    except pymongo.errors.ConnectionFailure:
        pytest.fail("Could not connect to MongoDB")
    except Exception as e:
        pytest.fail(f"Unexpected error while connecting to MongoDB: {str(e)}") 