"""Inspect the exact schema of GOOGLECALENDAR_CREATE_EVENT - just required + top-level fields."""
from dotenv import load_dotenv
load_dotenv()

import os, json
from composio import Composio
from composio_langchain import LangchainProvider

provider = LangchainProvider()
client = Composio(provider=provider)
uid = os.environ["COMPOSIO_USER_ID"]
tools = client.tools.get(user_id=uid, tools=["GOOGLECALENDAR_CREATE_EVENT"])

tool = tools[0]
print("Tool name:", tool.name)
schema = tool.args_schema.model_json_schema()

# Print just the required fields and their descriptions
required = schema.get("required", [])
props = schema.get("properties", {})
print("\nREQUIRED fields:", required)
print("\nALL fields with descriptions:")
for k, v in props.items():
    desc = v.get("description", "")[:120]
    default = v.get("default", "NO DEFAULT")
    print(f"  {k} (default={default}): {desc}")
