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
            
            response = requests.get(search_url, headers=self.headers, params=params)
            logger.info(f"Search response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text}")
                return []
                
            response.raise_for_status()
            data = response.json()
            
            if not data.get('results'):
                logger.info("No results found in search response")
                return []

            # Get place details
            place_id = data['results'][0]['fsq_id']
            details_url = f"{self.base_url}/{place_id}"
            details_params = {
                "fields": "name,location,rating,stats,price,tel,website,hours,popularity"
            }
            
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
            
            # Get tips for the place
            tips_url = f"{self.base_url}/{place_id}/tips"
            all_tips = []
            seen_tips = set()  # Track unique tips
            offset = 0
            limit = 50  # Maximum allowed by the API
            max_offset = 1000  # Maximum number of tips we want to collect
            
            while offset < max_offset:
                tips_params = {
                    "limit": limit,
                    "offset": offset,
                    "sort": "POPULAR"
                }
                
                response = requests.get(tips_url, headers=self.headers, params=tips_params)
                logger.info(f"Tips response status code: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Error response: {response.text}")
                    break
                    
                response.raise_for_status()
                tips_data = response.json()
                
                if not tips_data or len(tips_data) == 0:
                    logger.info("No more tips available")
                    break
                
                new_tips_found = False
                for tip in tips_data:
                    text = tip.get('text', '')
                    if text and text not in seen_tips:
                        seen_tips.add(text)
                        all_tips.append({
                            'rating': None,
                            'text': text,
                            'date': tip.get('created_at', ''),
                            'source': 'Foursquare'
                        })
                        new_tips_found = True
                
                if not new_tips_found:
                    logger.info("No new tips found in this batch, stopping collection")
                    break
                
                if len(tips_data) < limit:
                    break
                    
                offset += limit
            
            logger.info(f"Total number of unique tips collected: {len(all_tips)}")
            return all_tips
            
        except Exception as e:
            logger.error(f"Error in get_tips: {str(e)}")
            return []

class ReviewScraper:
    def __init__(self):
        self.foursquare = FoursquareAPI()

    def get_all_reviews(self, business_name, location):
        all_reviews = []
        logger.info(f"\nGetting Foursquare tips for {business_name} in {location}")
        foursquare_reviews = self.foursquare.get_tips(business_name, location)
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
        df = pd.DataFrame(reviews)
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Negative Reviews', index=False)
            
            # Create simple summary
            summary = {
                'Metric': ['Total Negative Reviews', 'Average Rating', 'Average Sentiment'],
                'Value': [
                    len(df),
                    f"{df['rating'].mean():.2f}",
                    f"{df['compound'].mean():.2f}"
                ]
            }
            pd.DataFrame(summary).to_excel(writer, sheet_name='Summary', index=False)
            
            # Basic formatting
            workbook = writer.book
            for sheet in writer.sheets.values():
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D7E4BC'
                })
                for col_num, value in enumerate(df.columns.values):
                    sheet.write(0, col_num, value, header_format)
                    sheet.set_column(col_num, col_num, 15)
                sheet.set_column(1, 1, 50)  # Column B (review text)
                sheet.set_column(2, 2, 15)  # Column C (date)

        logger.info(f"Successfully saved results to {filename}")
    except Exception as e:
        logger.error(f"Error saving to Excel: {str(e)}", exc_info=True)

