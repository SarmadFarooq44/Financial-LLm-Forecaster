# data_worker.py
from agents.historical_data_fetcher import StockDataFetcher  # Importing the external historical data fetcher
from agents.financial_news_fetcher import FinancialNewsFetcher  # Financial news fetcher is still external
from agents.real_time_data import RealTimeMarketData  # Assuming this class is in another file


class DataWorker:
    def __init__(self):
        self.news_fetcher = FinancialNewsFetcher()  # External financial news fetcher
        self.stock_data_fetcher = StockDataFetcher()  # External historical data fetcher
        self.real_time_data = RealTimeMarketData()  # Assuming RealTimeMarketData class is elsewhere

    def fetch_multimodal_data(self, ticker, startdate,enddate):
        """
        Fetch news, historical prices, and live data for a ticker.
        """
        print(f"Fetching multimodal data for {ticker}...")
        
        # Fetch financial news
        news = self.news_fetcher.fetch_news(ticker,startdate,enddate)
    

        return {
            "news": news,
        }
