"""Quick smoke test: verifies the entity_id is correct and the GOOGLECALENDAR_CREATE_EVENT tool loads."""
from dotenv import load_dotenv
load_dotenv()

import os
from composio import Composio
from composio_langchain import LangchainProvider

user_id = os.environ.get("COMPOSIO_USER_ID")
print(f"COMPOSIO_USER_ID = {user_id}")

if not user_id:
    print("❌ COMPOSIO_USER_ID not set in .env!")
else:
    provider = LangchainProvider()
    client = Composio(provider=provider)
    tools = client.tools.get(user_id=user_id, tools=["GOOGLECALENDAR_CREATE_EVENT"])
    print(f"✅ Loaded {len(tools)} tool(s): {[t.name for t in tools]}")
    print("Scheduling agent is ready to use!")
