from fastapi import FastAPI
from app.routers import predict, explain

app = FastAPI()
app.include_router(predict.router)
app.include_router(explain.router)