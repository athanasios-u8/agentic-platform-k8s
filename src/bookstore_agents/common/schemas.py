from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Book(BaseModel):
    id: int
    title: str
    genre: str
    audience: str
    price: float
    description: str
    published_year: int
    popularity: int
    authors: list[str] = Field(default_factory=list)


class InventoryItem(BaseModel):
    book_id: int
    title: str
    quantity_on_hand: int
    quantity_reserved: int
    available_quantity: int


class Customer(BaseModel):
    id: int
    name: str
    email: str
    loyalty_tier: str
    preferences: list[dict[str, Any]] = Field(default_factory=list)


class Reservation(BaseModel):
    reservation_id: str
    book_id: int
    customer_id: int
    status: Literal["active", "cancelled", "picked_up"]
    pickup_date: date
    approval_id: str | None = None
    created_at: datetime | None = None


class ApprovalRecord(BaseModel):
    approval_id: str
    agent_name: str
    tool_name: str
    arguments: dict[str, Any]
    summary: str
    status: Literal["pending", "approved", "rejected"]
    run_state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
