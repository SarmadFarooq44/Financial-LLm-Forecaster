import numpy as np
import pandas as pd
pd.set_option('display.max_columns', None)  # None means no limit on the number of columns to display

# Set other options for better readability (optional)
pd.set_option('display.width', None)  # Automatically adjust width based on terminal/console
pd.set_option('display.max_colwidth', None)  # Display full content in each column

class FeatureEngineer:
    def add_features(self, data):
        print("Here4")
        print("Initial data:")
        print(data)

        # Find the 'Close' column
        close_columns = [col for col in data.columns if 'Close' in col]
        if not close_columns:
            raise KeyError("'Close' column not found. Ensure the input data contains closing price information.")
        close_column = close_columns[0]
        data['Close'] = data[close_column]

        # Feature Engineering
       
        data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()
        data['RSI'] = self.calculate_rsi(data['Close'])
        data['MACD'], data['Signal_Line'] = self.calculate_macd(data['Close'])
        data['ATR'] = self.calculate_atr(data)
        data['Momentum'] = data['Close'] - data['Close'].shift(10)
        data['ROC'] = ((data['Close'] - data['Close'].shift(10)) / data['Close'].shift(10)) * 100

        # Drop NaN values and reset index
        print("Here now")
        print(data)


        if isinstance(data.index, pd.DatetimeIndex):
            data.reset_index(inplace=True)

        # Flatten multi-index columns but keep only the first level
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]

        # Rename 'Datetime' to 'Date' only if 'Date' is not already a column
        print("Here now 2")
        print(data.columns)
        if 'Datetime' in data.columns and 'Date' not in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)

        print("After flattening multi-index columns (if applicable):")
        print(data.columns)

        # Ensure 'Date' column exists after renaming
        if 'Date' not in data.columns:
            raise KeyError("'Date' column not found after resetting the index. Check your input data format.")

        print("Here5: After resetting index")
        print(data.columns)
        data = data.dropna().reset_index(drop=True)

        return data





    def transform(self, data):
        """
        Alias for add_features.
        """
        print("Here3")
        data = self.add_features(data)
        data.columns = data.columns.map(str)  # Ensure single-level column names

        print("Here 7")
        return data


    def calculate_rsi(self, close_prices, period=14):
        """
        Calculate the Relative Strength Index (RSI).
        """
        delta = close_prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, close_prices, window=20, num_std_dev=2):
        """
        Calculate Bollinger Bands.
        """
        sma = close_prices.rolling(window=window).mean()
        std_dev = close_prices.rolling(window=window).std()
        upper_band = sma + (std_dev * num_std_dev)
        lower_band = sma - (std_dev * num_std_dev)
        return upper_band, lower_band

    def calculate_macd(self, close_prices, short_span=12, long_span=26, signal_span=9):
        """
        Calculate MACD and Signal Line.
        """
        ema_short = close_prices.ewm(span=short_span, adjust=False).mean()
        ema_long = close_prices.ewm(span=long_span, adjust=False).mean()
        macd = ema_short - ema_long
        signal_line = macd.ewm(span=signal_span, adjust=False).mean()
        return macd, signal_line

    def calculate_atr(self, data, period=14):
        """
        Calculate Average True Range (ATR).
        """
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift(1))
        low_close = np.abs(data['Low'] - data['Close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
