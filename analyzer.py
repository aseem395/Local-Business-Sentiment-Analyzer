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
    format='%(asctime)s - %(message)s'
)

# Load environment variables
load_dotenv()

class Browser:
    def __init__(self):
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
        logging.info("Browser started")
    
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

    def get_tips(self, business_name, location):
        try:
            # Search for place
            search_url = f"{self.base_url}/search"
            params = {"query": business_name, "near": location, "limit": 1}
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Debug: Print the search response
            print(f"Foursquare search response: {data}")
            
            if not data.get('results'):
                return []

            # Get tips for the place
            place_id = data['results'][0]['fsq_id']
            tips_url = f"{self.base_url}/{place_id}/tips"
            response = requests.get(tips_url, headers=self.headers)
            response.raise_for_status()
            tips_data = response.json()
            
            # Debug: Print the tips response
            print(f"Foursquare tips response: {tips_data}")
            
            tips = []
            for tip in tips_data:
                tips.append({
                    'rating': 5.0,
                    'text': tip.get('text', ''),
                    'date': tip.get('created_at', ''),
                    'source': 'Foursquare'
                })
            
            return tips
            
        except Exception as e:
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
            return {**sentiment, **keyword_counts}
        except Exception as e:
            logging.error(f"Error analyzing text: {e}")
            return {'neg': 0.0, 'neu': 0.0, 'pos': 0.0, 'compound': 0.0, 
                   'service': 0, 'food': 0, 'ambiance': 0, 'price': 0, 'cleanliness': 0}

def save_to_excel(reviews, filename):
    try:
        # Create DataFrame
        df = pd.DataFrame(reviews)
        
        # Filter for negative reviews (compound score < 0)
        df = df[df['compound'] < 0]
        
        if df.empty:
            print("No negative reviews found!")
            return
        
        # Create Excel file
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Write reviews
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
        
        logging.info(f"Results saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving to Excel: {e}")

def main():
    try:
        # Check if Foursquare API key exists
        if not os.getenv('FOURSQUARE_API_KEY'):
            print("Warning: FOURSQUARE_API_KEY not found. Foursquare reviews will not be collected.")
            print("To enable Foursquare reviews, add your API key to the .env file:")
            print("FOURSQUARE_API_KEY=your_api_key_here")
        
        # Get reviews
        scraper = ReviewScraper()
        reviews = scraper.get_all_reviews(
            business_name="Joe's Pizza",
            location="New York, NY"
        )
        
        # Debug: Print the reviews list
        print(f"Reviews collected: {reviews}")
        
        if not reviews:
            print("No reviews found!")
            return
        
        # Analyze sentiment
        analyzer = SentimentAnalyzer()
        analyzed_reviews = []
        for review in reviews:
            analysis = analyzer.analyze(review['text'])
            analyzed_reviews.append({**review, **analysis})
        
        # Filter for negative reviews
        negative_reviews = [review for review in analyzed_reviews if review['compound'] < 0]
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'joes_pizza_negative_reviews_{timestamp}.xlsx'
        save_to_excel(analyzed_reviews, filename)
        
        # Print results
        print(f"\nAnalysis complete! Results saved to {filename}")
        print(f"Total Negative Reviews: {len(negative_reviews)}")
        if negative_reviews:
            print(f"Average Rating of Negative Reviews: {sum(r['rating'] for r in negative_reviews) / len(negative_reviews):.2f}")
            print(f"Average Sentiment of Negative Reviews: {sum(r['compound'] for r in negative_reviews) / len(negative_reviews):.2f}")
        
        # Print source distribution
        sources = {}
        for review in negative_reviews:
            source = review['source']
            sources[source] = sources.get(source, 0) + 1
        
        print("\nNegative reviews by source:")
        for source, count in sources.items():
            print(f"{source}: {count} reviews")
        
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()