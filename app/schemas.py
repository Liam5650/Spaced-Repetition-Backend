from pydantic import BaseModel, EmailStr, Field

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class DeckCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)

class DeckOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True