import os
import json
import logging
import random
from typing import List, Dict

import mlflow.sklearn
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
import logging
import requests     # Used for the manual Elasticsearch connection
import datetime     # Used for timestamps

# --- CONFIGURATION ---
DB_HOST = os.getenv("DB_HOST", "postgres-service")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "rotten_potatoes_db")
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# --- CUSTOM LOG HANDLER (The Fix for Python 3.12) ---
class SimpleElasticsearchHandler(logging.Handler):
    def __init__(self, host, port, index):
        super().__init__()
        self.url = f"http://{host}:{port}/{index}/_doc"
        self.headers = {"Content-Type": "application/json"}

    def emit(self, record):
        try:
            payload = {
                # Use timezone-aware UTC timestamp to fix Pylance warning
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "level": record.levelname,
                "message": self.format(record),
                "logger": record.name,
                "path": record.pathname,
                "line": record.lineno
            }
            # Fire and forget logging (1s timeout)
            requests.post(self.url, headers=self.headers, json=payload, timeout=1)
        except Exception:
            pass

# --- LOGGING SETUP ---
log = logging.getLogger("rotten_potatoes_logger")
log.setLevel(logging.INFO)

# 1. Console Handler (Standard Output)
console_handler = logging.StreamHandler()
log.addHandler(console_handler)

# 2. Elasticsearch Handler (Our Custom Class)
try:
    es_handler = SimpleElasticsearchHandler(host='elasticsearch', port=9200, index='rotten_potatoes_logs')
    log.addHandler(es_handler)
except Exception as e:
    print(f"WARNING: Could not initialize Elasticsearch logging. Error: {e}")


# --- DATABASE SETUP (SQLAlchemy) ---
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DB MODELS ---
class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(String)

class MovieReview(Base):
    __tablename__ = "movie_reviews"
    review_id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer)
    review = Column(String)
    isPos = Column(Boolean) 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PYDANTIC SCHEMAS ---
class Review(BaseModel):
    text: str

class MovieData(BaseModel):
    id: int
    name: str
    description: str

class MovieReviewData(BaseModel):
    review_id: int
    movie_id: int
    review: str
    isPos: bool

class ReviewInput(BaseModel):
    movie_id: int
    text: str

class ScoreResponse(BaseModel):
    total_reviews: int
    positive_count: int
    score: float

# --- APP INITIALIZATION & MODEL LOADING ---
app = FastAPI(title="Rotten Potatoes Backend API", 
              description="FastAPI, MLflow, and Persistent DB Integration.")

log.info("System Startup: Initializing Rotten Potatoes API...")

model = None
latest_run_id = "Unknown"

try:
    search_path = "mlruns"
    model_uri = None
    for root, dirs, files in os.walk(search_path):
        if "model.pkl" in files:
            model_uri = root
            log.info(f"Model Discovery: Found model.pkl at {model_uri}")
            break
            
    if not model_uri:
        log.error("CRITICAL: Model file not found in mlruns directory.")
        # We don't crash here so the DB can still seed, but predictions will fail
    else:
        model = mlflow.sklearn.load_model(model_uri)
        log.info("Model Loading: Success.")
        latest_run_id = os.path.basename(os.path.dirname(os.path.dirname(model_uri)))

except Exception as e:
    log.error(f"CRITICAL ERROR: Could not load model. Reason: {e}")
    model = None

