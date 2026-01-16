from fastapi import FastAPI
from .database import engine
from .models import Base

# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "spaced repetition backend"}

@app.get("/health")
def health():
    return {"status": "ok"}