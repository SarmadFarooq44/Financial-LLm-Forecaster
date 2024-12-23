import time  # For scheduling updates
from datetime import datetime
import pandas as pd
from agents.worker_data import DataWorker  # Assuming DataWorker is in data_worker.py
from agents.feature_engineering import FeatureEngineer
from agents.decision_agent import DecisionAgent
from agents.database_manager import DatabaseManager
from agents.real_time_data import RealTimeMarketData
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from datetime import date, timedelta

# Calculate start and end dates for the past week
end_date = date.today()
start_date = end_date - timedelta(days=7)

start_date = start_date.strftime('%Y-%m-%d')
end_date = end_date.strftime('%Y-%m-%d')


def get_live_data(ticker):
        try:
            # Fetch historical data
            fetcher = RealTimeMarketData()
            feature_engineer = FeatureEngineer()
            logging.info(f"Fetching live data for {ticker}...")
            live_data = fetcher.fetch_live_data(ticker)

            if live_data.empty:
                logging.warning(f"No live data fetched for {ticker}.")
                return


        
            new_data = live_data

            if not new_data.empty:
                # Feature engineer the new data
                logging.info(f"Feature engineering live data for {ticker}...")
                engineered_data = feature_engineer.transform(new_data)
                print(engineered_data)

                # Ensure 'Date' column is properly handled
                if 'Date' not in engineered_data.columns:
                    engineered_data['Date'] = engineered_data.index

                # Ensure all expected columns are present
                expected_columns = ['Date', 'Open', 'High', 'Low','Close', 'Volume', 
                                    'SMA_20', 'SMA_50', 'EMA_12', 'EMA_26', 'RSI', 
                                    'BB_upper', 'BB_lower', 'MACD', 'Signal_Line', 
                                    'ATR', 'Momentum', 'ROC']
                
                # Add any missing columns with NaN values
                for col in expected_columns:
                    if col not in engineered_data.columns:
                        logging.warning(f"Missing column: {col}")
                       

                # Ensure columns are in the expected order
                engineered_data = engineered_data[expected_columns]

                print("Where are you")
                return engineered_data
              
            else:
                logging.info(f"No new data to add for {ticker}.")
        except Exception as e:
            logging.error(f"Error during live data update for {ticker}: {e}")


def main():
    
    # Initialize agents
    data_worker = DataWorker()
    db_manager = DatabaseManager()
    db_manager.initialize_table()
   
    agent = DecisionAgent(sentiment_threshold=0.2)

    ticker = "AAPL"  # Example ticker

    # Initial update for historical data
    db_manager.update_historical_data(ticker)

    # Schedule updates every hour
    logging.info("Starting hourly updates...")
    while True:
        try:
            # Update historical data
            db_manager.update_historical_data(ticker)

            # Fetch and display the latest historical data
            print("Getting historical data")
            historical_data = db_manager.get_historical_data(ticker)
            logging.info(f"Latest historical data for {ticker}")
            print(historical_data)

            print("Getting live data")
            live_data = get_live_data(ticker)
            logging.info(f"Latest live data for {ticker}")
            print(live_data)
         

            # Fetch multimodal data for a ticker (news, historical data, and live data)
            multimodal_data = data_worker.fetch_multimodal_data(ticker,start_date,end_date)

            # Make a decision based on the articles
            decision = agent.make_decision(multimodal_data['news'])

            # Output the decision
            logging.info("\nDecision:")
            logging.info(f"- Decision: {decision['decision']}")
            logging.info(f"- Average Sentiment: {decision['average_sentiment']}")
            logging.info(f"- Articles Analyzed: {decision['articles_analyzed']}")

            # Wait for an hour before the next update
            logging.info(f"Waiting for the next update at {datetime.now()}...\n")
            time.sleep(3600)  # 1 hour in seconds
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            time.sleep(60)  # Wait for 1 minute before retrying


if __name__ == "__main__":
    main()
