from fastapi import APIRouter
from pydantic import BaseModel
from app.services.prediction import predict_week_logic

router = APIRouter()

class PredictRequest(BaseModel):
    keyword: str
    price: float
    good_id: str

@router.post("/predict_week")
def predict_week(req: PredictRequest):
    return predict_week_logic(req.keyword, req.price, req.good_id)