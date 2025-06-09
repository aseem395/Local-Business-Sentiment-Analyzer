import requests
from bs4 import BeautifulSoup
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
from datetime import datetime
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus

# Set up basic logging
logging.basicConfig(
    filename='sentiment_analyzer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  # 'w' mode to overwrite the file each time
)

# Add console handler to see logs in terminal
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger('').addHandler(console_handler)

# Load environment variables
load_dotenv()

class Browser:
    def __init__(self):
        logging.info("Initializing Browser")
        options = Options()
        # Enhanced Chrome options to better mimic real browser
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        logging.info("Browser started successfully")
    
    def get_page(self, url):
        try:
            self.driver.get(url)
            # Add random delay between 3-7 seconds
            time.sleep(random.uniform(3, 7))
            return self.driver.page_source
        except Exception as e:
            logging.error(f"Error loading page: {e}")
            return ""
    
    def click_reviews_tab(self):
        try:
            # Wait for the page to load
            time.sleep(5)
            
            # Find and click the reviews button
            reviews_button = self.driver.find_element('css selector', 'button[data-tab-index="1"]')
            if reviews_button:
                reviews_button.click()
                time.sleep(3)  # Wait for reviews to load
                
                # Scroll to load more reviews
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                return True
        except Exception as e:
            print(f"Error clicking reviews button: {e}")
        return False
    
    def close(self):
        try:
            self.driver.quit()
        except:
            pass

