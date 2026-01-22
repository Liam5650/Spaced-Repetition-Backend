from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

CARD_FRONT_MIN_LEN = 1
CARD_FRONT_MAX_LEN = 200
CARD_BACK_MIN_LEN = 1
CARD_BACK_MAX_LEN = 2000

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=8, max_length=72)

class DeckCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)

class DeckOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class CardCreate(BaseModel):
    front: str = Field(min_length=CARD_FRONT_MIN_LEN, max_length=CARD_FRONT_MAX_LEN)
    back: str = Field(min_length=CARD_BACK_MIN_LEN, max_length=CARD_BACK_MAX_LEN)

class CardOut(BaseModel):
    id: int
    front: str
    back: str

    model_config = ConfigDict(from_attributes=True)

class CardUpdate(BaseModel):
    front: Optional[str] = Field(default=None, min_length=CARD_FRONT_MIN_LEN, max_length=CARD_FRONT_MAX_LEN)
    back: Optional[str] = Field(default=None, min_length=CARD_BACK_MIN_LEN, max_length=CARD_BACK_MAX_LEN)

class ReviewIn(BaseModel):
    quality: int = Field(..., ge=0, le=5)