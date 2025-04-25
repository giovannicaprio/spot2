from fastapi import FastAPI
from app.routes import health, mongodb
from app.api.routes import app as chat_app

app = FastAPI()

# Include health check router
app.include_router(health.router)

# Include MongoDB router
app.include_router(mongodb.router)

# Include chat router
app.include_router(chat_app.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 