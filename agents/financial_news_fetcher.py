import requests
from newspaper import Article
import re
import cohere
from pinecone import Pinecone, ServerlessSpec
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import nltk
import schedule
import time
import threading
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
    ]
)



# Download required NLTK data
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')

# Initialize APIs and services
FINNHUB_API_KEY = ""
COHERE_API_KEY = ""


# Initialize Finnhub client
try:
    finnhub_client = requests.Session()
    finnhub_client.headers.update({'X-Finnhub-Token': FINNHUB_API_KEY})
except Exception as e:
    raise Exception(f"Error initializing Finnhub client: {e}")

# Initialize Cohere client
try:
    cohere_client = cohere.Client(COHERE_API_KEY)
except Exception as e:
    raise Exception(f"Error initializing Cohere client: {e}")



lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))


class FinancialNewsFetcher:
    def __init__(self):
        self.base_url = "https://finnhub.io/api/v1/company-news"



    def get_date_range(self,end_date, n_weeks):
        """
        Calculate start and end dates based on the given end_date and the number of weeks.
        :param end_date: End date as a string in 'YYYY-MM-DD' format.
        :param n_weeks: Number of weeks to look back.
        :return: start_date (str), end_date (str)
        """
        # Parse the end_date string into a datetime object
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Calculate the start date by subtracting n_weeks
        start_date_obj = end_date_obj - timedelta(weeks=n_weeks)
        
        # Format dates as 'YYYY-MM-DD'
        start_date = start_date_obj.strftime('%Y-%m-%d')
        end_date = end_date_obj.strftime('%Y-%m-%d')
        
        return start_date, end_date

      
    def fetch_news(self, symbol, end_date,n_weeks):
        """
        Fetch financial news articles using Finnhub API.
        """

        start_date,end_date = self.get_date_range(end_date,n_weeks)
        logging.info(f"Dates {start_date}.")
        logging.info(f"Dates {end_date}.")


        try:
            params = {
                "symbol": symbol,
                "from": start_date,
                "to": end_date
            }
            response = finnhub_client.get(self.base_url, params=params)
            logging.info(f"response {response}.")

            response.raise_for_status()
            news = response.json()
            cleaned_news = []
            for n in news:
                cleaned_content = self.clean_text(n['summary']) if n.get('summary') else "No summary available."
                cleaned_news.append({
                    "date": datetime.fromtimestamp(n['datetime']).strftime('%Y-%m-%d %H:%M:%S'),
                    "headline": n['headline'],
                    "content": cleaned_content,
                    "symbol": symbol
                })
            return cleaned_news
        except requests.RequestException as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []

    def clean_text(self, text):
        """
        Clean the article text (remove special characters, stopwords, etc.).
        """
        try:
            text = re.sub(r'[^A-Za-z\s]', '', text)
            tokens = word_tokenize(text.lower())
            tokens = [t for t in tokens if t not in stop_words]
            tokens = [lemmatizer.lemmatize(t) for t in tokens]
            return ' '.join(tokens)
        except Exception as e:
            print(f"Error cleaning text: {e}")
            return ""

    def embed_articles(self, articles):
        """
        Convert the articles into embeddings using Cohere.
        """
        embeddings = []
        for article in articles:
            try:
                title_response = cohere_client.embed(texts=[article['headline']])
                content_response = cohere_client.embed(texts=[article['content']])
                embeddings.append({
                    'title_embedding': title_response.embeddings[0],
                    'content_embedding': content_response.embeddings[0]
                })
            except Exception as e:
                print(f"Error embedding article: {e}")
        return embeddings



    def embed_query(self, query):
        """
        Convert the query into an embedding.
        """
        try:
            response = cohere_client.embed(texts=[query])
            return response.embeddings[0]
        except Exception as e:
            print(f"Error embedding query: {e}")
            return None




