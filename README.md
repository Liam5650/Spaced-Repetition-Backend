# Spaced Repetition Backend

Backend API for a spaced-repetition flashcard application.

The project focuses on a clean REST design, authentication, and data ownership rules. The service supports users, decks, and cards, and is extended with scheduling and review logic based on the SM-2 algorithm.

## Tech Stack
- **FastAPI** — API framework
- **SQLAlchemy 2.x** — ORM
- **PostgreSQL** — relational database
- **JWT (python-jose)** — authentication
- **Passlib** — password hashing
- **Uvicorn** — ASGI server

## Current Features
- User signup/login with hashed passwords
- JWT-based authentication
- Deck CRUD with per-user ownership
- Card CRUD scoped to decks
- Account deletion with password verification
- Learn cards (creates initial schedule)
- Fetch new cards / due cards
- Review endpoint updates schedule + persists deterministic review history
