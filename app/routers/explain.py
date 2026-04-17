from fastapi import APIRouter
from pydantic import BaseModel
from app.services.explanation import explain_price_change

router = APIRouter()

class ExplainRequest(BaseModel):
    reason: str
    tone: str = "friendly"  # 기본값은 친근한 톤

@router.post("/explain_price_change")
def explain(req: ExplainRequest):
    message = explain_price_change(req.reason, req.tone)
    return {"reason": req.reason, "message": message}