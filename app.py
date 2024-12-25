import os
import logging
import requests
from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import yfinance as yf
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import asyncio
import threading

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Initialize Flask app
app = Flask(__name__)

# Discord client setup
intents = discord.Intents.default()
intents.messages = True
client = commands.Bot(command_prefix="!", intents=intents)

# Function to verify Discord's signature
def verify_signature(req):
    signature = req.headers.get("X-Signature-Ed25519")
    timestamp = req.headers.get("X-Signature-Timestamp")
    body = req.data

    if not signature or not timestamp:
        raise ValueError("Missing signature or timestamp")

    public_key = VerifyKey(bytes.fromhex(os.getenv("DISCORD_PUBLIC_KEY")))
    try:
        public_key.verify(f"{timestamp}{body.decode()}".encode(), bytes.fromhex(signature))
    except BadSignatureError:
        raise ValueError("Invalid request signature")

# Background worker to send delayed responses
def send_followup_response(interaction_token, payload):
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        logging.info("Successfully sent follow-up response.")
    else:
        logging.error(f"Failed to send follow-up response: {response.status_code} {response.text}")

# Fetch SMA and volatility
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

# Fetch treasury rate
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

# Function to send a startup message to Discord
async def send_startup_message():
    try:
        bot_token = os.getenv("DISCORD_BOT_TOKEN")
        channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))  # Channel ID to send the message
        if not bot_token or not channel_id:
            logging.error("Bot token or channel ID is not set in environment variables.")
            return

        await client.login(bot_token)
        channel = await client.fetch_channel(channel_id)
        messages = []
        async for message in channel.history(limit=1):
            messages.append(message)

        if messages:
            last_user = messages[0].author.mention
            await channel.send(f"{last_user}, bot is online now!")
        else:
            await channel.send("Bot is online now!")

        logging.info("Startup message sent successfully.")
    except Exception as e:
        logging.error(f"Error sending startup message: {e}")
    finally:
        await client.close()

# Route to handle Discord interactions
@app.route("/", methods=["POST"])
def handle_interaction():
    # Verify the request
    try:
        verify_signature(request)
    except ValueError as e:
        logging.error(f"Verification failed: {e}")
        return jsonify({"error": "Invalid request signature"}), 401

    # Parse the JSON payload
    data = request.json
    logging.info(f"Received interaction: {data}")

    # Handle PING (Discord's interaction endpoint validation)
    if data.get("type") == 1:
        logging.info("Responding to PING.")
        return jsonify({"type": 1})

    # Handle slash commands
    if data.get("type") == 2:
        command_name = data["data"]["name"]
        interaction_token = data["token"]
        user_id = data["member"]["user"]["id"]  # Extract user ID for ping

        # Handle /ping command
        if command_name == "ping":
            threading.Thread(target=send_followup_response, args=(interaction_token, {"content": "The bot is awake and ready!"})).start()
            return jsonify({"type": 5})  # Acknowledge the command

        # Handle /check command
        elif command_name == "check":
            threading.Thread(target=fetch_and_respond_check, args=(interaction_token, user_id)).start()
            return jsonify({"type": 5})  # Acknowledge the command

    # Default response for unknown commands
    return jsonify({"error": "Unknown command"}), 400

# Fetch market data and send response for /check
def fetch_and_respond_check(interaction_token, user_id):
    try:
        last_close, sma_220, volatility = fetch_sma_and_volatility()
        treasury_rate = fetch_treasury_rate()

        embed = {
            "embeds": [
                {
                    "title": "Market Financial Evaluation Assistant (MFEA)",
                    "description": f"<@{user_id}>, here is the latest market data:",
                    "fields": [
                        {"name": "SPX Last Close", "value": f"{last_close}", "inline": True},
                        {"name": "SMA 220", "value": f"{sma_220}", "inline": True},
                        {"name": "Volatility (Annualized)", "value": f"{volatility}%", "inline": True},
                        {"name": "3M Treasury Rate", "value": f"{treasury_rate}%", "inline": True}
                    ],
                    "color": 5814783
                }
            ]
        }

        # Determine strategy
        if last_close > sma_220:
            if volatility < 14:
                strategy = "Risk ON - 100% UPRO or 3x (100% SPY)"
            elif volatility < 24:
                strategy = "Risk MID - 100% SSO or 2x (100% SPY)"
            else:
                if treasury_rate and treasury_rate < 4:
                    strategy = "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
                else:
                    strategy = "Risk OFF - 100% SPY or 1x (100% SPY)"
        else:
            if treasury_rate and treasury_rate < 4:
                strategy = "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
            else:
                strategy = "Risk OFF - 100% SPY or 1x (100% SPY)"

        embed["embeds"][0]["fields"].append({"name": "Investment Strategy", "value": strategy, "inline": False})

        send_followup_response(interaction_token, embed)
    except Exception as e:
        logging.error(f"Error in /check: {e}")
        send_followup_response(interaction_token, {"content": f"<@{user_id}>, an error occurred: {e}"})

# Flask health check endpoint
@app.route("/healthz", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200

# Start Flask server
if __name__ == "__main__":
    # Send startup message
    asyncio.run(send_startup_message())

    # Start Flask app
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
