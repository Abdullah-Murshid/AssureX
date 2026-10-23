"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

CATEGORIES = {"electronics", "appliances", "automotive"}
REGISTERABLE_ROLES = {"customer", "service_center"}


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: Dict[str, Any]


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = "customer"

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def _safe_role(cls, value: str) -> str:
        role = (value or "customer").strip().lower()
        return role if role in REGISTERABLE_ROLES else "customer"


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ProfileUpdateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    phone_number: str = ""
    mailing_address: str = ""

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ProductIn(BaseModel):
    product_name: str = Field(min_length=1, max_length=150)
    category: str = "electronics"
    brand: str = "Generic"
    model_number: str = "N/A"
    serial_number: str = Field(min_length=1, max_length=50)
    purchase_date: str
    purchase_price: float = Field(default=0, ge=0)
    retailer: str = "Unknown"
    warranty_duration_months: int = Field(default=24, ge=1)
    has_extended_warranty: bool = False
    extended_warranty_provider: str = ""
    extended_warranty_contract_number: str = ""
    extended_warranty_duration_months: int = Field(default=0, ge=0)

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str) -> str:
        category = (value or "electronics").strip().lower()
        if category not in CATEGORIES:
            raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
        return category


class PrecheckIn(BaseModel):
    product_id: str
    fault_occurrence_date: str
    claim_submission_date: Optional[str] = None
    fault_category: str = "general_defect"
    damage_type: str = "none"


class DocumentVerifyIn(BaseModel):
    purchase_date: str = ""
    invoice_number: str = ""
    product_name: str = ""
    model_number: str = ""
    serial_number: str = ""
    retailer_name: str = ""
    purchase_amount: str = ""
    warranty_period: str = ""


class RepairIn(BaseModel):
    product_id: str
    repair_date: str
    service_center_name: str = Field(min_length=1, max_length=150)
    replaced_parts: str = ""
    repair_cost: float = Field(default=0, ge=0)
    outcome: str = ""
    authorized: bool = True


class ReviewDecisionIn(BaseModel):
    action: str
    comments: str = Field(min_length=1, max_length=2000)

    @field_validator("action")
    @classmethod
    def _valid_action(cls, value: str) -> str:
        allowed = {"Approved", "Rejected", "Request More Info", "Closed"}
        if value not in allowed:
            raise ValueError(f"action must be one of {sorted(allowed)}")
        return value


class PolicyUpdateIn(BaseModel):
    data: Dict[str, Any]


class SettingsUpdateIn(BaseModel):
    settings: Dict[str, Any]
