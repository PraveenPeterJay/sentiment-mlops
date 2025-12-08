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

# --- CONFIGURATION ---
# Database connection string uses the Kubernetes Service Name: 'postgres-service'
DB_HOST = os.getenv("DB_HOST", "postgres-service")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "rotten_potatoes_db")
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# --- DATABASE SETUP (SQLAlchemy) ---
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the database models (Tables)
class Movie(Base):
    """Represents the 'movies' table."""
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(String)

class MovieReview(Base):
    """Represents the 'movie_reviews' table."""
    __tablename__ = "movie_reviews"
    review_id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer)
    review = Column(String)
    # isPos: True for Positive (1), False for Negative (0)
    isPos = Column(Boolean) 

# Dependency to get a new DB session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Schemas for API Request/Response ---

class Review(BaseModel):
    """Schema for the original /predict endpoint (no longer used directly)."""
    text: str

class MovieData(BaseModel):
    """Schema for /movies endpoint response."""
    id: int
    name: str
    description: str

class MovieReviewData(BaseModel):
    """Schema for /reviews/{movie_id} endpoint response."""
    review_id: int
    movie_id: int
    review: str
    isPos: bool

class ReviewInput(BaseModel):
    """Schema for the new /submit_review endpoint."""
    movie_id: int
    text: str

class ScoreResponse(BaseModel):
    """Schema for /score/{movie_id} endpoint response."""
    total_reviews: int
    positive_count: int
    score: float

# --- APP INITIALIZATION & MODEL LOADING ---

app = FastAPI(title="Rotten Potatoes Backend API", 
              description="FastAPI, MLflow, and Persistent DB Integration.")

print("Loading model...")
model = None
latest_run_id = "Unknown"

try:
    # Start searching from the current directory
    search_path = "mlruns"
    model_uri = None
    
    # Walk through every single folder looking for 'model.pkl'
    for root, dirs, files in os.walk(search_path):
        if "model.pkl" in files:
            model_uri = root
            print(f"Found model.pkl at: {model_uri}")
            break
            
    if not model_uri:
        # If model is not found, API will run but predictions will fail
        raise FileNotFoundError("Could not find 'model.pkl' anywhere in mlruns!")

    # Load the model from the folder we found
    model = mlflow.sklearn.load_model(model_uri)
    print("Model loaded successfully!")
    
    # Use the folder name as the version ID for display
    # This assumes a structure like mlruns/X/Y/artifacts/model
    latest_run_id = os.path.basename(os.path.dirname(os.path.dirname(model_uri)))

except Exception as e:
    logging.error(f"CRITICAL ERROR: Could not load model. {e}")
    model = None

# --- DATABASE SEEDING FUNCTION ---
def seed_database(db: Session):
    """
    Creates tables and populates initial data if tables are empty.
    NOTE: This is done inside the container, not on your local machine.
    """
    # 1. Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # 2. Check if the 'movies' table is already populated
    if db.query(Movie).count() > 0:
        print("Database already seeded. Skipping initial data load.")
        return

    print("Database is empty. Populating with initial data...")

    try:
        with open("initial_movies.json", "r") as f:
            initial_movies = json.load(f)
        
        with open("initial_reviews.json", "r") as f:
            initial_reviews_data = json.load(f)
    except FileNotFoundError as e:
        print(f"CRITICAL ERROR: Data file not found. {e}")
        return # Stop seeding if files are missing
    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: Data file has invalid JSON format. {e}")
        return # Stop seeding if JSON is invalid

    # 3. Insert Movies
    movie_objects = []
    for m in initial_movies:
        movie_objects.append(Movie(name=m['name'], description=m['desc']))
    db.add_all(movie_objects)
    db.commit()

    # Create a mapping of movie names to their new IDs for review linking
    movie_name_to_id = {m.name: m.id for m in db.query(Movie).all()}
    
    # 4. Insert Reviews
    review_objects = []
    for name, review_text, is_positive in initial_reviews_data:
        movie_id = movie_name_to_id.get(name)
        if movie_id:
            review_objects.append(MovieReview(
                movie_id=movie_id, 
                review=review_text, 
                isPos=is_positive
            ))
        else:
            print(f"Warning: Review for movie '{name}' skipped (Movie ID not found).")
            
    db.add_all(review_objects)
    db.commit()
    print(f"Database seeding complete. Inserted {len(movie_objects)} movies and {len(review_objects)} reviews.")

# --- LIFECYCLE HOOK: SEED DATABASE ON STARTUP ---

@app.on_event("startup")
async def startup_event():
    """Runs the database seeding when the API starts up."""
    try:
        db = SessionLocal()
        seed_database(db)
    except OperationalError as e:
        # This will catch errors if the Postgres container is not yet ready
        print(f"WARNING: Could not connect to database on startup. Retrying connection later. Error: {e}")
    except Exception as e:
        print(f"FATAL ERROR during startup/seeding: {e}")
    finally:
        if 'db' in locals() and db:
            db.close()

# --- API ENDPOINTS ---

@app.get("/")
def home():
    """Simple check to ensure the API is running."""
    return {"message": "Rotten Potatoes API is running."}

@app.get("/movies", response_model=List[MovieData])
def get_all_movies(db: Session = Depends(get_db)):
    """
    Retrieves the list of all movies from the database for the dropdown.
    """
    movies = db.query(Movie).all()
    # Convert SQLAlchemy objects to Pydantic objects for response
    return [{"id": m.id, "name": m.name, "description": m.description} for m in movies]

@app.get("/score/{movie_id}", response_model=ScoreResponse)
def get_movie_score(movie_id: int, db: Session = Depends(get_db)):
    """
    Calculates and returns the freshness score for a specific movie.
    Freshness = (Positive Reviews / Total Reviews) * 100
    """
    # Use SQLAlchemy to count reviews for the given movie_id
    total_reviews = db.query(MovieReview).filter(MovieReview.movie_id == movie_id).count()
    positive_count = db.query(MovieReview).filter(
        MovieReview.movie_id == movie_id, 
        MovieReview.isPos == True
    ).count()

    if total_reviews == 0:
        score = 0.0
    else:
        score = (positive_count / total_reviews) * 100

    return {
        "total_reviews": total_reviews,
        "positive_count": positive_count,
        "score": round(score, 2)
    }

@app.post("/submit_review")
def submit_and_predict_review(review_input: ReviewInput, db: Session = Depends(get_db)):
    """
    1. Predicts the sentiment of the review.
    2. Saves the review and its sentiment to the database.
    3. Returns the prediction result.
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded. Check server logs.")

    # --- Step 1: Predict Sentiment ---
    try:
        prediction = model.predict([review_input.text])
        # The model should output 'Positive' or 'Negative'
        sentiment = prediction[0]
        # isPos is True if sentiment is 'Positive', False otherwise
        is_positive = sentiment.lower() == "positive"
    except Exception as e:
        logging.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction service failed.")

    # --- Step 2: Save Review to Database ---
    try:
        new_review = MovieReview(
            movie_id=review_input.movie_id,
            review=review_input.text,
            isPos=is_positive
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)
    except Exception as e:
        db.rollback()
        logging.error(f"Database insertion failed: {e}")
        # Note: We still return the prediction even if the save fails, but log the error
        raise HTTPException(status_code=500, detail="Review saved failed but prediction was successful.")

    # --- Step 3: Return Prediction ---
    return {
        "sentiment": sentiment,
        "model_version": latest_run_id,
        "message": "Review submitted and analyzed successfully."
    }

@app.get("/reviews/{movie_id}", response_model=List[MovieReviewData])
def get_reviews(movie_id: int, db: Session = Depends(get_db)):
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
