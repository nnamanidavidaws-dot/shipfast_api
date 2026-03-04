from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class ProductCreate(BaseModel):
    name: str           = Field(..., min_length=1, max_length=255, example="Blue Sneakers")
    description: Optional[str] = Field(None, max_length=1000, example="Lightweight running shoes")
    price: float        = Field(..., gt=0, example=49.99)
    sku: str            = Field(..., min_length=1, max_length=100, example="SHOE-BLUE-42")
    in_stock: bool      = Field(True, example=True)

    @validator("price")
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return round(v, 2)


class ProductResponse(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    price:       float
    sku:         str
    in_stock:    bool
    created_at:  datetime
    updated_at:  datetime

    class Config:
        orm_mode = True


class ProductListResponse(BaseModel):
    total:    int
    products: list[ProductResponse]