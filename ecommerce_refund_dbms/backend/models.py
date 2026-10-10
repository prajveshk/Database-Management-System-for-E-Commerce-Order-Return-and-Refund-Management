from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    customer_id: Optional[int] = None

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

class ReturnItemCreate(BaseModel):
    order_item_id: int
    quantity: int = Field(..., gt=0)

class ReturnCreate(BaseModel):
    order_id: int
    reason: str = Field(..., max_length=120)
    items: List[ReturnItemCreate]

class InspectionCreate(BaseModel):
    condition_status: str = Field(..., description="GOOD, DAMAGED, or DEFECTIVE")
    notes: Optional[str] = None
