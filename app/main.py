from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from .database import engine, get_db
from .models import Base, User, Deck
from .schemas import SignupIn, LoginIn, DeckCreate, DeckOut
from .security import hash_password, verify_password, create_access_token, decode_access_token

from typing import cast


# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI()

bearer_scheme = HTTPBearer()

def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> int:
    token = creds.credentials
    try:
        return decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

@app.get("/")
def root():
    return {"message": "spaced repetition backend"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/signup", status_code=201)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email}

@app.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user_id: int = cast(int, user.id)
    token = create_access_token(user_id)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def me(user_id: int = Depends(get_current_user_id)):
    return {"user_id": user_id}

@app.post("/decks", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def create_deck(
    payload: DeckCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    deck = Deck(name=payload.name, user_id=user_id)
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck

@app.get("/decks", response_model=list[DeckOut])
def list_decks(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    decks = (
        db.query(Deck)
        .filter(Deck.user_id == user_id)
        .order_by(Deck.id.asc())
        .all()
    )
    return decks

@app.get("/decks/{deck_id}", response_model=DeckOut)
def get_deck(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == user_id)
        .first()
    )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )

    return deck

@app.delete("/decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == user_id)
        .first()
    )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )

    db.delete(deck)
    db.commit()
    return