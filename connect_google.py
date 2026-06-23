"""
One-time setup script to connect your Google Calendar account to Composio.
Run this once, visit the URL it prints, and authorize with your Google account.
After that, the scheduling agent will be able to create events.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from composio import Composio
from composio_langchain import LangchainProvider

provider = LangchainProvider()
client = Composio(provider=provider)

print("Checking for existing Google Calendar connections...")

try:
    # Try to initiate a new connection
    connection = client.connected_accounts.initiate(
        user_id="default",
        toolkit="googlecalendar",
    )
    
    # The connection object should have a redirect URL
    if hasattr(connection, 'redirect_url'):
        print(f"\nPlease visit this URL to authorize Google Calendar:\n{connection.redirect_url}")
    elif hasattr(connection, 'redirectUrl'):
        print(f"\nPlease visit this URL to authorize Google Calendar:\n{connection.redirectUrl}")
    elif hasattr(connection, 'url'):
        print(f"\nPlease visit this URL to authorize Google Calendar:\n{connection.url}")
    else:
        # Print all attributes to find the URL
        print(f"\nConnection response: {connection}")
        if isinstance(connection, dict):
            for k, v in connection.items():
                print(f"  {k}: {v}")
        else:
            for attr in dir(connection):
                if not attr.startswith('_'):
                    print(f"  {attr}: {getattr(connection, attr, 'N/A')}")
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying alternative method...")
    
    try:
        # Try the connected_accounts resource directly
        print(f"\nAvailable methods on client: {[m for m in dir(client) if not m.startswith('_')]}")
    except Exception as e2:
        print(f"Alternative also failed: {e2}")

print("\nAfter authorizing, restart cli.py and try scheduling again.")
