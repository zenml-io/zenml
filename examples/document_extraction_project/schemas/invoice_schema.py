"""Pydantic schemas for invoice data extraction."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class VendorInfo(BaseModel):
    """Vendor/supplier information."""

    name: Optional[str] = Field(None, description="Vendor or supplier name")
    address: Optional[str] = Field(None, description="Vendor address")
    phone: Optional[str] = Field(None, description="Vendor phone number")
    email: Optional[str] = Field(None, description="Vendor email address")


class InvoiceLineItem(BaseModel):
    """Individual line item on an invoice."""

    description: str = Field(..., description="Item or service description")
    quantity: float = Field(..., description="Quantity of items")
    unit_price: float = Field(..., description="Price per unit")
    total: float = Field(
        ..., description="Total line amount (quantity × unit_price)"
    )


class InvoiceData(BaseModel):
    """Complete invoice data structure."""

    invoice_number: Optional[str] = Field(
        None, description="Invoice number or ID"
    )
    invoice_date: Optional[date] = Field(
        None, description="Date the invoice was issued"
    )
    due_date: Optional[date] = Field(None, description="Payment due date")

    vendor: VendorInfo = Field(
        default_factory=VendorInfo, description="Vendor information"
    )

    line_items: List[InvoiceLineItem] = Field(
        default_factory=list,
        description="List of items or services on the invoice",
    )

    subtotal: Optional[float] = Field(None, description="Subtotal before tax")
    tax_amount: Optional[float] = Field(None, description="Tax amount")
    total_amount: Optional[float] = Field(
        None, description="Final total amount"
    )
    currency: Optional[str] = Field(
        None, description="Currency code (USD, EUR, etc.)"
    )

    # Additional fields
    po_number: Optional[str] = Field(None, description="Purchase order number")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(
        None, description="Additional notes or comments"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {date: lambda v: v.isoformat() if v else None}
