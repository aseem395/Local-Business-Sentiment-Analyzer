import streamlit as st
import pandas as pd
from datetime import datetime
from analyzer import ReviewScraper, SentimentAnalyzer, save_to_excel
import os

# Configure Streamlit page
st.set_page_config(
    page_title="Business Sentiment Analyzer",
    page_icon="📊",
    layout="wide"
)

def login():
    pass

def analyze_business(business_name, location):
    """Analyze reviews for a business and return negative reviews."""
    # Get reviews
    scraper = ReviewScraper()
    reviews = scraper.get_all_reviews(business_name, location)
    
    if not reviews:
        return None, "No reviews found."
    
    # Analyze reviews
    analyzer = SentimentAnalyzer()
    analyzed_reviews = []
    
    for review in reviews:
        sentiment = analyzer.analyze(review['text'])
        sentiment['analyzed_rating'] = sentiment.pop('rating')
        analyzed_reviews.append({**review, **sentiment})

    # Filter negative reviews
    negative_reviews = [r for r in analyzed_reviews if r['compound'] <= -0.2]
    
    if not negative_reviews:
        return None, "No negative reviews found."
        
    return negative_reviews, f"Found {len(negative_reviews)} negative reviews!"

# Add error handling for file operations
def save_file_safely(data, filename):
    try:
        save_to_excel(data, filename)
        return True
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return False

def main():
    st.title("Business Sentiment Analyzer 📊")
    
    # Add a sidebar with information
    with st.sidebar:
        st.header("About")
        st.write("This app analyzes business reviews and identifies negative sentiment.")
        st.write("Enter a business name and location to get started.")

    # Input fields
    business_name = st.text_input("Business Name", "The Spotted Pig")
    location = st.text_input("Location", "New York, NY")

    if st.button("Analyze"):
        try:
            with st.spinner("Fetching reviews and analyzing..."):
                # Get analysis results
                negative_reviews, message = analyze_business(business_name, location)
                
                if negative_reviews is None:
                    st.warning(message)
                else:
                    # Display results
                    st.success(message)
                    st.dataframe(pd.DataFrame(negative_reviews))

                    # Save and provide download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"reviews_{timestamp}.xlsx"
                    
                    if save_file_safely(negative_reviews, filename):
                        with open(filename, "rb") as f:
                            st.download_button(
                                "Download Excel",
                                f,
                                file_name=filename
                            )
                        # Clean up the file after download
                        try:
                            os.remove(filename)
                        except:
                            pass
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.info("Please try again or contact support if the problem persists.")

if __name__ == "__main__":
    main()
