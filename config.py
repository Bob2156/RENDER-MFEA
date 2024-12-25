import os

DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
DISCORD_APP_ID = os.getenv("DISCORD_APP_ID")
PORT = int(os.getenv("PORT", 8080))
