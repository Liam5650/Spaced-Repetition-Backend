from .config import ENV
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import engine, get_db
from .models import Base, User, Deck, Card, CardSchedule, ReviewHistory
from .schemas import SignupIn, LoginIn, DeleteAccountIn, DeckCreate, DeckOut, CardCreate, CardOut, CardUpdate, ReviewIn
from .security import hash_password, verify_password, create_access_token, decode_access_token
from .sm2 import sm2_update

from fastapi.staticfiles import StaticFiles
from pathlib import Path


# --- Startup ---

# Drop and recreate all tables if in the dev environment
if ENV == "dev":
    Base.metadata.drop_all(bind=engine)

Base.metadata.create_all(bind=engine)
    
app = FastAPI()
app.mount("/ui", StaticFiles(directory=str(Path(__file__).resolve().parent / "static"), html=True), name="ui")


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
    # Confirm deck exists AND belongs to user
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

    # Create the card linked to that deck
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
    # Confirm deck exists AND belongs to user
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

@app.get("/decks/{deck_id}/cards/new", response_model=CardOut)
def get_new_card(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
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

    card = (
        db.query(Card)
        .filter(Card.deck_id == deck_id)
        .filter(Card.is_learned == False)
        .order_by(Card.id.asc())
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No new cards",
        )

    return card

@app.get("/decks/{deck_id}/cards/due", response_model=CardOut)
def get_due_card(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Confirm deck exists and belongs to user
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

    # Fetch first due card for this deck (index-driven)
    card = (
        db.query(Card)
        .join(CardSchedule, CardSchedule.card_id == Card.id)
        .filter(CardSchedule.deck_id == deck_id)
        .filter(CardSchedule.next_review_at <= func.now())
        .order_by(CardSchedule.next_review_at.asc())
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No due cards",
        )

    return card

@app.post("/cards/{card_id}/learn", status_code=status.HTTP_201_CREATED)
def learn_card(
    card_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Fetch card + enforce ownership via deck. Lock card to prevent race
    # condition where two requests may pass the is_learned check, and both
    # try to create the schedule.
    card = (
        db.query(Card)
        .join(Deck, Card.deck_id == Deck.id)
        .filter(Card.id == card_id, Deck.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    # Reject if already learned
    if card.is_learned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Card is already learned",
        )

    # Create initial schedule (due immediately)
    schedule = CardSchedule(
        card_id=card.id,
        deck_id=card.deck_id,
        repetition_count=0,
        interval_days=0,
        ease_factor=2.5,
        next_review_at=func.now(),
        last_reviewed_at=None,
    )

    card.is_learned = True
    db.add(schedule)
    db.commit()
    return

@app.post("/cards/{card_id}/review")
def review_card(
    card_id: int,
    payload: ReviewIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Fetch card schedule + enforce ownership via deck. Lock schedule to ensure
    # one review will always map to one history being created (race condition)
    result = (
        db.query(CardSchedule, func.now())
        .join(Card, CardSchedule.card_id == Card.id)
        .join(Deck, Card.deck_id == Deck.id)
        .filter(Card.id == card_id, Deck.user_id == user_id)
        .with_for_update(of=CardSchedule)
        .first()
        )
    if not result:
        # We don't know if the card ID is wrong OR if the card is just not learned yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found or not learned."
        )

    # Unpack the tuple: (CardSchedule object, datetime object)
    schedule, db_now = result
    
    # If a previous request just completed and the schedule is now unlocked, 
    # another race condition is possible where the schedule could accidentally get 
    # updated (reviewed) twice. Ensure the card is actually still due. 
    if schedule.next_review_at > db_now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Card was already reviewed and is no longer due."
        )
    
    # Get current schedule values
    repetition_before = schedule.repetition_count
    interval_before = schedule.interval_days
    ease_before = schedule.ease_factor
    timestamp = db_now

    # Unpack payload
    quality = payload.quality
    
    # Get new values from sm-2 algo
    updated_vals = sm2_update(
        repetition_before,
        interval_before,
        ease_before,
        quality,
        timestamp,
    )

    # Update to new card schedule values
    schedule.repetition_count = updated_vals["repetition_count"]
    schedule.interval_days = updated_vals["interval_days"]
    schedule.ease_factor = updated_vals["ease_factor"]
    schedule.next_review_at = updated_vals["next_review_at"]
    schedule.last_reviewed_at = timestamp

    # Create history for the review
    history = ReviewHistory(
        card_id=card_id,
        reviewed_at=timestamp,
        quality=quality,
        repetition_before=repetition_before,
        interval_before=interval_before,
        ease_before=ease_before,
        repetition_after=schedule.repetition_count,
        interval_after=schedule.interval_days,
        ease_after=schedule.ease_factor,
        next_review_at_after=schedule.next_review_at,
    )
    
    db.add(history)
    db.commit()
    return

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