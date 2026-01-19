"""FastAPI application for E-commerce API."""
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import SessionLocal
from . import models
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal


app = FastAPI(
    title="E-commerce API",
    description="RESTful API for managing products, orders, and sales analytics",
    version="1.0.0"
)

# Constants
HTTP_404_NOT_FOUND = status.HTTP_404_NOT_FOUND
HTTP_201_CREATED = status.HTTP_201_CREATED

# Pydantic Models for Response
class ProductOut(BaseModel):
    """Product response model."""
    id: int
    name: str
    price: Decimal
    category_id: Optional[int] = None
    description: Optional[str] = None
    image: Optional[str] = None
    is_sale: bool = False
    sale_price: Decimal = Decimal('0.00')

    class Config:
        from_attributes = True


class PaymentOrderOut(BaseModel):
    """Payment order response model."""
    id: int
    user_id: Optional[int] = None
    full_name: str
    email: str
    shipping_address: str
    amount_paid: Decimal
    date_oredered: Optional[datetime] = None
    shipped: bool = False
    date_shipped: Optional[datetime] = None

    class Config:
        from_attributes = True


def get_db() -> Session:
    """
    Database dependency for FastAPI routes.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        dict: Status of the API
    """
    return {"status": "ok"}

@app.get("/")
def read_root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message
    """
    return {"message": "Hello World"}


@app.get("/items", response_model=List[ProductOut])
def get_items(db: Session = Depends(get_db)) -> List[ProductOut]:
    """
    Get all products.
    
    Args:
        db: Database session
        
    Returns:
        List[Product]: List of all products
    """
    return db.query(models.Product).all()


@app.get("/items/{item_id}", response_model=ProductOut)
def get_item(item_id: int, db: Session = Depends(get_db)) -> ProductOut:
    """
    Get a specific product by ID.
    
    Args:
        item_id: Product ID
        db: Database session
        
    Returns:
        Product: Product details
        
    Raises:
        HTTPException: 404 if product not found
    """
    item = db.query(models.Product).filter(models.Product.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item

def _calculate_revenue(
    product_id: int,
    product_name: str,
    total_revenue: Optional[Decimal]
) -> dict[str, float | int | str]:
    """
    Calculate and format revenue data for a product.
    
    Args:
        product_id: Product ID
        product_name: Product name
        total_revenue: Total revenue (can be None)
        
    Returns:
        dict: Formatted revenue data
    """
    return {
        "product_id": product_id,
        "product_name": product_name,
        "total_revenue": float(total_revenue) if total_revenue is not None else 0.0,
    }


@app.get("/ecom/totalrevenue")
def get_total_revenue_per_product(
    db: Session = Depends(get_db)
) -> List[dict[str, float | int | str]]:
    """
    Get total revenue per product.
    
    Args:
        db: Database session
        
    Returns:
        List[dict]: Revenue data for each product
    """
    results = (
        db.query(
            models.Product.id.label("product_id"),
            models.Product.name.label("product_name"),
            func.sum(models.OrderItem.price * models.OrderItem.quantity).label("total_revenue"),
        )
        .join(models.OrderItem, models.OrderItem.product_id == models.Product.id)
        .group_by(models.Product.id, models.Product.name)
        .all()
    )

    return [
        _calculate_revenue(r.product_id, r.product_name, r.total_revenue)
        for r in results
    ]


@app.get("/ecom/highest_selling")
def get_highest_selling_product(
    db: Session = Depends(get_db)
) -> dict[str, float | int | str]:
    """
    Get the highest-selling product by quantity.
    
    Args:
        db: Database session
        
    Returns:
        dict: Product with highest sales data
        
    Raises:
        HTTPException: 404 if no sales data available
    """
    result = (
        db.query(
            models.Product.id.label("product_id"),
            models.Product.name.label("product_name"),
            func.sum(models.OrderItem.quantity).label("total_quantity"),
            func.sum(models.OrderItem.price * models.OrderItem.quantity).label("total_revenue"),
        )
        .join(models.OrderItem, models.OrderItem.product_id == models.Product.id)
        .group_by(models.Product.id, models.Product.name)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="No sales data available"
        )

    return {
        "product_id": result.product_id,
        "product_name": result.product_name,
        "total_quantity": int(result.total_quantity) if result.total_quantity is not None else 0,
        "total_revenue": float(result.total_revenue) if result.total_revenue is not None else 0.0,
    }


@app.get("/sales", response_model=List[PaymentOrderOut])
def get_sales(db: Session = Depends(get_db)) -> List[PaymentOrderOut]:
    """
    Get all sales transactions (orders).
    
    Args:
        db: Database session
        
    Returns:
        List[PaymentOrder]: List of all orders
    """
    return db.query(models.PaymentOrder).all()


# Pydantic Models for Request/Response
class OrderItemIn(BaseModel):
    """Order item input model."""
    product_id: int = Field(..., gt=0, description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    price: Decimal = Field(..., gt=0, description="Price per item")


class OrderIn(BaseModel):
    """Order input model."""
    user_id: Optional[int] = Field(None, description="User ID (optional)")
    full_name: str = Field(..., min_length=1, max_length=250, description="Customer full name")
    email: str = Field(..., description="Customer email address")
    shipping_address: str = Field(..., min_length=1, description="Shipping address")
    amount_paid: Decimal = Field(..., gt=0, description="Total amount paid")
    items: List[OrderItemIn] = Field(default_factory=list, description="Order items")


@app.post("/orders")
def add_order(order: OrderIn, db: Session = Depends(get_db)):
    new_order = models.PaymentOrder(
        user_id=order.user_id,
        full_name=order.full_name,
        email=order.email,
        shipping_address=order.shipping_address,
        amount_paid=order.amount_paid
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Add order items
    for item in order.items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            user_id=order.user_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(order_item)
    db.commit()

    return {"message": "Order created", "order_id": new_order.id}


# ============================================================
# PUT API: Update an order (quantity, status)
# ============================================================
class UpdateOrderItemIn(BaseModel):
    product_id: int
    quantity: Optional[int] = None
    price: Optional[Decimal] = None


class UpdateOrderIn(BaseModel):
    shipped: Optional[bool] = None
    date_shipped: Optional[datetime] = None
    items: Optional[List[UpdateOrderItemIn]] = None


@app.put("/orders/{order_id}")
def update_order(order_id: int, update_data: UpdateOrderIn, db: Session = Depends(get_db)):
    order = db.query(models.PaymentOrder).filter(models.PaymentOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update status fields
    if update_data.shipped is not None:
        order.shipped = update_data.shipped
    if update_data.date_shipped is not None:
        order.date_shipped = update_data.date_shipped
    # Auto-set date_shipped when shipped flips to True and not provided
    if order.shipped and order.date_shipped is None:
        order.date_shipped = datetime.utcnow()

    # Update quantities in OrderItem
    if update_data.items is not None:
        for item in update_data.items:
            order_item = db.query(models.OrderItem).filter(
                models.OrderItem.order_id == order_id,
                models.OrderItem.product_id == item.product_id
            ).first()
            if order_item:
                if item.quantity is not None:
                    order_item.quantity = item.quantity
                if item.price is not None:
                    order_item.price = item.price

    db.commit()
    db.refresh(order)
    return {"message": "Order updated", "order": order}


# ============================================================
# DELETE API: Delete an order
# ============================================================
@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PaymentOrder).filter(models.PaymentOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully"}
# Seed endpoint removed per requirement

