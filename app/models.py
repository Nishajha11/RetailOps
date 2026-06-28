"""Relational schema.

The design is a small star schema around `Sale`:

    Category 1──* Product *──* Sale *──1 Customer
                     │
                  Invoice 1──* Sale

`Product.stock` is the single source of truth for on-hand inventory and is
decremented inside the billing transaction so the number is always live.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, func,
)
from sqlalchemy.orm import relationship

from .database import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    cost = Column(Float, nullable=False, default=0.0)      # rate (cost to us)
    mrp = Column(Float, nullable=False, default=0.0)       # printed/sell price
    stock = Column(Integer, nullable=False, default=0)     # live on-hand qty
    lead_time_days = Column(Integer, nullable=False, default=7)
    hsn_code = Column(String, default="")                  # HSN/SAC for GST
    gst_rate = Column(Float, nullable=False, default=0.0)  # GST % applied on sale

    category = relationship("Category", back_populates="products")
    sales = relationship("Sale", back_populates="product")

    @property
    def margin(self) -> float:
        return round(self.mrp - self.cost, 2)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    gstin = Column(String, default="")                     # customer GST number
    sales = relationship("Sale", back_populates="customer")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_no = Column(String, index=True, default="")    # human number, e.g. INV-0007
    customer_id = Column(Integer, ForeignKey("customers.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    subtotal = Column(Float, default=0.0)                  # taxable value before discount
    discount_pct = Column(Float, default=0.0)
    tax_pct = Column(Float, default=0.0)                   # legacy / unused with GST
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    tax_total = Column(Float, default=0.0)                 # cgst + sgst
    total = Column(Float, default=0.0)                     # grand total payable
    payment_mode = Column(String, default="Cash")          # Cash, UPI, Card, Bank, Credit
    amount_paid = Column(Float, default=0.0)
    balance_due = Column(Float, default=0.0)
    status = Column(String, default="Paid")                # Paid, Partial, Unpaid

    customer = relationship("Customer")
    items = relationship("Sale", back_populates="invoice")


class BusinessProfile(Base):
    """Single-row table holding the shop's identity for invoice headers."""
    __tablename__ = "business_profile"
    id = Column(Integer, primary_key=True)
    name = Column(String, default="RetailOps")
    address = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    gstin = Column(String, default="")
    state = Column(String, default="")


class Expense(Base):
    """External operating expense (not cost of goods).

    Captures money that leaves the business outside of inventory purchasing --
    delivery charges, staff salaries, electricity/utility bills, rent, etc. Used
    to turn gross profit (revenue - COGS) into a true net profit.
    """
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    category = Column(String, nullable=False, default="Other")  # Delivery, Salary, Utilities, Rent, Other
    description = Column(String, default="")
    payee = Column(String, default="")
    amount = Column(Float, nullable=False, default=0.0)


class Sale(Base):
    """A single line item. Doubles as the historical sales fact table."""
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    qty = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)            # price charged
    line_total = Column(Float, nullable=False, default=0.0)

    product = relationship("Product", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    invoice = relationship("Invoice", back_populates="items")