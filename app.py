import os
import logging
from flask import Flask, request, jsonify, abort
import nacl.signing
import nacl.exceptions
import threading

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
if not DISCORD_PUBLIC_KEY:
    raise ValueError("DISCORD_PUBLIC_KEY is not set in environment variables.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Function to verify request signature from Discord
def verify_signature(req):
    signature = req.headers.get("X-Signature-Ed25519")
    timestamp = req.headers.get("X-Signature-Timestamp")
    body = req.get_data(as_text=True)

    if not signature or not timestamp:
        logging.error("Missing signature or timestamp in headers.")
        abort(401, "Missing signature or timestamp")

    try:
        verify_key = nacl.signing.VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
    except nacl.exceptions.BadSignatureError:
        logging.error("Invalid request signature.")
        abort(401, "Invalid request signature")


# Background worker to send delayed responses
def send_followup_response(interaction_token, content):
    import requests
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"
    response = requests.post(url, json={"content": content})
    if response.status_code == 200:
        logging.info("Successfully sent follow-up response.")
    else:
        logging.error(f"Failed to send follow-up response: {response.status_code} {response.text}")


# Route to handle Discord interactions
@app.route("/", methods=["POST"])
def handle_interaction():
    # Verify the request
    verify_signature(request)

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
        interaction_token = data["token"]  # For follow-up responses
        logging.info(f"Command received: {command_name}")

        if command_name == "check":
            # Send a deferred response immediately
            logging.info("Acknowledging the /check command.")
            threading.Thread(target=send_followup_response, args=(interaction_token, "working")).start()
            return jsonify({
                "type": 5  # Acknowledge the command and defer the response
            })

    # Default fallback
    logging.warning("Unhandled interaction type.")
    return jsonify({"type": 1})


# Main entry point
if __name__ == "__main__":
    # Ensure PORT is set for Render
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
