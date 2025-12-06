import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="Sentiment Analysis API", description="MLOps Project Demo")

class Review(BaseModel):
    text: str

# --- UPDATED MODEL LOADING LOGIC (RECURSIVE SEARCH) ---
print("Loading model...")
model = None

try:
    # Start searching from the current directory
    search_path = "mlruns"
    model_uri = None
    
    # Walk through every single folder looking for 'model.pkl'
    for root, dirs, files in os.walk(search_path):
        if "model.pkl" in files:
            # Found it! The model URI is this folder.
            model_uri = root
            print(f"Found model.pkl at: {model_uri}")
            break
            
    if not model_uri:
        raise Exception("Could not find 'model.pkl' anywhere in mlruns!")

    # Load the model from the folder we found
    model = mlflow.sklearn.load_model(model_uri)
    print("Model loaded successfully!")
    
    # Use the folder name as the version ID for display
    latest_run_id = os.path.basename(os.path.dirname(model_uri))

except Exception as e:
    print(f"CRITICAL ERROR: Could not load model. {e}")
    model = None

@app.post("/predict")
def predict_sentiment(review: Review):
    if not model:
        # Return a 500 error if model is missing, don't crash
        return {"error": "Model not loaded. Check server logs."}

    prediction = model.predict([review.text])
    return {"result": prediction[0], "model_version": latest_run_id}

@app.get("/")
def home():
    return {"message": "API is running."}