import os
import re
import time
import json
import random
import finnhub
import torch
import gradio as gr
import pandas as pd
import yfinance as yf 
from pynvml import *
from peft import PeftModel
from collections import defaultdict
from datetime import date, datetime, timedelta
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer


access_token = ""
finnhub_client = finnhub.Client(api_key="")

base_model = AutoModelForCausalLM.from_pretrained(
    'meta-llama/Llama-2-7b-chat-hf',
    use_auth_token=access_token,  # Use `use_auth_token` for CPU if access_token is provided
    trust_remote_code=True,
    offload_folder="offload/"  # Offloading to disk for memory constraints
)

# Load the PEFT model on top of the base model
model = PeftModel.from_pretrained(
    base_model,
    'FinGPT/fingpt-forecaster_dow30_llama2-7b_lora',
    offload_folder="offload/"  # Ensure offload_folder is available if needed
)
model = model.eval()

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    'meta-llama/Llama-2-7b-chat-hf',
    use_auth_token=access_token
)

# Explicitly set model and tokenizer to CPU
model.to('cpu')
streamer = TextStreamer(tokenizer)

B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"

SYSTEM_PROMPT = "You are a seasoned stock market analyst. Your task is to list the positive developments and potential concerns for companies based on relevant news and basic financials from the past weeks, then provide an analysis and prediction for the companies' stock price movement for the upcoming week. " \
    "Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Prediction & Analysis]\nPrediction: ...\nAnalysis: ..."


def print_gpu_utilization():
    
    nvmlInit()
    handle = nvmlDeviceGetHandleByIndex(0)
    info = nvmlDeviceGetMemoryInfo(handle)
    print(f"GPU memory occupied: {info.used//1024**2} MB.")


def get_curday():
    
    return date.today().strftime("%Y-%m-%d")


def n_weeks_before(date_string, n):
    
    date = datetime.strptime(date_string, "%Y-%m-%d") - timedelta(days=7*n)

    return date.strftime("%Y-%m-%d")


def get_stock_data(stock_symbol, steps):
    # Download stock data
    stock_data = yf.download(stock_symbol, steps[0], steps[-1])
    
    # Check if data is empty
    if stock_data.empty:
        raise gr.Error(f"Failed to download stock price data for symbol {stock_symbol} from yfinance!")
    
    # Ensure the 'Close' column exists
    if 'Close' not in stock_data.columns:
        raise gr.Error(f"The 'Close' column is missing from the stock data for symbol {stock_symbol}!")
    
    # Initialize dates and prices
    dates, prices = [], []
    available_dates = stock_data.index.astype(str).tolist()  # Convert index to string
    
    for date in steps[:-1]:
        # Find the closest available date >= current step date
        for available_date in available_dates:
            if available_date >= date:
                prices.append(stock_data.loc[available_date, 'Close'])  # Use .loc for label-based indexing
                dates.append(datetime.strptime(available_date, "%Y-%m-%d"))
                break
        else:
            raise gr.Error(f"No data available for the date: {date}")
    
    # Add the final date and price
    final_date = available_dates[-1]
    dates.append(datetime.strptime(final_date, "%Y-%m-%d"))
    prices.append(stock_data.loc[final_date, 'Close'])
    
    # Return as a DataFrame
    return pd.DataFrame({
        "Start Date": dates[:-1],
        "End Date": dates[1:],
        "Start Price": prices[:-1],
        "End Price": prices[1:]
    })


def get_news(symbol, data):
    
    news_list = []
    
    for end_date, row in data.iterrows():
        start_date = row['Start Date'].strftime('%Y-%m-%d')
        end_date = row['End Date'].strftime('%Y-%m-%d')
#         print(symbol, ': ', start_date, ' - ', end_date)
        time.sleep(1) # control qpm
        weekly_news = finnhub_client.company_news(symbol, _from=start_date, to=end_date)
        if len(weekly_news) == 0:
            raise gr.Error(f"No company news found for symbol {symbol} from finnhub!")
        weekly_news = [
            {
                "date": datetime.fromtimestamp(n['datetime']).strftime('%Y%m%d%H%M%S'),
                "headline": n['headline'],
                "summary": n['summary'],
            } for n in weekly_news
        ]
        weekly_news.sort(key=lambda x: x['date'])
        news_list.append(json.dumps(weekly_news))
    
    data['News'] = news_list
    
    return data


