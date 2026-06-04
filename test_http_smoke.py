#!/usr/bin/env python3
"""Smoke test: connect to the streamable-HTTP MCP server, list tools, run one real query."""
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:5179/mcp"


async def main() -> None:
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("TOOLS:", names)
            assert names == ["find_related", "get_context_blocks", "semantic_search"], names

            res = await session.call_tool("semantic_search", {"query": "vault conventions", "limit": 3})
            text = res.content[0].text if res.content else "(no content)"
            print("QUERY OK, first 300 chars:\n", text[:300])

    print("SMOKE PASS")


if __name__ == "__main__":
    asyncio.run(main())
