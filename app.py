import discord
from discord.ext import commands
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
import threading
import time
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")

# Helper function to fetch SMA and volatility
def fetch_sma_and_volatility():
    try:
        ticker = yf.Ticker("^GSPC")  # S&P 500 Index
        data = ticker.history(period="1y")  # Get 1 year of data

        if data.empty or len(data) < 220:
            raise ValueError("Insufficient data to calculate SMA or volatility.")

        sma_220 = round(data['Close'].rolling(window=220).mean().iloc[-1], 2)
        last_close = round(data['Close'].iloc[-1], 2)

        # Calculate 30-day volatility
        recent_data = data[-30:]
        if len(recent_data) < 30:
            raise ValueError("Insufficient data for volatility calculation.")
        daily_returns = recent_data['Close'].pct_change().dropna()
        volatility = round(daily_returns.std() * (252**0.5) * 100, 2)

        return last_close, sma_220, volatility
    except Exception as e:
        raise ValueError(f"Error fetching SMA and volatility: {e}")

# Helper function to fetch treasury rate
def fetch_treasury_rate():
    try:
        URL = "https://www.cnbc.com/quotes/US3M"
        response = requests.get(URL)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            rate_element = soup.find("span", {"class": "QuoteStrip-lastPrice"})
            if rate_element:
                rate_text = rate_element.text.strip()
                if rate_text.endswith('%'):
                    return round(float(rate_text[:-1]), 2)
        raise ValueError("Failed to fetch treasury rate.")
    except Exception as e:
        raise ValueError(f"Error fetching treasury rate: {e}")

# !check Command
@bot.command()
async def check(ctx):
    await ctx.send("Fetching data... Please wait.")
    try:
        last_close, sma_220, volatility = fetch_sma_and_volatility()
        treasury_rate = fetch_treasury_rate()

        embed = discord.Embed(title="Market Financial Evaluation Assistant (MFEA)", color=discord.Color.blue())
        embed.add_field(name="SPX Last Close", value=f"{last_close}", inline=False)
        embed.add_field(name="SMA 220", value=f"{sma_220}", inline=False)
        embed.add_field(name="Volatility (Annualized)", value=f"{volatility}%", inline=False)
        embed.add_field(name="3M Treasury Rate", value=f"{treasury_rate}%", inline=False)

        # Recommendation logic
        if last_close > sma_220:
            if volatility < 14:
                recommendation = "Risk ON - 100% UPRO or 3x (100% SPY)"
            elif volatility < 24:
                recommendation = "Risk MID - 100% SSO or 2x (100% SPY)"
            else:
                recommendation = (
                    "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
                    if treasury_rate and treasury_rate < 4
                    else "Risk OFF - 100% SPY or 1x (100% SPY)"
                )
        else:
            recommendation = (
                "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
                if treasury_rate and treasury_rate < 4
                else "Risk OFF - 100% SPY or 1x (100% SPY)"
            )

        embed.add_field(name="MFEA Recommendation", value=recommendation, inline=False)
        await ctx.send(embed=embed)
    except ValueError as e:
        await ctx.send(f"Error: {e}")
    except Exception as e:
        await ctx.send(f"Unexpected error: {e}")

# Flask setup for health checks and wake-up pings
app = Flask(__name__)

@app.route("/")
def home():
    return "The bot is running!"

@app.route("/healthz", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200

# /ping Command for Discord to send HTTP requests
@bot.command()
async def ping(ctx):
    url = f"https://{os.getenv('RENDER_APP_URL')}/healthz"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            await ctx.send("The bot is awake and ready!")
        else:
            await ctx.send(f"Unexpected response from wake-up ping: {response.status_code}")
    except Exception as e:
        await ctx.send(f"Error sending wake-up ping: {e}")

# Run Flask server in a separate thread
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Discord bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
