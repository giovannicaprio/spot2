# Spot2 Real Estate Assistant

A secure, scalable, and user-friendly real estate assistant application that helps users find properties based on their requirements. The application uses AI to collect information about users' real estate needs and stores this information in MongoDB for future reference.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Docker Deployment (Recommended)](#docker-deployment-recommended)
  - [Local Development (Without Docker)](#local-development-without-docker)
  - [Cloud Deployment](#cloud-deployment)
- [Configuration](#configuration)
- [Usage](#usage)
- [Security](#security)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- **AI-Powered Conversation**: Natural language interface for collecting real estate requirements
- **Structured Data Collection**: Automatically extracts and validates property requirements
- **MongoDB Integration**: Stores collected information for future reference
- **Secure Architecture**: Multi-layer security approach to prevent attacks
- **Responsive UI**: Streamlit-based interface that works on all devices
- **API-First Design**: RESTful API with comprehensive documentation

## Architecture

The application follows a modern microservices architecture with three main components:

### 1. Backend API Service (FastAPI)

- **RESTful API**: Clean, documented endpoints
- **Pydantic Models**: Type validation and serialization
- **Security Middleware**: API key validation, rate limiting
- **LLM Integration**: AI-powered conversation handling
- **MongoDB Integration**: Data persistence and retrieval

### 2. Frontend Service (Streamlit)

- **Interactive UI**: Real-time updates and feedback
- **Data Visualization**: Tables and charts for MongoDB data
- **State Management**: Session-based conversation tracking
- **Responsive Design**: Works on all devices

### 3. MongoDB Service

- **Document Storage**: Flexible schema for real estate data
- **Indexing**: Optimized queries for performance
- **Validation**: Schema validation at database level
- **Security**: Secure access control

### Security Architecture

The application implements a multi-layer security approach:

- **API Layer**: API key validation, rate limiting
- **Application Layer**: Input sanitization, field validation
- **Database Layer**: Schema validation, secure queries
- **Network Layer**: CORS, security headers

This architecture ensures:
- **Scalability**: Each service can be scaled independently
- **Maintainability**: Clear separation of concerns
- **Resilience**: Failures in one service don't affect others
- **Security**: Comprehensive protection against attacks

## Prerequisites

- Docker and Docker Compose
- Google Cloud API key (for Gemini LLM)

## Installation

### Docker Deployment (Recommended)

This is the recommended way to run the application as it ensures consistent environments and simplifies setup.

1. Clone the repository:
   ```bash
   git clone https://github.com/giovannicaprio/spot2.git
   cd spot2
   ```

2. Create a `.env` file (see [Configuration](#configuration))

3. Build and run the Docker containers:
   ```bash
   docker-compose up -d build
   ```

4. Access the application:
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development (Without Docker)

This approach is only recommended if you need to modify the code and want faster development cycles.

1. Clone the repository:
   ```bash
   git clone https://github.com/giovannicaprio/spot2.git
   cd spot2
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file (see [Configuration](#configuration))

5. Start MongoDB (using Docker):
   ```bash
   docker-compose up -d mongodb
   ```

6. Run the application:
   ```bash
   # Start the backend
   cd backend
   uvicorn app.main:app --reload
   
   # Start the frontend (in a new terminal)
   cd frontend
   streamlit run streamlit_app.py
   ```

### Cloud Deployment

#### Google Cloud Run

1. Build and push the Docker images:
   ```bash
   # Set your project ID
   export PROJECT_ID=your-project-id
   
   # Build and push the backend image
   docker build -t gcr.io/$PROJECT_ID/spot2-backend -f backend/Dockerfile .
   docker push gcr.io/$PROJECT_ID/spot2-backend
   
   # Build and push the frontend image
   docker build -t gcr.io/$PROJECT_ID/spot2-frontend -f frontend/Dockerfile .
   docker push gcr.io/$PROJECT_ID/spot2-frontend
   ```

2. Deploy to Cloud Run:
   ```bash
   # Deploy the backend
   gcloud run deploy spot2-backend \
     --image gcr.io/$PROJECT_ID/spot2-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   
   # Deploy the frontend
   gcloud run deploy spot2-frontend \
     --image gcr.io/$PROJECT_ID/spot2-frontend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

3. Set up environment variables in Cloud Run:
   ```bash
   gcloud run services update spot2-backend \
     --set-env-vars="MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/spot2,API_KEY=your-api-key,GEMINI_API_KEY=your-gemini-api-key"
   ```

#### MongoDB Atlas

1. Create a MongoDB Atlas account and cluster
2. Set up network access (IP whitelist)
3. Create a database user
4. Get the connection string and update the `.env` file

## Configuration

Create a `.env` file in the root directory with the following variables:

```
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/spot2
MONGODB_DB=spot2

# API Configuration
API_KEY=your-secure-api-key
API_KEY_HEADER=X-API-Key

# LLM Configuration
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-pro

# Security Configuration
MAX_PROMPT_LENGTH=1000
MAX_RESPONSE_LENGTH=5000
MAX_FIELD_LENGTH=100
MAX_HISTORY_LENGTH=20
RATE_LIMIT_WINDOW=3600
MAX_REQUESTS_PER_WINDOW=100

# Frontend Configuration
BACKEND_URL=http://localhost:8000
```

## Usage

1. Open the application in your browser: http://localhost:8501
2. Start a conversation with the real estate assistant
3. Provide information about your real estate requirements
4. View collected information in the sidebar
5. Access stored documents in the MongoDB Documents tab

## Security

The application implements comprehensive security measures:

### Input Validation

- **Pattern Matching**: Regex-based validation for all inputs
- **Field Validation**: Type and range checking for all fields
- **Content Filtering**: Detection of dangerous content
- **Sanitization**: Removal of HTML and control characters

### API Security

- **API Key Authentication**: Required for all API calls
- **Rate Limiting**: Prevents abuse of the API
- **CORS**: Cross-Origin Resource Sharing protection
- **Security Headers**: XSS protection, content security policy

### Database Security

- **Schema Validation**: Ensures data integrity
- **Secure Queries**: Prevents NoSQL injection
- **Access Control**: Role-based access control
- **Encryption**: Data encryption at rest and in transit

## API Documentation

The API documentation is available at http://localhost:8000/docs when running the application locally, or at the deployed URL when running in the cloud.

### Key Endpoints

- `POST /chat`: Process a chat message and return the response
- `GET /health`: Check the health of the API
- `GET /mongodb/collections`: Get available MongoDB collections
- `GET /mongodb/documents/{collection}`: Get documents from a collection

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 