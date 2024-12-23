import requests
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
    ]
)

# Groq API variables
GROQ_API_KEY = ""
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Initialize global variables for over-episode risk
cumulative_risk = {
    "total_drawdown": 0,
    "max_drawdown": 0,
    "total_pnl": 0,
    "episodes_tracked": 0,
}

# Prepare data
def format_data_for_prompt(data):
    """
    Formats historical stock data into a concise, readable format for the LLaMA model.
    Handles column names in a case-insensitive manner.
    """
    # Convert column names to lowercase for case-insensitive access

    logging.info("Format data")
    data = data.rename(columns=str.lower)

    logging.info(f"data lower{data}")

    formatted_data = ""
    for index, row in data.iterrows():

        logging.info(f"Row has {row}")
        formatted_data += (
            f"Date: {row['date']}, Open: {row['open']}, High: {row['high']}, "
            f"Low: {row['low']}, Close: {row['close']}, Volume: {row['volume']}, "
            f" RSI: {row['rsi']}, "
            f"MACD: {row['macd']}, Signal_Line: {row['signal_line']}, ATR: {row['atr']}\n"
        )
    return formatted_data


# Risk Management Calculation
def calculate_risk_metrics(live_data,hist_data):
    """
    Computes risk metrics for decision-making.
    """

    logging.info(f"This is live data{live_data}")
    latest_data = live_data
    logging.info(f"This is live data{latest_data}")

    volatility=hist_data['ATR'].mean()
    logging.info(f"This is volatility{volatility}")
    current_atr=latest_data['ATR'].iloc[0]
    logging.info(f"This is atr{current_atr}")
    rsi=latest_data['RSI'].iloc[0]
    logging.info(f"This is rsi{rsi}")
    position_sizing=max(0.01, min(0.05, 1 / current_atr))  
    logging.info(f"This is position sizing {position_sizing}")
    

    hist_risk = {
        "volatility": volatility,  # Average True Range for historical data
        "current_atr":current_atr,      # Current ATR
        "rsi": rsi,             # RSI value
        "position_sizing":position_sizing
    }

    logging.info(f"Done {hist_risk}")
    return hist_risk


# Within-Episode Risk Management
def manage_within_episode_risk(live_data, risk_metrics):
    """
    Adjusts trading actions based on real-time risks within the current episode.
    """
    rsi = risk_metrics["rsi"]
    current_atr = risk_metrics["current_atr"]

    # Example rules
    if rsi > 70:
        return "Sell - Overbought conditions detected"
    elif rsi < 30:
        return "Buy - Oversold conditions detected"
    elif current_atr > risk_metrics["volatility"] * 1.5:
        return "Hold - High volatility, minimize risk"
    return "Proceed with decision"


# Over-Episode Risk Management
def manage_over_episode_risk(pnl, drawdown):
    """
    Tracks cumulative risks and adjusts future trades based on overall performance.
    """
    global cumulative_risk

    # Ensure the cumulative_risk dictionary is initialized
    if 'cumulative_risk' not in globals() or not isinstance(cumulative_risk, dict):
        cumulative_risk = {
            "total_drawdown": 0.0,
            "total_pnl": 0.0,
            "episodes_tracked": 0,
            "max_drawdown": 0.0
        }

    # Update cumulative risk metrics
    cumulative_risk["total_drawdown"] += drawdown
    cumulative_risk["total_pnl"] += pnl
    cumulative_risk["episodes_tracked"] += 1
    cumulative_risk["max_drawdown"] = max(cumulative_risk["max_drawdown"], drawdown)

    # Risk management decision rules
    if cumulative_risk["total_drawdown"] > 0.2:  # Example: 20% overall drawdown
        return "Pause Trading - Excessive drawdown detected"
    elif cumulative_risk["total_pnl"] < 0:  # Example: Negative PnL over multiple episodes
        return "Adjust Strategy - Overall losses detected"
    else:
        return "Continue Trading - Within acceptable risk"


