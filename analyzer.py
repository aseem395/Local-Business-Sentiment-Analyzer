import requests
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import time
import random
import os
from dotenv import load_dotenv
import logging
import sys

# Set up logging with both file and console handlers
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create file handler
    log_file = os.path.join('logs', f'sentiment_analyzer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logging
logger = setup_logging()

# Load environment variables
load_dotenv()

class FoursquareAPI:
    def __init__(self):
        self.api_key = os.getenv('FOURSQUARE_API_KEY')
        if not self.api_key:
            raise ValueError("FOURSQUARE_API_KEY not found")
        
        self.base_url = "https://api.foursquare.com/v3/places"
        self.headers = {"Accept": "application/json", "Authorization": self.api_key}
        logger.info("Initialized FoursquareAPI")

    def get_tips(self, business_name, location):
        try:
            # Search for place
            search_url = f"{self.base_url}/search"
            params = {
                "query": business_name,
                "near": location,
                "limit": 1,
                "fields": "fsq_id,name,location,rating,stats"
            }
            logger.info(f"Searching Foursquare with URL: {search_url}")
            logger.info(f"Search parameters: {params}")
            logger.info(f"Headers: {self.headers}")
            
            response = requests.get(search_url, headers=self.headers, params=params)
            logger.info(f"Search response status code: {response.status_code}")
            logger.info(f"Search response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text}")
                return []
                
            response.raise_for_status()
            data = response.json()
            
            # Debug: Print the search response
            logger.info(f"Foursquare search response: {data}")
            
            if not data.get('results'):
                logger.info("No results found in search response")
                return []

            # Get place details
            place_id = data['results'][0]['fsq_id']
            details_url = f"{self.base_url}/{place_id}"
            details_params = {
                "fields": "name,location,rating,stats,price,tel,website,hours,popularity"
            }
            logger.info(f"\nGetting details from URL: {details_url}")
            logger.info(f"Details parameters: {details_params}")
            
            details_response = requests.get(details_url, headers=self.headers, params=details_params)
            logger.info(f"Details response status code: {details_response.status_code}")
            
            if details_response.status_code != 200:
                logger.error(f"Error response: {details_response.text}")
                return []
                
            details_response.raise_for_status()
            details_data = details_response.json()
            
            # Print place details
            logger.info("\nPlace Details:")
            logger.info(f"Name: {details_data.get('name', 'N/A')}")
            logger.info(f"Address: {details_data.get('location', {}).get('formatted_address', 'N/A')}")
            logger.info(f"Rating: {details_data.get('rating', 'N/A')}")
            logger.info(f"Price Tier: {'$' * details_data.get('price', 0)}")
            logger.info(f"Phone: {details_data.get('tel', 'N/A')}")
            logger.info(f"Website: {details_data.get('website', 'N/A')}")
            
            place_url = f"https://foursquare.com/v/{place_id}"
            logger.info(f"\nFoursquare URL: {place_url}")
            
            # Get tips for the place
            tips_url = f"{self.base_url}/{place_id}/tips"
            tips_params = {
                "limit": 50,  # Get more tips
                "sort": "POPULAR"  # Sort by popularity
            }
            logger.info(f"\nGetting tips from URL: {tips_url}")
            logger.info(f"Tips parameters: {tips_params}")
            
            response = requests.get(tips_url, headers=self.headers, params=tips_params)
            logger.info(f"Tips response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text}")
                return []
                
            response.raise_for_status()
            tips_data = response.json()
            
            # Debug: Print the tips response
            logger.info(f"Foursquare tips response: {tips_data}")
            
            tips = []
            for tip in tips_data:
                text = tip.get('text', '')
                if text: 
                    tips.append({
                        'rating': None,
                        'text': text,
                        'date': tip.get('created_at', ''),
                        'source': 'Foursquare'
                    })
            
            return tips
            
        except Exception as e:
            logger.error(f"Error in get_tips: {str(e)}")
            return []

class ReviewScraper:
    def __init__(self):
        self.foursquare = FoursquareAPI()
        # No Google selectors needed
        self.selectors = {}

    def get_all_reviews(self, business_name, location):
        all_reviews = []
        # Only get Foursquare tips
        logger.info(f"\nGetting Foursquare tips for {business_name} in {location}")
        foursquare_reviews = self.foursquare.get_tips(business_name, location)
        # Debug: Print the Foursquare reviews
        logger.info(f"Foursquare reviews: {foursquare_reviews}")
        all_reviews.extend(foursquare_reviews)
        logger.info(f"\nTotal reviews collected: {len(all_reviews)}")
        return all_reviews

class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        # Simple keyword categories
        self.keywords = {
            'service': ['service', 'staff', 'employee', 'server', 'waiter', 'waitress'],
            'food': ['food', 'dish', 'meal', 'taste', 'flavor', 'menu'],
            'ambiance': ['ambiance', 'atmosphere', 'decor', 'environment', 'setting'],
            'price': ['price', 'cost', 'expensive', 'cheap', 'value', 'worth'],
            'cleanliness': ['clean', 'hygiene', 'sanitary', 'dirty', 'messy']
        }

    def analyze(self, text):
        try:
            # Get sentiment scores
            sentiment = self.analyzer.polarity_scores(text)
            
            # Count keywords
            keyword_counts = {}
            for category, words in self.keywords.items():
                count = 0
                for word in words:
                    if word in text.lower():
                        count += 1
                keyword_counts[category] = count
            
            # Combine results
            result = {**sentiment, **keyword_counts}
            
            # Convert compound score to a rating (0-5 scale)
            result['rating'] = (sentiment['compound'] + 1) * 2.5  # Convert from [-1,1] to [0,5], Sentiment-based rating in [0, 5]
            
            return result
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return {'neg': 0.0, 'neu': 0.0, 'pos': 0.0, 'compound': 0.0, 'rating': 0.0,
                   'service': 0, 'food': 0, 'ambiance': 0, 'price': 0, 'cleanliness': 0}

def save_to_excel(reviews, filename):
    try:
        logger.info(f"Starting to save {len(reviews)} reviews to Excel file: {filename}")
        # Create DataFrame
        df = pd.DataFrame(reviews)
        logger.info(f"Created DataFrame with {len(df)} rows")
        
        # Create Excel file
        logger.info(f"Saving to Excel file: {filename}")
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Write reviews
            df.to_excel(writer, sheet_name='Positive Reviews', index=False)
            logger.info("Wrote reviews to Excel sheet")
            
            # Create simple summary
            summary = {
                'Metric': ['Total Positive Reviews', 'Average Rating', 'Average Sentiment'],
                'Value': [
                    len(df),
                    f"{df['rating'].mean():.2f}",
                    f"{df['compound'].mean():.2f}"
                ]
            }
            pd.DataFrame(summary).to_excel(writer, sheet_name='Summary', index=False)
            logger.info("Wrote summary to Excel sheet")
            
            # Basic formatting
            workbook = writer.book
            for sheet in writer.sheets.values():
                # Format headers
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D7E4BC'
                })
                for col_num, value in enumerate(df.columns.values):
                    sheet.write(0, col_num, value, header_format)
                    sheet.set_column(col_num, col_num, 15)
                # Set column widths
                sheet.set_column(1, 1, 50)  # Column B (review text)
                sheet.set_column(2, 2, 15)  # Column C (date)

            logger.info("Applied formatting to Excel file")
        
        logger.info(f"Successfully saved results to {filename}")
        logger.info(f"Successfully saved results to {filename}")
    except Exception as e:
        error_msg = f"Error saving to Excel: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Include full traceback

