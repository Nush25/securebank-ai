
from fastapi import FastAPI

from backend.app.routes.chat import router as chat_router
from backend.app.routes.auth import router as auth_router

app = FastAPI(
    title="Secure Banking Assistant",
    description="A local AI-powered banking policy assistant",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to Secure Banking Assistant!",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(chat_router)
app.include_router(auth_router)
