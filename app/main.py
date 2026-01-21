from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import engine, get_db
from .models import Base, User, Deck, Card, CardSchedule
from .schemas import SignupIn, LoginIn, DeleteAccountIn, DeckCreate, DeckOut, CardCreate, CardOut, CardUpdate
from .security import hash_password, verify_password, create_access_token, decode_access_token


# --- Startup ---

Base.metadata.create_all(bind=engine) # Create tables if they don't exist yet
app = FastAPI()


# --- Auth Dependency ---

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


# --- Routes ---

@app.get("/")
def root():
    return {"message": "spaced repetition backend"}

@app.get("/health")
def health():
    return {"status": "ok"}


# --- User routes ---

@app.post("/signup", status_code=status.HTTP_201_CREATED)
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
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def me(user_id: int = Depends(get_current_user_id)):
    return {"user_id": user_id}

@app.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    payload: DeleteAccountIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify password before deletion
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    db.delete(user)
    db.commit()
    return


# --- Deck routes ---

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


# --- Card routes ---

@app.post("/decks/{deck_id}/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def create_card(
    deck_id: int,
    payload: CardCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 1) Confirm deck exists AND belongs to user
    _deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == user_id)
        .first()
    )
    if not _deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )

    # 2) Create the card linked to that deck
    card = Card(front=payload.front, back=payload.back, deck_id=deck_id)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card

@app.get("/decks/{deck_id}/cards", response_model=list[CardOut])
def list_cards(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 1) Confirm deck exists AND belongs to user
    _deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == user_id)
        .first()
    )
    if not _deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )
    
    cards = (
        db.query(Card)
        .filter(Card.deck_id == deck_id)
        .order_by(Card.id.asc())
        .all()
    )

    return cards

@app.get("/decks/{deck_id}/cards/due", response_model=list[CardOut])
def list_due_cards(
    deck_id: int,
    limit: int = 10,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 1) Confirm deck exists and belongs to user
    deck_exists = (
        db.query(Deck.id)
        .filter(Deck.id == deck_id, Deck.user_id == user_id)
        .first()
    )
    if not deck_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )

    # 2) Fetch due cards for this deck (index-driven)
    cards = (
        db.query(Card)
        .join(CardSchedule, CardSchedule.card_id == Card.id)
        .filter(CardSchedule.deck_id == deck_id)
        .filter(CardSchedule.next_review_at <= func.now())
        .order_by(CardSchedule.next_review_at.asc())
        .limit(limit)
        .all()
    )

    return cards

@app.patch("/cards/{card_id}", response_model=CardOut)
def update_card(
    card_id: int,
    payload: CardUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    
    # Reject empty update payload
    if payload.front is None and payload.back is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )
    
    # Fetch card + enforce ownership by joining through deck
    card = (
        db.query(Card)
        .join(Deck, Card.deck_id == Deck.id)
        .filter(Card.id == card_id, Deck.user_id == user_id)
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    # Apply only fields the client actually sent
    if payload.front is not None:
        card.front = payload.front
    if payload.back is not None:
        card.back = payload.back

    db.commit()
    db.refresh(card)
    return card

@app.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    card = (
        db.query(Card)
        .join(Deck, Card.deck_id == Deck.id)
        .filter(Card.id == card_id, Deck.user_id == user_id)
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    db.delete(card)
    db.commit()
    return