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
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# --- SMART LOG HANDLER (This logic extracts the tags) ---
class SimpleElasticsearchHandler(logging.Handler):
    def __init__(self, host, port, index):
        super().__init__()
        self.url = f"http://{host}:{port}/{index}/_doc"
        self.headers = {"Content-Type": "application/json"}

    def emit(self, record):
        try:
            # Base Payload
            payload = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(), 
                "logger": record.name
            }
            
            # Add Custom "Extra" Fields (The Important Part)
            standard_attr = ["name", "msg", "args", "levelname", "levelno", "pathname", 
                             "filename", "module", "exc_info", "exc_text", "stack_info", 
                             "lineno", "funcName", "created", "msecs", "relativeCreated", 
                             "thread", "threadName", "processName", "process", "message"]
            
            for key, value in record.__dict__.items():
                if key not in standard_attr and not key.startswith("_"):
                    payload[key] = value

            requests.post(self.url, headers=self.headers, json=payload, timeout=1)
        except Exception:
            pass

# --- LOGGING SETUP ---
log = logging.getLogger("rotten_potatoes_logger")
log.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
log.addHandler(console_handler)

try:
    es_handler = SimpleElasticsearchHandler(host='elasticsearch', port=9200, index='rotten_potatoes_logs')
    log.addHandler(es_handler)
except Exception as e:
    print(f"WARNING: Could not initialize Elasticsearch logging. Error: {e}")

# --- DB SETUP ---
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# --- SCHEMAS ---
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

# --- APP STARTUP ---
app = FastAPI(title="Rotten Potatoes Backend API", description="FastAPI, MLflow, and Persistent DB Integration.")

# NOTE: This log message is different now ("System Startup" vs "Initializing...")
log.info("System Startup", extra={"event_type": "LIFECYCLE", "status": "STARTING"})

model = None
latest_run_id = "Unknown"

try:
    search_path = "ml_model"
    model_uri = None
    for root, dirs, files in os.walk(search_path):
        if "model.pkl" in files:
            model_uri = root
            log.info(f"Model Found", extra={"event_type": "MODEL_LOAD", "path": model_uri})
            break
            
    if not model_uri:
        log.error("Model Missing", extra={"event_type": "MODEL_LOAD", "status": "FAILED"})
    else:
        model = mlflow.sklearn.load_model(model_uri)
        latest_run_id = os.path.basename(os.path.dirname(os.path.dirname(model_uri)))
        log.info("Model Loaded", extra={"event_type": "MODEL_LOAD", "status": "SUCCESS", "version": latest_run_id})

except Exception as e:
    log.error(f"Model Load Error: {e}", extra={"event_type": "MODEL_LOAD", "status": "CRASH"})
    model = None

# --- DB SEEDING ---
def seed_database(db: Session):
    Base.metadata.create_all(bind=engine)
    if db.query(Movie).count() > 0:
        return

    log.info("Seeding Database", extra={"event_type": "DB_SEED", "status": "STARTED"})
    try:
        with open("initial_movies.json", "r") as f:
            initial_movies = json.load(f)
        with open("initial_reviews.json", "r") as f:
            initial_reviews_data = json.load(f)
    except Exception as e:
        log.error("Seeding Failed", extra={"event_type": "DB_SEED", "status": "FAILED", "error": str(e)})
        return

    movie_objects = [Movie(name=m['name'], description=m['desc']) for m in initial_movies]
    db.add_all(movie_objects)
    db.commit()

    movie_name_to_id = {m.name: m.id for m in db.query(Movie).all()}
    review_objects = []
    for name, review_text, is_positive in initial_reviews_data:
        movie_id = movie_name_to_id.get(name)
        if movie_id:
            review_objects.append(MovieReview(movie_id=movie_id, review=review_text, isPos=is_positive))
            
    db.add_all(review_objects)
    db.commit()
    log.info("Seeding Complete", extra={"event_type": "DB_SEED", "status": "SUCCESS", "movies_added": len(movie_objects)})

@app.on_event("startup")
async def startup_event():
    try:
        db = SessionLocal()
        seed_database(db)
    except Exception as e:
        log.error(f"Startup DB Error: {e}")
    finally:
        if 'db' in locals() and db:
            db.close()

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Rotten Potatoes API is running."}

@app.get("/movies", response_model=List[MovieData])
def get_all_movies(db: Session = Depends(get_db)):
    # NOTE: This message is different ("View Movies List" vs "API Request: Fetching...")
    log.info("View Movies List", extra={"event_type": "TRAFFIC", "endpoint": "/movies"})
    movies = db.query(Movie).all()
    return [{"id": m.id, "name": m.name, "description": m.description} for m in movies]

@app.get("/score/{movie_id}", response_model=ScoreResponse)
def get_movie_score(movie_id: int, db: Session = Depends(get_db)):
    
    total_reviews = db.query(MovieReview).filter(MovieReview.movie_id == movie_id).count()
    positive_count = db.query(MovieReview).filter(MovieReview.movie_id == movie_id, MovieReview.isPos == True).count()

    score = 0.0 if total_reviews == 0 else (positive_count / total_reviews) * 100

    log.info("Score Viewed", extra={
        "event_type": "VIEW_SCORE",
        "movie_id": movie_id,
        "score": round(score, 2),
        "total_reviews": total_reviews
    })

    return {"total_reviews": total_reviews, "positive_count": positive_count, "score": round(score, 2)}

@app.post("/submit_review")
def submit_and_predict_review(review_input: ReviewInput, db: Session = Depends(get_db)):
    if not model:
        log.error("Model Error", extra={"event_type": "PREDICTION_ERROR", "reason": "Not Loaded"})
        raise HTTPException(status_code=503, detail="Model not loaded.")

    # 1. Predict
    try:
        prediction = model.predict([review_input.text])
        sentiment = prediction[0]
        is_positive = sentiment.lower() == "positive"
        
        # THIS IS THE MOST IMPORTANT LOG FOR YOUR PIE CHART
        log.info("Prediction Made", extra={
            "event_type": "PREDICTION",
            "movie_id": review_input.movie_id,
            "sentiment": sentiment, 
            "model_version": latest_run_id
        })
        
    except Exception as e:
        log.error(f"Prediction Failed: {e}", extra={"event_type": "PREDICTION_ERROR"})
        raise HTTPException(status_code=500, detail="Prediction service failed.")

    # 2. Save
    try:
        new_review = MovieReview(movie_id=review_input.movie_id, review=review_input.text, isPos=is_positive)
        db.add(new_review)
        db.commit()
        db.refresh(new_review)
        
        log.info("Review Saved", extra={"event_type": "DB_WRITE", "status": "SUCCESS", "review_id": new_review.review_id})
        
    except Exception as e:
        db.rollback()
        log.error(f"Save Failed: {e}", extra={"event_type": "DB_WRITE", "status": "FAILED"})
        raise HTTPException(status_code=500, detail="Review saved failed.")

    return {"sentiment": sentiment, "model_version": latest_run_id, "message": "Success"}

@app.get("/reviews/{movie_id}", response_model=List[MovieReviewData])
def get_reviews(movie_id: int, db: Session = Depends(get_db)):
    log.info("View Reviews", extra={"event_type": "TRAFFIC", "endpoint": "/reviews", "movie_id": movie_id})
    recent_reviews = db.query(MovieReview).filter(MovieReview.movie_id == movie_id).order_by(MovieReview.review_id.desc()).limit(3).all()
    return [{"review_id": r.review_id, "movie_id": r.movie_id, "review": r.review, "isPos": r.isPos} for r in recent_reviews]