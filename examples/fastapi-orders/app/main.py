from fastapi import FastAPI

from app.api.orders import router as orders_router

app = FastAPI(title="Shop")
app.include_router(orders_router)
