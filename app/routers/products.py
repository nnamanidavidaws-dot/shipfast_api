import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductResponse, ProductListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ProductListResponse)
def list_products(
    skip:     int            = Query(0,    ge=0,   description="Records to skip"),
    limit:    int            = Query(20,   ge=1, le=100, description="Max records to return"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock status"),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of products.
    Optionally filter by `in_stock` status.
    """
    query = db.query(Product)

    if in_stock is not None:
        query = query.filter(Product.in_stock == in_stock)

    total    = query.count()
    products = query.offset(skip).limit(limit).all()

    logger.info("Listed %d / %d products (skip=%d, limit=%d)", len(products), total, skip, limit)
    return {"total": total, "products": products}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Fetch a single product by its ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product.
    SKUs must be unique — returns 409 if the SKU already exists.
    """
    product = Product(**payload.dict())
    db.add(product)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A product with SKU '{payload.sku}' already exists",
        )

    logger.info("Created product id=%d  sku=%s", product.id, product.sku)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductCreate, db: Session = Depends(get_db)):
    """Full update of an existing product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    for field, value in payload.dict().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    logger.info("Updated product id=%d", product_id)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    db.delete(product)
    db.commit()
    logger.info("Deleted product id=%d", product_id)