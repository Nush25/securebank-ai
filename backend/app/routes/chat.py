
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.app.services.rag_service import ask_banking_assistant
from backend.app.core.security import get_current_user

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


@router.post("/chat")
def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = ask_banking_assistant(request.question)

        return {
            **result,
            "user_id": current_user["id"],
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to process your question. Please try again.",
        )