class FoursquareAPI:
    def __init__(self):
        self.api_key = os.getenv('FOURSQUARE_API_KEY')
        if not self.api_key:
            raise ValueError("FOURSQUARE_API_KEY not found")
        
        self.base_url = "https://api.foursquare.com/v3/places"
        self.headers = {"Accept": "application/json", "Authorization": self.api_key}
        print(f"Initialized FoursquareAPI with key")

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
            print(f"\nSearching Foursquare with URL: {search_url}")
            print(f"Search parameters: {params}")
            print(f"Headers: {self.headers}")
            
            response = requests.get(search_url, headers=self.headers, params=params)
            print(f"Search response status code: {response.status_code}")
            print(f"Search response headers: {response.headers}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return []
                
            response.raise_for_status()
            data = response.json()
            
            # Debug: Print the search response
            print(f"Foursquare search response: {data}")
            
            if not data.get('results'):
                print("No results found in search response")
                return []

            # Get place details
            place_id = data['results'][0]['fsq_id']
            details_url = f"{self.base_url}/{place_id}"
            details_params = {
                "fields": "name,location,rating,stats,price,tel,website,hours,popularity"
            }
            print(f"\nGetting details from URL: {details_url}")
            print(f"Details parameters: {details_params}")
            
            details_response = requests.get(details_url, headers=self.headers, params=details_params)
            print(f"Details response status code: {details_response.status_code}")
            
            if details_response.status_code != 200:
                print(f"Error response: {details_response.text}")
                return []
                
            details_response.raise_for_status()
            details_data = details_response.json()
            
            # Print place details
            print("\nPlace Details:")
            print(f"Name: {details_data.get('name', 'N/A')}")
            print(f"Address: {details_data.get('location', {}).get('formatted_address', 'N/A')}")
            print(f"Rating: {details_data.get('rating', 'N/A')}")
            print(f"Price Tier: {'$' * details_data.get('price', 0)}")
            print(f"Phone: {details_data.get('tel', 'N/A')}")
            print(f"Website: {details_data.get('website', 'N/A')}")
            
            place_url = f"https://foursquare.com/v/{place_id}"
            print(f"\nFoursquare URL: {place_url}")
            
            # Get tips for the place
            tips_url = f"{self.base_url}/{place_id}/tips"
            tips_params = {
                "limit": 50,  # Get more tips
                "sort": "POPULAR"  # Sort by popularity
            }
            print(f"\nGetting tips from URL: {tips_url}")
            print(f"Tips parameters: {tips_params}")
            
            response = requests.get(tips_url, headers=self.headers, params=tips_params)
            print(f"Tips response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return []
                
            response.raise_for_status()
            tips_data = response.json()
            
            # Debug: Print the tips response
            print(f"Foursquare tips response: {tips_data}")
            
            tips = []
            for tip in tips_data:
                rating = tip.get('rating', 5.0)
                if rating >= 3.0:
                    tips.append({
                        'rating': rating,
                        'text': tip.get('text', ''),
                        'date': tip.get('created_at', ''),
                        'source': 'Foursquare'
                    })
            
            return tips
            
        except Exception as e:
            print(f"Error in get_tips: {str(e)}")
            logging.error(f"Error getting Foursquare tips: {e}")
            return []

class ReviewScraper:
    def __init__(self):
        self.browser = Browser()
        self.foursquare = FoursquareAPI()
        # No Google selectors needed
        self.selectors = {}

    def __del__(self):
        self.browser.close()

    def extract_rating(self, element, source):
        return 0.0  # No web scraping, so this is unused

    def scrape_reviews(self, url, source):
        return []  # No web scraping, so this is unused

    def get_all_reviews(self, business_name, location):
        all_reviews = []
        # Only get Foursquare tips
        print(f"\nGetting Foursquare tips for {business_name} in {location}")
        foursquare_reviews = self.foursquare.get_tips(business_name, location)
        # Debug: Print the Foursquare reviews
        print(f"Foursquare reviews: {foursquare_reviews}")
        all_reviews.extend(foursquare_reviews)
        print(f"\nTotal reviews collected: {len(all_reviews)}")
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

    def analyze(self, text, rating=None):
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
            
            # If rating is provided and >= 3.0, consider the review positive
            if rating is not None and rating >= 3.0:
                result['compound'] = abs(result['compound'])  # Make compound positive
            
            return result
        except Exception as e:
            logging.error(f"Error analyzing text: {e}")
            return {'neg': 0.0, 'neu': 0.0, 'pos': 0.0, 'compound': 0.0, 
                   'service': 0, 'food': 0, 'ambiance': 0, 'price': 0, 'cleanliness': 0}

def save_to_excel(reviews, filename):
    try:
        logging.info(f"Starting to save {len(reviews)} reviews to Excel file: {filename}")
        # Create DataFrame
        df = pd.DataFrame(reviews)
        logging.info(f"Created DataFrame with {len(df)} rows")
        
        # Create Excel file
        print(f"Saving to Excel file: {filename}")
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Write reviews
            df.to_excel(writer, sheet_name='Positive Reviews', index=False)
            logging.info("Wrote reviews to Excel sheet")
            
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
            logging.info("Wrote summary to Excel sheet")
            
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
                sheet.set_column('B:B', 50)  # Review text
                sheet.set_column('C:C', 15)  # Date
            logging.info("Applied formatting to Excel file")
        
        logging.info(f"Successfully saved results to {filename}")
        print(f"Successfully saved results to {filename}")
    except Exception as e:
        error_msg = f"Error saving to Excel: {str(e)}"
        print(error_msg)
        logging.error(error_msg, exc_info=True)  # Include full traceback

def main():
    try:
        logging.info("Starting sentiment analysis")
        # Check if Foursquare API key exists
        if not os.getenv('FOURSQUARE_API_KEY'):
            warning_msg = "Warning: FOURSQUARE_API_KEY not found. Foursquare reviews will not be collected."
            print(warning_msg)
            logging.warning(warning_msg)
            print("To enable Foursquare reviews, add your API key to the .env file:")
            print("FOURSQUARE_API_KEY=your_api_key_here")
        
        # Get reviews for a well-known restaurant
        logging.info("Initializing ReviewScraper")
        scraper = ReviewScraper()
        reviews = scraper.get_all_reviews(
            business_name="The Spotted Pig",
            location="New York, NY"
        )
        
        # Debug: Print the reviews list
        logging.info(f"Collected {len(reviews)} reviews")
        print(f"Reviews collected: {reviews}")
        
        if not reviews:
            logging.warning("No reviews found!")
            print("No reviews found!")
            return
        
        # Analyze sentiment
        logging.info("Starting sentiment analysis")
        analyzer = SentimentAnalyzer()
        analyzed_reviews = []
        for review in reviews:
            analysis = analyzer.analyze(review['text'], review['rating'])
            analyzed_reviews.append({**review, **analysis})
        
        # Filter for positive reviews (compound >= 0)
        positive_reviews = [review for review in analyzed_reviews if review['compound'] >= 0]
        logging.info(f"Found {len(positive_reviews)} positive reviews")
        
        if not positive_reviews:
            logging.warning("No positive reviews found!")
            print("No positive reviews found!")
            return
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'spotted_pig_positive_reviews_{timestamp}.xlsx'
        save_to_excel(positive_reviews, filename)
        
        # Print results
        print(f"\nAnalysis complete! Results saved to {filename}")
        print(f"Total Positive Reviews: {len(positive_reviews)}")
        print(f"Average Rating of Positive Reviews: {sum(r['rating'] for r in positive_reviews) / len(positive_reviews):.2f}")
        print(f"Average Sentiment of Positive Reviews: {sum(r['compound'] for r in positive_reviews) / len(positive_reviews):.2f}")
        
        # Print source distribution
        sources = {}
        for review in positive_reviews:
            source = review['source']
            sources[source] = sources.get(source, 0) + 1
        
        print("\nPositive reviews by source:")
        for source, count in sources.items():
            print(f"{source}: {count} reviews")
        
    except Exception as e:
        error_msg = f"Error in main: {str(e)}"
        print(error_msg)
        logging.error(error_msg, exc_info=True)  # Include full traceback

if __name__ == "__main__":
    main()