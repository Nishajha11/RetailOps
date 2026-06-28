"""Pydantic schemas for request validation and response shaping."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---- Products ------------------------------------------------------------
class ProductBase(BaseModel):
    name: str
    category_id: Optional[int] = None
    cost: float = 0.0
    mrp: float = 0.0
    stock: int = 0
    lead_time_days: int = 7
    hsn_code: str = ""
    gst_rate: float = 0.0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    cost: Optional[float] = None
    mrp: Optional[float] = None
    stock: Optional[int] = None
    lead_time_days: Optional[int] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None


class ProductOut(ProductBase):
    id: int
    margin: float = 0.0

    class Config:
        from_attributes = True


# ---- Categories ----------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str
    product_count: int = 0

    class Config:
        from_attributes = True


# ---- Customers -----------------------------------------------------------
class CustomerBase(BaseModel):
    name: str
    address: str = ""
    phone: str = ""
    email: str = ""
    gstin: str = ""


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None


class CustomerOut(CustomerBase):
    id: int

    class Config:
        from_attributes = True


# ---- Expenses ------------------------------------------------------------
class ExpenseCreate(BaseModel):
    category: str = Field("Other", description="Delivery, Salary, Utilities, Rent, Other")
    description: str = ""
    payee: str = ""
    amount: float = Field(gt=0, description="Expense amount; must be positive")
    date: Optional[datetime] = None


class ExpenseOut(BaseModel):
    id: int
    date: datetime
    category: str
    description: str
    payee: str
    amount: float

    class Config:
        from_attributes = True


# ---- Billing -------------------------------------------------------------
class CartItem(BaseModel):
    product_id: int
    qty: int = Field(gt=0, description="Units sold; must be positive")
    price: Optional[float] = Field(None, description="Override unit price; defaults to product MRP")


class InvoiceCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[CartItem]
    discount_pct: float = Field(0.0, ge=0, le=100)
    tax_pct: float = Field(0.0, ge=0, le=100)  # legacy; GST is taken from products
    payment_mode: str = Field("Cash", description="Cash, UPI, Card, Bank, Credit")
    amount_paid: Optional[float] = Field(None, description="Amount received now; None = full for non-credit, 0 for Credit")


class InvoiceLineOut(BaseModel):
    product_id: int
    product_name: str
    hsn_code: str = ""
    qty: int
    unit_price: float
    line_total: float
    gst_rate: float = 0.0
    gst_amount: float = 0.0
    stock_after: int


class InvoiceOut(BaseModel):
    invoice_id: int
    invoice_no: str = ""
    customer_id: Optional[int]
    created_at: datetime
    lines: List[InvoiceLineOut]
    subtotal: float
    discount_pct: float
    cgst: float = 0.0
    sgst: float = 0.0
    tax_total: float = 0.0
    total: float
    payment_mode: str = "Cash"
    amount_paid: float = 0.0
    balance_due: float = 0.0
    status: str = "Paid"


class InvoiceSummary(BaseModel):
    invoice_id: int
    invoice_no: str = ""
    customer_id: Optional[int]
    customer_name: str
    created_at: datetime
    item_count: int
    units: int
    total: float
    amount_paid: float = 0.0
    balance_due: float = 0.0
    status: str = "Paid"
    payment_mode: str = "Cash"


# ---- Analytics -----------------------------------------------------------
class SellerRow(BaseModel):
    product_id: int
    product_name: str
    units_sold: int
    revenue: float


class ForecastPoint(BaseModel):
    period: str
    predicted_units: float
    kind: str  # "history" or "forecast"


# ---- Business profile ----------------------------------------------------
class BusinessProfileIn(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    state: Optional[str] = None


class BusinessProfileOut(BaseModel):
    name: str = "RetailOps"
    address: str = ""
    phone: str = ""
    email: str = ""
    gstin: str = ""
    state: str = ""

    class Config:
        from_attributes = True