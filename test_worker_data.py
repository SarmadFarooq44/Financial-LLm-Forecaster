from agents.worker_data import DataWorker

def test_data_fetching():
    # Initialize the DataWorker
    data_worker = DataWorker()

    # Test fetching data for a valid stock ticker
    ticker = "AAPL"  # Replace with any valid ticker symbol
    data = data_worker.fetch_data(ticker)

    # Print the results
    if not data.empty:
        print(f"Fetched {len(data)} rows of data for {ticker}:")
        print(data.head())
    else:
        print(f"No data fetched for ticker '{ticker}'.")

if __name__ == "__main__":
    test_data_fetching()
