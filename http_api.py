#!/usr/bin/env python3
"""
HTTP API wrapper around SmartConnectionsDatabase for SvelteKit integration.
GET /search?q=<query>&limit=5 → FK-relative file paths ranked by semantic similarity.

Start:
  .venv\Scripts\python.exe -m uvicorn http_api:app --port 5174
  (liest OBSIDIAN_VAULT_PATH + SEMANTIC_API_KEY aus .env automatisch)
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from server import SmartConnectionsDatabase

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("SEMANTIC_API_KEY", "")
VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", "")

if not API_KEY:
    raise RuntimeError("SEMANTIC_API_KEY not set")
if not VAULT_PATH:
    raise RuntimeError("OBSIDIAN_VAULT_PATH not set")

FK_PREFIX = "03-Resources/Fakultaet-KB/"
FK_SCOPES = (
    f"{FK_PREFIX}Pruefungsordnungen/",
    f"{FK_PREFIX}Modulhandbuecher/",
)

app = FastAPI()
security = HTTPBearer()
db = SmartConnectionsDatabase(VAULT_PATH)


def verify_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> None:
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/search")
def search(
    q: str,
    limit: int = 5,
    _: None = Security(verify_key),
):
    results = db.semantic_search(q, limit=limit * 3, min_similarity=0.5)

    seen: set[str] = set()
    paths: list[str] = []

    for r in results:
        vault_path = r.get("path", "")
        if not any(vault_path.startswith(scope) for scope in FK_SCOPES):
            continue
        rel = vault_path[len(FK_PREFIX):]  # strip FK prefix → kb.ts-compatible
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)
        if len(paths) >= limit:
            break

    return {"query": q, "paths": paths}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