# Generate prompt with risk management
def generate_prompt(answer, hist_data, live_data, decision, risk_metrics, within_episode_risk,over_episode_risk):
    logging.info(f"Inside prompt")
    historical_data = format_data_for_prompt(hist_data)
    live_data = format_data_for_prompt(live_data)

    prompt = (
        f"### Historical Stock Data\n"
        f"The following historical data has been observed for the stock over the last 5 intervals:\n"
        f"{historical_data}\n\n"
        
        f"### Live Stock Data\n"
        f"The most recent live stock data available is:\n"
        f"{live_data}\n\n"
        
        f"### Analysis from FinGPT\n"
        f"FinGPT has analyzed the market data, trends, and financials and provided the following insights:\n"
        f"{answer}\n\n"
        
        f"### Sentiment Decision from FinBERT\n"
        f"Based on the sentiment analysis of recent news, the decision for this stock is to: **{decision.upper()}**.\n"
        f"If the decision is to buy, it means the sentiment suggests a bullish outlook. If the decision is to sell, "
        f"it indicates a bearish sentiment. A hold decision suggests neutral sentiment or market uncertainty.\n\n"
        
        f"### Risk Management Metrics\n"
        f"Here are the risk management metrics computed based on historical and live data:\n"
        f"- Average Volatility (ATR): {risk_metrics['volatility']:.2f}\n"
        f"- Current Volatility (ATR): {risk_metrics['current_atr']:.2f}\n"
        f"- RSI: {risk_metrics['rsi']:.2f}\n"
        f"- Recommended Position Sizing (as % of capital): {risk_metrics['position_sizing']*100:.2f}%\n\n"

        f"### Within-Episode Risk Management\n"
        f"The following risk adjustment has been suggested within the current trading episode:\n"
        f"{within_episode_risk}\n\n"

        f"### Over Episode Risk Management\n"
        f"The following risk adjustment has been suggested within the current trading episode:\n"
        f"{over_episode_risk}\n\n"
        
        f"### Decision Context\n"
        f"Using the provided historical data, live data, FinGPT analysis, sentiment decision, and risk metrics, determine the optimal "
        f"action for the stock. Consider risk management factors like volatility, moving averages, RSI, and ATR. "
        f"Your response should include the following details:\n"
        f"1. A confirmation of the suggested action (Buy, Sell, Hold).\n"
        f"2. A justification for the decision based on trends, momentum indicators, and sentiment.\n"
        f"3. Specific details on how long to hold if buying, or at what price levels to sell if selling.\n"
        f"4. Any additional insights about the stock's expected performance in the near term.\n\n"
        
        f"### Task\n"
        f"Provide a detailed response with a structured explanation, aligning the decision with the data provided. "
        f"Your response should be actionable and data-driven, offering precise recommendations for the trading bot to execute."
    )
    return prompt




# Send request to Groq API
# def get_prediction(prompt):
#     headers = {
#         "Authorization": f"Bearer {GROQ_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "model": "llama3-8b-8192",  # Specify the LLaMA model
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": 0.7,  # Adjust for variability
#         "max_tokens": 500
#     }
    
#     response = requests.post(GROQ_URL, headers=headers, json=payload)
#     if response.status_code == 200:
#         return response.json()["choices"][0]["message"]["content"]
#     else:
#         print("Error:", response.json())
#         return None

def get_prediction(prompt, retries=3):
    """
    Sends a prompt to the Groq API and retrieves the model's prediction.
    
    Args:
        prompt (str): The prompt to send to the API.
        retries (int): Number of retry attempts in case of failure (default: 3).
    
    Returns:
        str: The content of the response from the API, or None if an error occurs.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",  # Specify the LLaMA model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,  # Adjust for variability
        
    }
    logging.info(f"In prediction{prompt}")

    for attempt in range(retries):
        try:
            logging.info(f"Sending request to Groq API. Attempt {attempt + 1} of {retries}...")
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=10)

            # Check for a successful response
            if response.status_code == 200:
                response_content = response.json()
                logging.debug(f"Groq API response: {response_content}")
                return response_content["choices"][0]["message"]["content"]
            else:
                # Log the error details
                error_details = response.json()
                logging.error(f"Groq API Error - Status Code: {response.status_code}, Details: {error_details}")

        except requests.exceptions.Timeout:
            logging.error("Request timed out. Retrying...")
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred while connecting to the Groq API: {e}")

    logging.error("Exceeded maximum retries. Unable to get a prediction.")
    return None