def main():
    try:
        logger.info("Starting sentiment analysis")
        # Check if Foursquare API key exists
        if not os.getenv('FOURSQUARE_API_KEY'):
            warning_msg = "Warning: FOURSQUARE_API_KEY not found. Foursquare reviews will not be collected."
            logger.warning(warning_msg)
            logger.info(warning_msg)
            logger.info("To enable Foursquare reviews, add your API key to the .env file:")
            logger.info("FOURSQUARE_API_KEY=your_api_key_here")
        
        # Get reviews for a well-known restaurant
        logger.info("Initializing ReviewScraper")
        scraper = ReviewScraper()
        reviews = scraper.get_all_reviews(
            business_name="The Spotted Pig",
            location="New York, NY"
        )
        
        # Debug: Print the reviews list
        logger.info(f"Collected {len(reviews)} reviews")
        logger.info(f"Reviews collected: {reviews}")
        
        if not reviews:
            logger.warning("No reviews found!")
            logger.info("No reviews found!")
            return
        
        # Analyze sentiment
        logger.info("Starting sentiment analysis")
        analyzer = SentimentAnalyzer()
        analyzed_reviews = []
        for review in reviews:
            analysis = analyzer.analyze(review['text'])
            analyzed_reviews.append({**review, **analysis})
        
        # Filter for positive reviews (compound >= 0.2)
        positive_reviews = [review for review in analyzed_reviews if review['compound'] >= 0.2]
        logger.info(f"Found {len(positive_reviews)} positive reviews")
        
        if not positive_reviews:
            logger.warning("No positive reviews found!")
            logger.info("No positive reviews found!")
            return
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'spotted_pig_positive_reviews_{timestamp}.xlsx'
        save_to_excel(positive_reviews, filename)
        
        # Print results
        logger.info(f"\nAnalysis complete! Results saved to {filename}")
        logger.info(f"Total Positive Reviews: {len(positive_reviews)}")
        if positive_reviews:
            avg_rating = sum(r['rating'] for r in positive_reviews) / len(positive_reviews)
            avg_sentiment = sum(r['compound'] for r in positive_reviews) / len(positive_reviews)
            logger.info(f"Average Rating: {avg_rating:.2f}")
            logger.info(f"Average Sentiment: {avg_sentiment:.2f}")
        
        # Print source distribution
        sources = {}
        for review in positive_reviews:
            source = review['source']
            sources[source] = sources.get(source, 0) + 1
        
        logger.info("\nPositive reviews by source:")
        for source, count in sources.items():
            logger.info(f"{source}: {count} reviews")
        
    except Exception as e:
        error_msg = f"Error in main: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Include full traceback

if __name__ == "__main__":
    main()