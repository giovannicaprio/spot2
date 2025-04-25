#!/bin/bash

# Stop any running containers
docker-compose down

# Remove the network and volume
docker network rm spot2_spot2-network || true
docker volume rm spot2_mongodb_data || true

# Create network and volume
docker network create spot2_spot2-network
docker volume create spot2_mongodb_data

# Build and start the containers
docker-compose build mongodb backend frontend
docker-compose up -d mongodb backend frontend

# Wait for services to start
echo "Aguardando os serviços iniciarem..."
sleep 10

# Run the tests
docker-compose exec backend pytest tests/test_backend.py tests/test_mongodb_collection.py tests/test_chat_mongodb_integration.py -v

# Stop the containers
docker-compose down

# Remove the network
docker network rm spot2_spot2-network 