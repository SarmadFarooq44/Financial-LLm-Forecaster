import yfinance as yf
class RealTimeMarketData:
    def fetch_live_data(self, ticker):
        """
        Fetch real-time stock market data.
        """
        print(f"Fetching live data for {ticker}...")
        stock = yf.Ticker(ticker)
        return stock.history(period="1mo", interval="1h")