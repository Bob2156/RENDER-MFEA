import discord
from discord import app_commands
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
import threading
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Discord bot setup
intents = discord.Intents.default()

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")
        await self.tree.sync()  # Sync slash commands
        logging.info("Slash commands synced.")

bot = MyBot()

# /check Command
@bot.tree.command(name="check", description="Fetches market data and provides recommendations.")
async def check(interaction: discord.Interaction):
    await interaction.response.defer()  # Acknowledge the command
    try:
        # Fetch financial data
        ticker = yf.Ticker("^GSPC")
        data = ticker.history(period="1y")
        sma_220 = round(data['Close'].rolling(window=220).mean().iloc[-1], 2)
        last_close = round(data['Close'].iloc[-1], 2)

        # Fetch 3-month Treasury rate
        URL = "https://www.cnbc.com/quotes/US3M"
        response = requests.get(URL)
        soup = BeautifulSoup(response.text, "html.parser")
        rate_element = soup.find("span", {"class": "QuoteStrip-lastPrice"})
        treasury_rate = float(rate_element.text.strip().replace('%', ''))

        # Create response embed
        embed = discord.Embed(title="Market Financial Evaluation", color=discord.Color.blue())
        embed.add_field(name="SPX Last Close", value=f"{last_close}")
        embed.add_field(name="SMA 220", value=f"{sma_220}")
        embed.add_field(name="3M Treasury Rate", value=f"{treasury_rate}%")
        embed.add_field(name="Recommendation", value="Check market trends for your strategy.")

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

# /ping Command
@bot.tree.command(name="ping", description="Sends an HTTP request to wake up the bot.")
async def ping(interaction: discord.Interaction):
    url = f"https://{os.getenv('RENDER_APP_URL')}/healthz"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            await interaction.response.send_message("The bot is awake and ready!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unexpected response from wake-up ping: {response.status_code}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error sending wake-up ping: {e}", ephemeral=True)

# Flask setup for health checks
app = Flask(__name__)

@app.route("/")
def home():
    return "The bot is running!"

@app.route("/healthz", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200

# Run Flask server in a separate thread
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Flask server
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Discord bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
