# historical_data_fetcher.py
import yfinance as yf
from datetime import date, datetime, timedelta
from agents.feature_engineering import FeatureEngineer
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockDataFetcher:
    def n_weeks_before(self,date_string, n):
    
        date = datetime.strptime(date_string, "%Y-%m-%d") - timedelta(days=7*n)

        return date.strftime("%Y-%m-%d")

    def fetch_historical_data(self, ticker,curday, n_weeks):

        try:
            steps = [self.n_weeks_before(curday, n) for n in range(n_weeks + 1)][::-1]
        except Exception:
            print("Invalid date")
        """
        Fetch historical stock price data.
        """
        print(f"Fetching historical data for {ticker}...")
        stock_data = yf.download(ticker, steps[0], steps[-1])
        return stock_data
    
    def get_historical_data(self, ticker,curday, n_weeks):
        try:
            # Fetch historical data
            
            feature_engineer = FeatureEngineer()
            logging.info(f"Fetching historical data for {ticker}...")
            hist_data = self.fetch_historical_data(ticker,curday, n_weeks)

            if hist_data.empty:
                logging.warning(f"No historical data fetched for {ticker}.")
                return


        
            new_data = hist_data

            if not new_data.empty:
                # Feature engineer the new data
                logging.info(f"Feature  historical data for {ticker}...")
                engineered_data = feature_engineer.transform(new_data)
                print(engineered_data)

                # Ensure 'Date' column is properly handled
                if 'Date' not in engineered_data.columns:
                    engineered_data['Date'] = engineered_data.index

                # Ensure all expected columns are present
                expected_columns = ['Date', 'Open', 'High', 'Low','Close', 'Volume', 'EMA_12', 'EMA_26', 'RSI', 
                                    'MACD', 'Signal_Line', 
                                    'ATR', 'Momentum', 'ROC']
                
                # Add any missing columns with NaN values
                for col in expected_columns:
                    if col not in engineered_data.columns:
                        logging.warning(f"Missing column: {col}")
                       

                # Ensure columns are in the expected order
                engineered_data = engineered_data[expected_columns]

                logging.info(f"Inside History{engineered_data}")

                logging.info("Where are you history")
                return engineered_data
              
            else:
                logging.info(f"No new data to add for {ticker}.")
        except Exception as e:
            logging.error(f"Error during live data update for {ticker}: {e}")
