"""Entry point: python -m mcp_servers.web_search"""

from mcp_servers.web_search.server import main
import asyncio

asyncio.run(main())
