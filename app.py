import os
import logging
import requests
from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import threading
import yfinance as yf
from bs4 import BeautifulSoup

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Initialize Flask app
app = Flask(__name__)

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
def send_followup_response(interaction_token, content):
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(url, json={"content": content}, headers=headers)
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

        # Handle /ping command
        if command_name == "ping":
            threading.Thread(target=send_followup_response, args=(interaction_token, "The bot is awake and ready!")).start()
            return jsonify({"type": 5})  # Acknowledge the command

        # Handle /check command
        elif command_name == "check":
            threading.Thread(target=fetch_and_respond_check, args=(interaction_token,)).start()
            return jsonify({"type": 5})  # Acknowledge the command

    # Default response for unknown commands
    return jsonify({"error": "Unknown command"}), 400

# Fetch market data and send response for /check
def fetch_and_respond_check(interaction_token):
    try:
        last_close, sma_220, volatility = fetch_sma_and_volatility()
        treasury_rate = fetch_treasury_rate()

        content = (
            f"**Market Financial Evaluation Assistant (MFEA)**\n"
            f"SPX Last Close: {last_close}\n"
            f"SMA 220: {sma_220}\n"
            f"Volatility (Annualized): {volatility}%\n"
            f"3M Treasury Rate: {treasury_rate}%\n"
        )
        send_followup_response(interaction_token, content)
    except Exception as e:
        logging.error(f"Error in /check: {e}")
        send_followup_response(interaction_token, f"An error occurred: {e}")

# Flask health check endpoint
@app.route("/healthz", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200

# Start Flask server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
