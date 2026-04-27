"""
Admin-facing Pydantic schemas for CRUD on game_components, cost_rates,
papers and users.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class GameComponentIn(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    name: str
    category: str = Field(min_length=1, max_length=32)
    unit: str = Field(min_length=1, max_length=32)
    price_uah: Decimal
    notes: Optional[str] = None


class GameComponentOut(GameComponentIn):
    pass


class CostRateIn(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    rate_key: str = Field(min_length=1, max_length=128)
    value_numeric: Decimal
    unit: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None


class CostRateOut(CostRateIn):
    pass


class CostRatePatch(BaseModel):
    value_numeric: Optional[Decimal] = None
    unit: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None


class PaperIn(BaseModel):
    id: str
    name: str
    type: str
    weight_gsm: int
    compatible_with: list[str]
    typical_use: list[str]
    thickness_mm: Optional[Decimal] = None


class PaperOut(PaperIn):
    pass


class UserAdminIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    role: str = Field(default="client", pattern="^(admin|client|expert)$")
    is_active: bool = True


class UserAdminPatch(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=200)
    role: Optional[str] = Field(default=None, pattern="^(admin|client|expert)$")
    is_active: Optional[bool] = None


class UserAdminOut(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LlmRuntimeSettingIn(BaseModel):
    provider: str = Field(pattern="^(openai|anthropic)$")
    model: str = Field(min_length=1, max_length=128)


class LlmRuntimeSettingOut(LlmRuntimeSettingIn):
    setting_key: str
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
