#!/usr/bin/env python3
"""
Smart Connections MCP — streamable-HTTP transport.

Persistent server so every Claude Code session shares ONE warm process:
the embedding model + vault embeddings load once at boot, not per session.
The stdio entry point (server.py) stays untouched as a fallback.

Start (persistent):
  .venv\\Scripts\\python.exe mcp_http.py
  -> serves MCP at http://127.0.0.1:5179/mcp

Register (user scope, all projects):
  claude mcp remove smart-connections -s user
  claude mcp add --transport http smart-connections http://127.0.0.1:5179/mcp -s user

Env (read from .env):
  OBSIDIAN_VAULT_PATH   required, vault root
  MCP_HTTP_HOST         optional, default 127.0.0.1
  MCP_HTTP_PORT         optional, default 5179
"""
import os
import sys

# pythonw.exe (boot autostart) has no console: sys.stdout/sys.stderr are None,
# so the first print()/logging write (server.py init, uvicorn, rich) raises
# AttributeError and kills the process before the port binds. Redirect None
# streams to a logfile so pythonw behaves like a console run.
if sys.stdout is None or sys.stderr is None:
    _log = open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_http.log"),
        "a", buffering=1, encoding="utf-8",
    )
    if sys.stdout is None:
        sys.stdout = _log
    if sys.stderr is None:
        sys.stderr = _log

from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from server import SmartConnectionsDatabase

load_dotenv(Path(__file__).parent / ".env")

VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", "")
if not VAULT_PATH:
    raise RuntimeError("OBSIDIAN_VAULT_PATH not set")

HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_HTTP_PORT", "5179"))

db = SmartConnectionsDatabase(VAULT_PATH)
mcp = FastMCP("smart-connections-mcp", host=HOST, port=PORT)


@mcp.tool()
def semantic_search(query: str, limit: int = 10, min_similarity: float = 0.3) -> dict:
    """Search vault using semantic similarity (not keyword matching). Finds notes related to query meaning, not just exact words."""
    results = db.semantic_search(query=query, limit=limit, min_similarity=min_similarity)
    return {"query": query, "results_count": len(results), "results": results}


@mcp.tool()
def find_related(file_path: str, limit: int = 10) -> dict:
    """Find notes related to a specific file path. Like the Smart Connections sidebar in Obsidian. file_path is relative to the vault root."""
    results = db.find_related(file_path=file_path, limit=limit)
    return {"source_file": file_path, "related_count": len(results), "related_files": results}


@mcp.tool()
def get_context_blocks(query: str, max_blocks: int = 5) -> dict:
    """Get best text blocks for a query (for RAG/context building). Returns actual text content."""
    results = db.get_context_blocks(query=query, max_blocks=max_blocks)
    return {"query": query, "blocks_count": len(results), "blocks": results}


def warm() -> None:
    """Preload model + embeddings so the first client query is already warm."""
    db.ensure_model_loaded()
    db.load_embeddings()


if __name__ == "__main__":
    warm()
    mcp.run(transport="streamable-http")
