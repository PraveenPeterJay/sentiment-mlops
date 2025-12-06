import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, classification_report

# SET EXPERIMENT NAME
mlflow.set_experiment("IMDB_Sentiment_Analysis")

def train():
    with mlflow.start_run():
        # 1. READ DATA (DVC ensures this is the right version)
        print("Reading data...")
        df = pd.read_csv("data/train.csv")

        # The dataset has columns 'review' and 'sentiment'
        # (Note: The downloaded dataset might use 'Review' or 'text', checking header...)
        # We assume columns are 'Review' and 'Sentiment' based on the source link.
        # If the CSV has different headers, print df.columns to check.

        X = df['review'] 
        y = df['sentiment']

        # 2. SPLIT
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 3. DEFINE MODEL (TF-IDF + Logistic Regression is great for text)
        # Log parameters
        mlflow.log_param("vectorizer", "Tfidf")
        mlflow.log_param("model", "LogisticRegression")

        pipe = make_pipeline(TfidfVectorizer(), LogisticRegression())

        # 4. TRAIN
        print("Training...")
        pipe.fit(X_train, y_train)

        # 5. EVALUATE
        preds = pipe.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"Accuracy: {acc}")

        # Log metrics
        mlflow.log_metric("accuracy", acc)

        # 6. REGISTER MODEL
        # This saves the model file into the MLflow system
        mlflow.sklearn.log_model(pipe, "model")
        print("Model saved to MLflow")

if __name__ == "__main__":
    train()