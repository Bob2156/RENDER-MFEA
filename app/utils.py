import os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

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
