import os
import requests
import logging

def send_followup_response(interaction_token, payload):
    """
    Sends a follow-up response to Discord via webhook.

    Args:
        interaction_token (str): The interaction token provided by Discord.
        payload (dict): The data to send in the response.

    Raises:
        Exception: If the response fails.
    """
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        logging.info("Successfully sent follow-up response.")
    else:
        logging.error(f"Failed to send follow-up response: {response.status_code} {response.text}")
        raise Exception(f"Discord API returned {response.status_code}: {response.text}")

def verify_signature(req):
    """
    Verifies Discord's signature on incoming requests.

    Args:
        req: The Flask request object.

    Raises:
        ValueError: If the signature is invalid or missing.
    """
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError

    signature = req.headers.get("X-Signature-Ed25519")
    timestamp = req.headers.get("X-Signature-Timestamp")
    body = req.data

    if not signature or not timestamp:
        raise ValueError("Missing signature or timestamp")

    public_key = VerifyKey(bytes.fromhex(os.getenv("DISCORD_PUBLIC_KEY")))
    try:
        public_key.verify(f"{timestamp}{body.decode()}".encode(), bytes.fromhex(signature))
    except BadSignatureError:
        raise ValueError("Invalid request signature"
