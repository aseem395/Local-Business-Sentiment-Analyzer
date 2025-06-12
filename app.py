import streamlit as st
import pandas as pd
from datetime import datetime
from analyzer import ReviewScraper, SentimentAnalyzer, save_to_excel  # Put your classes in sentiment_app.py

st.title("Sentiment Analysis App")

business_name = st.text_input("Business Name", "The Spotted Pig")
location = st.text_input("Location", "New York, NY")

if st.button("Analyze"):
    with st.spinner("Fetching reviews and analyzing..."):
        scraper = ReviewScraper()
        reviews = scraper.get_all_reviews(business_name, location)

        if not reviews:
            st.warning("No reviews found.")
        else:
            analyzer = SentimentAnalyzer()
            analyzed_reviews = [dict(**r, **analyzer.analyze(r['text'])) for r in reviews]
            positive_reviews = [r for r in analyzed_reviews if r['compound'] >= 0.2]

            if not positive_reviews:
                st.warning("No positive reviews found.")
            else:
                st.success(f"Found {len(positive_reviews)} positive reviews!")
                df = pd.DataFrame(positive_reviews)
                st.dataframe(df)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"reviews_{timestamp}.xlsx"
                save_to_excel(positive_reviews, filename)

                with open(filename, "rb") as f:
                    st.download_button("Download Excel", f, file_name=filename)
