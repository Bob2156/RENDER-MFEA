from flask import Flask, request, jsonify
import threading
from utils import verify_signature, send_followup_response, fetch_sma_and_volatility, fetch_treasury_rate
import logging

app = Flask(__name__)

@app.route("/", methods=["POST"])
def handle_interaction():
    try:
        verify_signature(request)
    except ValueError as e:
        logging.error(f"Verification failed: {e}")
        return jsonify({"error": "Invalid request signature"}), 401

    data = request.json
    logging.info(f"Received interaction: {data}")

    if data.get("type") == 1:  # PING
        logging.info("Responding to PING.")
        return jsonify({"type": 1})

    if data.get("type") == 2:  # Slash commands
        command_name = data["data"]["name"]
        interaction_token = data["token"]
        user_id = data["member"]["user"]["id"]

        if command_name == "ping":
            threading.Thread(target=send_followup_response, args=(interaction_token, {"content": "The bot is awake and ready!"})).start()
            return jsonify({"type": 5})

        elif command_name == "check":
            threading.Thread(target=fetch_and_respond_check, args=(interaction_token, user_id)).start()
            return jsonify({"type": 5})

    return jsonify({"error": "Unknown command"}), 400

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

        send_followup_response(interaction_token, embed)
    except Exception as e:
        logging.error(f"Error in /check: {e}")
        send_followup_response(interaction_token, {"content": f"<@{user_id}>, an error occurred: {e}"})

@app.route("/healthz", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
