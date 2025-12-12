import streamlit as st
import requests
import json
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Rotten Potatoes", page_icon="🥔")
st.title("🥔 Rotten Potatoes: IIITB's Least Trusted Movie Review Hub")

# --- API ENDPOINTS ---
# Using the same logic for API URL as before, but the base URL.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
MOVIES_URL = f"{API_BASE_URL}/movies"
REVIEWS_URL = f"{API_BASE_URL}/reviews"
SUBMIT_REVIEW_URL = f"{API_BASE_URL}/submit_review"

# --- HELPER FUNCTIONS ---

def get_movies():
    """Fetches the list of movies from the backend API."""
    try:
        response = requests.get(MOVIES_URL)
        if response.status_code == 200:
            # Expecting a list of dicts: [{"id": 1, "name": "...", "description": "..."}, ...]
            return response.json()
        st.error(f"Error fetching movies: {response.status_code}")
        return []
    except requests.exceptions.ConnectionError:
        st.error("🚨 Connection Error! We are facing some technical difficulties. Please try again later.")
        return []

def calculate_score_and_status(movies_data, selected_movie_id):
    """
    Calculates the freshness score and status based on the movie_id.
    This function will now use a dedicated API endpoint /score/<movie_id>
    which your backend needs to implement.
    """
    if not selected_movie_id:
        return None, None, None

    try:
        score_url = f"{API_BASE_URL}/score/{selected_movie_id}"
        response = requests.get(score_url)

        if response.status_code == 200:
            data = response.json()
            # Expected response: {"total_reviews": 30, "positive_count": 25, "score": 83.33}
            score = data.get("score")
            total_reviews = data.get("total_reviews")
            
            if score is not None:
                if score >= 75:
                    status = "CERTIFIED HOT 🍟"
                    color = "green"
                elif score >= 60:
                    status = "FRESH 🥔"
                    color = "orange"
                else:
                    status = "ROTTEN 🤮"
                    color = "red"
                
                return score, status, total_reviews, color
            
            return 0, "No Reviews Yet", 0, "gray"

        st.warning("Could not fetch score. Assuming no reviews yet.")
        return 0, "No Reviews Yet", 0, "gray"

    except requests.exceptions.ConnectionError:
        st.error("🚨 Could not connect to score service.")
        return 0, "No Reviews Yet", 0, "gray"

def get_recent_reviews(movie_id):
    """Fetches the last N recent reviews for a movie from the backend API."""
    try:
        review_url = f"{REVIEWS_URL}/{movie_id}"
        response = requests.get(review_url)
        if response.status_code == 200:
            return response.json() 
        return []
    except requests.exceptions.ConnectionError:
        st.error("🚨 Could not connect to the database.")
        return []
    
# --- MAIN APPLICATION LOGIC ---

# Load movies data at the start
movies = get_movies()
movie_names = {m["name"]: m for m in movies}

# --- Preparation for Default State ---
PLACEHOLDER = "--- Select Movie ---"
# Create the full list of options, starting with the placeholder
movie_options = [PLACEHOLDER] + list(movie_names.keys())

# Determine the default index: 0 will be the placeholder
default_index = 0

# 1. MOVIE SELECTION
movie_selection = st.selectbox(
    "",
    options=movie_options,
    index=default_index
)

# --- Logic to handle the selection and prevent immediate display ---
# If the selection is the placeholder, selected_movie should be None
if movie_selection == PLACEHOLDER:
    selected_movie = None
    selected_movie_id = None
else:
    # Otherwise, look up the selected movie data
    selected_movie = movie_names.get(movie_selection)
    selected_movie_id = selected_movie["id"] if selected_movie else None

# 2. SCORE & DESCRIPTION DISPLAY (using columns for layout)
col1, col2 = st.columns([1, 2])

