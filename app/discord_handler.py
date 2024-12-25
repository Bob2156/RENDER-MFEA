from app.market_data import fetch_sma_and_volatility, fetch_treasury_rate
from app.utils import send_followup_response

def handle_ping():
    """
    Responds to Discord's PING request.
    """
    return {"type": 1}

def handle_check(data):
    """
    Handles the /check command.

    Args:
        data (dict): The incoming interaction data.

    Returns:
        dict: Acknowledgment to Discord.
    """
    interaction_token = data["token"]
    user_id = data["member"]["user"]["id"]

    # Send a follow-up response asynchronously
    from threading import Thread
    Thread(target=send_check_response, args=(interaction_token, user_id)).start()
    return {"type": 5}

def send_check_response(interaction_token, user_id):
    """
    Sends the /check response to Discord with market data.

    Args:
        interaction_token (str): Interaction token from Discord.
        user_id (str): Discord user ID.
    """
    try:
        last_close, sma_220, volatility = fetch_sma_and_volatility()
        treasury_rate = fetch_treasury_rate()

        embed = {
            "embeds": [
                {
                    "title": "Market Financial Evaluation Assistant (MFEA)",
                    "description": f"<@{user_id}>, here is the latest market data:",
                    "fields": [
                        {"name": "SPX Last Close", "value": str(last_close), "inline": True},
                        {"name": "SMA 220", "value": str(sma_220), "inline": True},
                        {"name": "Volatility (Annualized)", "value": f"{volatility}%", "inline": True},
                        {"name": "3M Treasury Rate", "value": f"{treasury_rate}%", "inline": True},
                    ],
                    "color": 5814783,
                }
            ]
        }
        send_followup_response(interaction_token, embed)
    except Exception as e:
        send_followup_response(interaction_token, {"content": f"An error occurred: {e}"})