# --- DATABASE SEEDING ---
def seed_database(db: Session):
    Base.metadata.create_all(bind=engine)
    if db.query(Movie).count() > 0:
        log.info("Database Check: Data exists. Skipping seeding.")
        return

    log.info("Database Check: Empty. Starting seeding process...")
    try:
        with open("initial_movies.json", "r") as f:
            initial_movies = json.load(f)
        with open("initial_reviews.json", "r") as f:
            initial_reviews_data = json.load(f)
    except Exception as e:
        log.error(f"Seeding Failed: Could not read JSON files. {e}")
        return

    movie_objects = []
    for m in initial_movies:
        movie_objects.append(Movie(name=m['name'], description=m['desc']))
    db.add_all(movie_objects)
    db.commit()

    movie_name_to_id = {m.name: m.id for m in db.query(Movie).all()}
    
    review_objects = []
    for name, review_text, is_positive in initial_reviews_data:
        movie_id = movie_name_to_id.get(name)
        if movie_id:
            review_objects.append(MovieReview(
                movie_id=movie_id, 
                review=review_text, 
                isPos=is_positive
            ))
            
    db.add_all(review_objects)
    db.commit()
    log.info(f"Seeding Complete: Inserted {len(movie_objects)} movies and {len(review_objects)} reviews.")

@app.on_event("startup")
async def startup_event():
    try:
        db = SessionLocal()
        seed_database(db)
    except Exception as e:
        log.error(f"Startup Error: Database connection failed. {e}")
    finally:
        if 'db' in locals() and db:
            db.close()

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Rotten Potatoes API is running."}

@app.get("/movies", response_model=List[MovieData])
def get_all_movies(db: Session = Depends(get_db)):
    log.info("API Request: Fetching all movies.")
    movies = db.query(Movie).all()
    return [{"id": m.id, "name": m.name, "description": m.description} for m in movies]

@app.get("/score/{movie_id}", response_model=ScoreResponse)
def get_movie_score(movie_id: int, db: Session = Depends(get_db)):
    # Log this action for ELK
    log.info(f"API Request: Calculating score for Movie ID {movie_id}")
    
    total_reviews = db.query(MovieReview).filter(MovieReview.movie_id == movie_id).count()
    positive_count = db.query(MovieReview).filter(
        MovieReview.movie_id == movie_id, 
        MovieReview.isPos == True
    ).count()

    if total_reviews == 0:
        score = 0.0
    else:
        score = (positive_count / total_reviews) * 100

    log.info(f"Score Result: Movie {movie_id} is {score:.2f}% fresh.")
    return {
        "total_reviews": total_reviews,
        "positive_count": positive_count,
        "score": round(score, 2)
    }

@app.post("/submit_review")
def submit_and_predict_review(review_input: ReviewInput, db: Session = Depends(get_db)):
    if not model:
        log.error("Prediction Attempt Failed: Model not loaded.")
        raise HTTPException(status_code=503, detail="Model not loaded.")

    # 1. Predict
    try:
        log.info(f"Processing Review for Movie {review_input.movie_id}...")
        prediction = model.predict([review_input.text])
        sentiment = prediction[0]
        is_positive = sentiment.lower() == "positive"
        log.info(f"AI Prediction: '{sentiment}'")
    except Exception as e:
        log.error(f"AI Failure: {e}")
        raise HTTPException(status_code=500, detail="Prediction service failed.")

    # 2. Save
    try:
        new_review = MovieReview(
            movie_id=review_input.movie_id,
            review=review_input.text,
            isPos=is_positive
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)
        log.info(f"Database Success: Saved review ID {new_review.review_id}")
    except Exception as e:
        db.rollback()
        log.error(f"Database Failure: {e}")
        raise HTTPException(status_code=500, detail="Review saved failed.")

    return {
        "sentiment": sentiment,
        "model_version": latest_run_id,
        "message": "Success"
    }

@app.get("/reviews/{movie_id}", response_model=List[MovieReviewData])
def get_reviews(movie_id: int, db: Session = Depends(get_db)):
    log.info(f"API Request: Fetching recent reviews for Movie {movie_id}")
    recent_reviews = (
        db.query(MovieReview)
          .filter(MovieReview.movie_id == movie_id)
          .order_by(MovieReview.review_id.desc())
          .limit(3)
          .all()
    )
    return [
        {"review_id": r.review_id, "movie_id": r.movie_id, "review": r.review, "isPos": r.isPos}
        for r in recent_reviews
    ]