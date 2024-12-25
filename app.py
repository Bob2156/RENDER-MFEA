import nacl.signing
import nacl.exceptions
import threading
import requests

# Initialize Flask app
app = Flask(__name__)
@@ -36,30 +37,32 @@

# Background worker to send delayed responses
def send_followup_response(interaction_token, content):
    import requests
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"
    response = requests.post(url, json={"content": content})
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"  # Correct webhook URL
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(url, json={"content": content}, headers=headers)
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
