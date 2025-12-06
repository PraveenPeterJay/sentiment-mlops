import streamlit as st
import requests
import json
import os
# 1. PAGE CONFIGURATION
# Set the title and icon of the tab in the browser
st.set_page_config(page_title="Sentiment Analyzer", page_icon="🎬")

# 2. TITLE AND HEADER
st.title("🎬 Movie Review Sentiment Analyzer")
st.markdown("### Powered by MLOps (FastAPI + MLflow + Docker)")
st.write("Enter a movie review below to see if it's Positive or Negative.")

# 3. USER INPUT
# A text area for the user to type the review
user_input = st.text_area("Type your review here:", height=150)

# 4. THE "PREDICT" BUTTON
if st.button("Analyze Sentiment"):
    if user_input.strip() == "":
        st.warning("Please enter some text first.")
    else:
        # 5. CONNECT TO BACKEND
        # This is where the Frontend talks to the Backend (The API we just built)
        # If we are in Docker, use the environment variable 'API_URL'.
        # If we are on your laptop, default to localhost.
        api_url = os.getenv("API_URL", "http://127.0.0.1:8000/predict")
        
        # Prepare the payload (the data to send)
        payload = {"text": user_input}
        
        try:
            # Show a spinner while waiting for the response
            with st.spinner("Analyzing..."):
                response = requests.post(api_url, json=payload)
            
            # 6. DISPLAY RESULTS
            if response.status_code == 200:
                data = response.json()
                
                # SAFETY CHECK: Did we actually get a result?
                if "result" in data:
                    sentiment = data["result"]
                    model_id = data.get("model_version", "Unknown")
                    
                    if sentiment.lower() == "positive":
                        st.success(f"**Sentiment: {sentiment.upper()}** 😃")
                    else:
                        st.error(f"**Sentiment: {sentiment.upper()}** 😡")
                    
                    st.caption(f"Prediction served by Model Version: {model_id}")
                
                # If the backend sent an error inside the JSON
                elif "error" in data:
                    st.error(f"Backend Error: {data['error']}")
                else:
                    st.error("Unknown response format from API.")
                    st.write(data) # Print the raw data to debug
                
            else:
                st.error(f"Error {response.status_code}: Could not contact the model.")
                st.write(response.text)
                
        except requests.exceptions.ConnectionError:
            st.error("🚨 Connection Error! Is the FastAPI backend running?")