def get_company_prompt(symbol):

    profile = finnhub_client.company_profile2(symbol=symbol)
    if not profile:
        raise gr.Error(f"Failed to find company profile for symbol {symbol} from finnhub!")
        
    company_template = "[Company Introduction]:\n\n{name} is a leading entity in the {finnhubIndustry} sector. Incorporated and publicly traded since {ipo}, the company has established its reputation as one of the key players in the market. As of today, {name} has a market capitalization of {marketCapitalization:.2f} in {currency}, with {shareOutstanding:.2f} shares outstanding." \
        "\n\n{name} operates primarily in the {country}, trading under the ticker {ticker} on the {exchange}. As a dominant force in the {finnhubIndustry} space, the company continues to innovate and drive progress within the industry."

    formatted_str = company_template.format(**profile)
    
    return formatted_str


def get_prompt_by_row(symbol, row):
    # Print row for debugging
    print(row)
    print(type(row))

    # Dynamically extract ticker from the nested Series
    if isinstance(row['Start Price'], pd.Series):
        start_price = row['Start Price'].iloc[0]  # Extract the first value dynamically
    else:
        start_price = row['Start Price']

    if isinstance(row['End Price'], pd.Series):
        end_price = row['End Price'].iloc[0]  # Extract the first value dynamically
    else:
        end_price = row['End Price']

    print(f"End Price: {end_price}")
    print(f"Start Price: {start_price}")

    # Check for missing values
    if pd.isnull(end_price) or pd.isnull(start_price):
        raise gr.Error(f"Missing price data for symbol {symbol} in row: {row}")

    # Use scalar comparison
    term = 'increased' if end_price > start_price else 'decreased'

    # Format the dates
    start_date = row['Start Date'] if isinstance(row['Start Date'], str) else row['Start Date'].strftime('%Y-%m-%d')
    end_date = row['End Date'] if isinstance(row['End Date'], str) else row['End Date'].strftime('%Y-%m-%d')

    # Build the prompt
    head = f"From {start_date} to {end_date}, {symbol}'s stock price {term} from {start_price:.2f} to {end_price:.2f}. Company news during this period are listed below:\n\n"

    # Extract and format news
    news = json.loads(row["News"])
    news = [
        f"[Headline]: {n['headline']}\n[Summary]: {n['summary']}\n"
        for n in news
        if n['date'][:8] <= end_date.replace('-', '') and not n['summary'].startswith("Looking for stock market analysis and research with proven results?")
    ]

    # Extract and format basics
    basics = json.loads(row['Basics'])
    if basics:
        basics = (
            f"Some recent basic financials of {symbol}, reported at {basics['period']}, are presented below:\n\n[Basic Financials]:\n\n"
            + "\n".join(f"{k}: {v}" for k, v in basics.items() if k != 'period')
        )
    else:
        basics = "[Basic Financials]:\n\nNo basic financial reported."

    return head, news, basics




def sample_news(news, k=5):
    
    return [news[i] for i in sorted(random.sample(range(len(news)), k))]


def get_current_basics(symbol, curday):

    basic_financials = finnhub_client.company_basic_financials(symbol, 'all')
    if not basic_financials['series']:
        raise gr.Error(f"Failed to find basic financials for symbol {symbol} from finnhub!")
        
    final_basics, basic_list, basic_dict = [], [], defaultdict(dict)
    
    for metric, value_list in basic_financials['series']['quarterly'].items():
        for value in value_list:
            basic_dict[value['period']].update({metric: value['v']})

    for k, v in basic_dict.items():
        v.update({'period': k})
        basic_list.append(v)
        
    basic_list.sort(key=lambda x: x['period'])
    
    for basic in basic_list[::-1]:
        if basic['period'] <= curday:
            break
            
    return basic
    