def main():
    try:
        logger.info("Starting sentiment analysis")
        if not os.getenv('FOURSQUARE_API_KEY'):
            warning_msg = "Warning: FOURSQUARE_API_KEY not found. Foursquare reviews will not be collected."
            logger.warning(warning_msg)
            return
        
        scraper = ReviewScraper()
        reviews = scraper.get_all_reviews(
            business_name="Olive Garden",
            location="Times Square, New York, NY"
        )
        
        if not reviews:
            logger.warning("No reviews found!")
            return
        
        analyzer = SentimentAnalyzer()
        analyzed_reviews = []
        for review in reviews:
            analysis = analyzer.analyze(review['text'])
            analyzed_reviews.append({**review, **analysis})
        
        # Filter for negative reviews (compound <= -0.2 and contains negative keywords)
        negative_keywords = [
            # Explicit negative words
            'bad', 'terrible', 'awful', 'horrible', 'disappointing', 'poor', 'mediocre', 'overrated', 'waste', 'never again',
            'worst', 'avoid', 'regret', 'ripoff', 'expensive', 'rude', 'slow', 'cold', 'undercooked', 'overcooked',
            'dirty', 'filthy', 'unclean', 'unsanitary', 'smelly', 'stale', 'tasteless', 'bland', 'dry', 'burnt',
            'unprofessional', 'unfriendly', 'unhelpful', 'ignored', 'wait', 'crowded', 'noisy', 'loud', 'uncomfortable',
            'overpriced', 'rip-off', 'scam', 'disgusting', 'inedible', 'spit', 'hair', 'bug', 'insect', 'complaint',
            
            # Subtle negative indicators
            'expected better', 'not worth', 'would not recommend', 'disappointed', 'let down', 'fell short',
            'could be better', 'needs improvement', 'room for improvement', 'not impressed', 'underwhelming',
            'average at best', 'nothing special', 'skip this', 'pass on', 'think twice', 'second thoughts',
            'not what i expected', 'not as good as', 'used to be better', 'gone downhill', 'not the same',
            'overrated', 'overhyped', 'tourist trap', 'chain restaurant', 'generic', 'mass produced',
            'frozen', 'microwaved', 'reheated', 'canned', 'packaged', 'pre-made', 'pre-cooked',
            'long wait', 'slow service', 'understaffed', 'busy', 'packed', 'noisy', 'loud music',
            'small portions', 'tiny', 'skimpy', 'not enough', 'too much', 'overpriced', 'pricey',
            'basic', 'simple', 'plain', 'boring', 'uninspired', 'lacking', 'missing', 'forgot',
            'mistake', 'error', 'wrong order', 'mixed up', 'confused', 'disorganized', 'chaotic',
            'uncomfortable', 'cramped', 'tight', 'squeezed', 'no space', 'no privacy', 'too close',
            'temperature', 'too hot', 'too cold', 'lukewarm', 'room temperature', 'not fresh',
            'greasy', 'oily', 'soggy', 'mushy', 'tough', 'chewy', 'rubbery', 'stringy',
            'artificial', 'fake', 'processed', 'chemical', 'preserved', 'preservatives',
            'not authentic', 'not traditional', 'americanized', 'watered down', 'diluted',
            'not worth the price', 'overcharged', 'hidden fees', 'extra charge', 'surprise charge',
            'not what was advertised', 'misleading', 'false advertising', 'different from menu',
            'not as described', 'not as pictured', 'not as shown', 'not as promised'
        ]
        negative_reviews = [
            review for review in analyzed_reviews 
            if review['compound'] <= -0.2 and 
            any(keyword in review['text'].lower() for keyword in negative_keywords)
        ]
        
        if not negative_reviews:
            logger.warning("No negative reviews found!")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'olive_garden_negative_reviews_{timestamp}.xlsx'
        save_to_excel(negative_reviews, filename)
        
        logger.info(f"\nAnalysis complete! Results saved to {filename}")
        logger.info(f"Total Negative Reviews: {len(negative_reviews)}")
        if negative_reviews:
            avg_rating = sum(r['rating'] for r in negative_reviews) / len(negative_reviews)
            avg_sentiment = sum(r['compound'] for r in negative_reviews) / len(negative_reviews)
            logger.info(f"Average Rating: {avg_rating:.2f}")
            logger.info(f"Average Sentiment: {avg_sentiment:.2f}")
        
        sources = {}
        for review in negative_reviews:
            source = review['source']
            sources[source] = sources.get(source, 0) + 1
        
        logger.info("\nNegative reviews by source:")
        for source, count in sources.items():
            logger.info(f"{source}: {count} reviews")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()