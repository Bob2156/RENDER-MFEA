import yfinance as yf
import requests
from bs4 import BeautifulSoup

def fetch_sma_and_volatility():
    ticker = yf.Ticker("^GSPC")
    data = ticker.history(period="1y")
    if data.empty or len(data) < 220:
        raise ValueError("Insufficient data to calculate SMA or volatility.")

    sma_220 = round(data['Close'].rolling(window=220).mean().iloc[-1], 2)
    last_close = round(data['Close'].iloc[-1], 2)

    recent_data = data[-30:]
    daily_returns = recent_data['Close'].pct_change().dropna()
    volatility = round(daily_returns.std() * (252 ** 0.5) * 100, 2)
    return last_close, sma_220, volatility

def fetch_treasury_rate():
    URL = "https://www.cnbc.com/quotes/US3M"
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")
    rate_element = soup.find("span", {"class": "QuoteStrip-lastPrice"})
    if rate_element:
        rate_text = rate_element.text.strip()
        if rate_text.endswith('%'):
            return round(float(rate_text[:-1]), 2)
    raise ValueError("Failed to fetch treasury rate.")
