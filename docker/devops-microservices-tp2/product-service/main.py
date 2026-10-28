from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Product Service")

class Product(BaseModel):
    id: int
    name: str
    price: float

products_db = [
    Product(id=1, name="Laptop", price=999.99),
    Product(id=2, name="Mouse", price=29.99),
    Product(id=3, name="Keyboard", price=79.99),
]

@app.get("/health")
def health():
    return {"service": "product-service", "status": "healthy"}

@app.get("/products")
def get_products():
    return products_db

@app.get("/products/{product_id}")
def get_product(product_id: int):
    for product in products_db:
        if product.id == product_id:
            return product
    return {"error": "Product not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
