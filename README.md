Local Business Sentiment Analyzer

Overview
This project analyzes sentiment from reviews of local businesses using the Foursquare API. It collects reviews, performs sentiment analysis, and saves the results to an Excel file.

Features
- Collects reviews from Foursquare
- Performs sentiment analysis using VADER
- Saves results to an Excel file with a summary

Prerequisites
- Python 3.6+
- Required Python packages (install via `pip install -r requirements.txt`):
  - requests
  - beautifulsoup4
  - pandas
  - vaderSentiment
  - selenium
  - webdriver_manager
  - python-dotenv
  - xlsxwriter

Setup
1. Clone the repository:
   
   git clone <repository-url>
   cd local-business-sentiment-analyzer
   

2. Install dependencies:
   
   pip install -r requirements.txt
   

3. Create a `.env` file in the project root with your Foursquare API key:
   
   FOURSQUARE_API_KEY=your_api_key_here
   

Usage
Run the script:

python analyzer.py


The script will:
- Collect reviews from Foursquare for the specified business
- Perform sentiment analysis
- Save the results to an Excel file named `joes_pizza_reviews_<timestamp>.xlsx`

Output
- Excel File: Contains two sheets:
  - Reviews: Raw review data with sentiment scores
  - Summary: Total reviews, average rating, and average sentiment

Troubleshooting
- If no reviews are found, check your Foursquare API key and ensure the business exists on Foursquare.
- For more detailed logs, check `sentiment_analyzer.log`.

License
This project is licensed under the MIT License - see the LICENSE file for details. 