def get_all_prompts_online(symbol, data, curday, with_basics=True):

    company_prompt = get_company_prompt(symbol)

    prev_rows = []

    for row_idx, row in data.iterrows():
        head, news, _ = get_prompt_by_row(symbol, row)
        prev_rows.append((head, news, None))
        
    prompt = ""
    for i in range(-len(prev_rows), 0):
        prompt += "\n" + prev_rows[i][0]
        sampled_news = sample_news(
            prev_rows[i][1],
            min(5, len(prev_rows[i][1]))
        )
        if sampled_news:
            prompt += "\n".join(sampled_news)
        else:
            prompt += "No relative news reported."
        
    period = "{} to {}".format(curday, n_weeks_before(curday, -1))
    
    if with_basics:
        basics = get_current_basics(symbol, curday)
        basics = "Some recent basic financials of {}, reported at {}, are presented below:\n\n[Basic Financials]:\n\n".format(
            symbol, basics['period']) + "\n".join(f"{k}: {v}" for k, v in basics.items() if k != 'period')
    else:
        basics = "[Basic Financials]:\n\nNo basic financial reported."

    info = company_prompt + '\n' + prompt + '\n' + basics
    prompt = info + f"\n\nBased on all the information before {curday}, let's first analyze the positive developments and potential concerns for {symbol}. Come up with 2-4 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Then make your prediction of the {symbol} stock price movement for next week ({period}). Provide a summary analysis to support your prediction."
        
    return info, prompt


def construct_prompt(ticker, curday, n_weeks, use_basics):

    try:
        steps = [n_weeks_before(curday, n) for n in range(n_weeks + 1)][::-1]
    except Exception:
        raise gr.Error(f"Invalid date {curday}!")
        
    data = get_stock_data(ticker, steps)
    data = get_news(ticker, data)
    data['Basics'] = [json.dumps({})] * len(data)
    # print(data)
    
    info, prompt = get_all_prompts_online(ticker, data, curday, use_basics)
    
    prompt = B_INST + B_SYS + SYSTEM_PROMPT + E_SYS + prompt + E_INST
    # print(prompt)
    
    return info, prompt


def predict(ticker, date, n_weeks, use_basics):

    print_gpu_utilization()

    

    info, prompt = construct_prompt(ticker, date, n_weeks, use_basics)
      
    inputs = tokenizer(
        prompt, return_tensors='pt', padding=False
    )
    inputs = {key: value.to(model.device) for key, value in inputs.items()}

    print("Inputs loaded onto devices.")
        
    res = model.generate(
        **inputs, max_length=4096, do_sample=True,
        eos_token_id=tokenizer.eos_token_id,
        use_cache=True, streamer=streamer
    )
    output = tokenizer.decode(res[0], skip_special_tokens=True)
    answer = re.sub(r'.*\[/INST\]\s*', '', output, flags=re.DOTALL)

    torch.cuda.empty_cache()
    
    return info, answer


demo = gr.Interface(
    predict,
    inputs=[
        gr.Textbox(
            label="Ticker",
            value="AAPL",
            info="Companys from Dow-30 are recommended"
        ),
        gr.Textbox(
            label="Date",
            value=get_curday,
            info="Date from which the prediction is made, use format yyyy-mm-dd"
        ),
        gr.Slider(
            minimum=1,
            maximum=4,
            value=3,
            step=1,
            label="n_weeks",
            info="Information of the past n weeks will be utilized, choose between 1 and 4"
        ),
        gr.Checkbox(
            label="Use Latest Basic Financials",
            value=False,
            info="If checked, the latest quarterly reported basic financials of the company is taken into account."
        )
    ],
    outputs=[
        gr.Textbox(
            label="Information"
        ),
        gr.Textbox(
            label="Response"
        )
    ],
    title="FinGPT-Forecaster",
    description="""
**Disclaimer: Nothing herein is financial advice, and NOT a recommendation to trade real money. Please use common sense and always first consult a professional before trading or investing.**
"""
)

demo.launch()