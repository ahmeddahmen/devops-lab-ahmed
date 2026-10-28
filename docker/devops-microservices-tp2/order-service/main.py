from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

app = FastAPI(title="Order Service")

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001")

class Order(BaseModel):
    order_id: int
    product_id: int
    quantity: int
    product_name: str
    total: float

orders_db = []
order_counter = 0

@app.get("/health")
def health():
    return {"service": "order-service", "status": "healthy"}

@app.get("/orders")
def get_orders():
    return orders_db

@app.post("/orders")
async def create_order(product_id: int, quantity: int):
    global order_counter

    # Call Product Service to get product details
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Product not found")
            product = response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to product service: {str(e)}")

    order_counter += 1
    total = product["price"] * quantity

    order = Order(
        order_id=order_counter,
        product_id=product_id,
        quantity=quantity,
        product_name=product["name"],
        total=total
    )
    orders_db.append(order)

    return order

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