if selected_movie:
    # Calculate score and status
    score, status, total_reviews, color = calculate_score_and_status(movies, selected_movie_id)

    # Column 1: Score Display
    with col1:
        st.markdown(f"### Score: <span style='color:{color}'>{score:.0f}%</span>", unsafe_allow_html=True)
        st.markdown(f"**Status:** {status}")
        st.caption(f"Based on **{total_reviews}** reviews.")

    # Column 2: Description
    with col2:
        st.markdown("### Description")
        st.info(selected_movie["description"])

else:
    # Display a message when the placeholder is selected
    st.info("Please select a movie from the list above to view its details and submit a review.")

if selected_movie:
    st.markdown("---")

    st.subheader("Recent Community Reviews")
    
    recent_reviews = get_recent_reviews(selected_movie_id)

    if recent_reviews:
        for i, review in enumerate(recent_reviews):
            # Determine color based on isPos boolean
            color = "green" if review.get("isPos") else "red"

            # Render colored quote-style review
            st.markdown(
                f"> <span style='color:{color}; font-weight:500;'>{review['review']}</span>",
                unsafe_allow_html=True
            )

            st.markdown("---")

    else:
        st.info("Be the first to review this movie!")

    # 3. USER INPUT AREA
    st.write("### Write Your Own Review")

    # Clear the review box BEFORE the text area is drawn
    if st.session_state.get("should_clear_review", False):
        st.session_state.review_text_input = ""
        st.session_state.should_clear_review = False

    user_input = st.text_area("Type your review here:", key="review_text_input", height=150)
    current_review_text = st.session_state.review_text_input

    if "post_submission_message" not in st.session_state:
        st.session_state.post_submission_message = None

    # 4. THE "SUBMIT REVIEW" BUTTON
    if st.button("Submit Review"):

        st.session_state.post_submission_message = None
        
        review_words = current_review_text.strip().split()

        if not selected_movie_id:
            st.error("Please select a valid movie first.")
            
        # --- New 5-word minimum check ---
        elif len(review_words) < 5:
            st.warning("Please ensure your review has at least **5 words**.")
            
        elif current_review_text.strip() == "":
            # This check is now mostly redundant due to the word count check, but good for safety
            st.warning("Please enter some text first.")
            
        else:
            # 5. CONNECT TO BACKEND (New Submit Endpoint)
            payload = {
                "movie_id": selected_movie_id,
                "text": current_review_text # Use the variable bound to session state
            }
            
            try:
                with st.spinner("Analyzing and Saving Review..."):
                    response = requests.post(SUBMIT_REVIEW_URL, json=payload)
                
                # 6. DISPLAY RESULTS
                if response.status_code == 200:
                    data = response.json()
                    
                    if "sentiment" in data:
                        sentiment = data["sentiment"]
                        model_id = data.get("model_version", "Unknown")
                        
                        # Store the custom success/error message in session state
                        if sentiment.lower() == "positive":
                            msg = {
                                "type": "positive",
                                "text": f"**Thank you for your positive review!** Your feedback helps others discover great movies!"
                            }
                        else:
                            msg = {
                                "type": "negative",
                                "text": f"**Thank you for your negative review.** We appreciate your honesty."
                            }
                        st.session_state.post_submission_message = msg
                        
                        # Clear the review box
                        st.session_state.should_clear_review = True
                        st.experimental_rerun() # Rerun to refresh score and clear text area
                
                    elif "error" in data:
                        st.error(f"Backend Error: {data['error']}")
                    else:
                        st.error("Unknown response format from API.")
                        st.write(data)
                    
                else:
                    st.error(f"Error {response.status_code}: Could not submit review to the model.")
                    st.write(response.text)
                    
            except requests.exceptions.ConnectionError:
                st.error("🚨 Connection Error! We are facing some technical difficulties. Please try again later.")

    # Display the message outside the button block so it persists during rerun
    if st.session_state.post_submission_message:
        message_type = st.session_state.post_submission_message['type']
        message_text = st.session_state.post_submission_message['text']
        
        if message_type == 'positive':
            st.success(message_text)
        elif message_type == 'negative':
            st.error(message_text)