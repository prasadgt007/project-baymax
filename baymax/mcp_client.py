import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .models import PatientProfile

# Synchronous wrapper for MCP client
def fetch_patient_profile_mcp(patient_id: str):
    async def _fetch():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(base_dir, "database_mcp_server.py")
        
        server_params = StdioServerParameters(
            command="python",
            args=[server_path],
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call the tool
                result = await session.call_tool("get_patient_profile", arguments={"patient_id": patient_id})
                
                # Result is typically a list of content objects
                if result.content and len(result.content) > 0:
                    json_str = result.content[0].text
                    if json_str == "{}":
                        return None
                    return PatientProfile.model_validate_json(json_str)
                return None
                
    return asyncio.run(_fetch())

def search_interactions_mcp(patient_id: str, query: str, limit: int = 3):
    async def _search():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(base_dir, "database_mcp_server.py")
        
        server_params = StdioServerParameters(
            command="python",
            args=[server_path],
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(
                    "search_interactions", 
                    arguments={"patient_id": patient_id, "query": query, "limit": limit}
                )
                
                if result.content and len(result.content) > 0:
                    json_str = result.content[0].text
                    return json.loads(json_str)
                return []
                
    return asyncio.run(_search())
