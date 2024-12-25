from flask import Blueprint, request, jsonify
from app.utils import verify_signature
from app.discord_handler import handle_ping, handle_check

routes = Blueprint("routes", __name__)

@routes.route("/", methods=["POST"])
def interaction_handler():
    try:
        verify_signature(request)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    data = request.json

    if data.get("type") == 1:  # PING
        return handle_ping()
    elif data.get("type") == 2:  # Slash commands
        command_name = data["data"]["name"]
        if command_name == "ping":
            return handle_ping()
        elif command_name == "check":
            return handle_check(data)
    return jsonify({"error": "Unknown command"}), 400
