from dotenv import load_dotenv
load_dotenv()

from composio import Composio

c = Composio()
conns = c.connected_accounts.list()
print(f"Total connections: {len(conns.items)}")
for a in conns.items:
    toolkit = getattr(a, 'toolkit', getattr(a, 'appName', '?'))
    print(f"  id={a.id}  user_id={a.user_id}  status={a.status}  toolkit={toolkit}")
