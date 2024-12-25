from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Discord Bot Token and Public Key
DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


@app.route("/", methods=["POST"])
def handle_interaction():
    # Handle the interaction from Discord
    data = request.json

    # Respond to the `/check` command
    if data.get("type") == 2:  # Interaction type 2 = ApplicationCommand
        if data["data"]["name"] == "check":
            return jsonify({
                "type": 4,  # Response type 4 = Channel Message With Source
                "data": {
                    "content": "working"
                }
            })

    return jsonify({"type": 1})  # Default acknowledgment


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
