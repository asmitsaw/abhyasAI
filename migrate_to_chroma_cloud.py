#!/usr/bin/env python3
"""
migrate_to_chroma_cloud.py
==========================
One-shot migration script: reads all vectors from the local ChromaDB
PersistentClient and re-ingests the raw document text into Chroma Cloud
with Qwen dense + SPLADE sparse hybrid embeddings.

Usage
-----
    python migrate_to_chroma_cloud.py

Requirements
------------
Set CHROMA_API_KEY in your .env before running:

    CHROMA_API_KEY=<your-key>
    CHROMA_TENANT=688bc2df-d727-4a69-9f2e-5fa46471ce1c
    CHROMA_DATABASE=abhyasAI

Progress
--------
The script is idempotent: already-migrated chunks are skipped (Chroma
upsert by chunk_id). Re-run safely at any time.
"""

import os
import sys
import time

# ── Load .env ────────────────────────────────────────────────────────────────
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"[migrate] Loaded .env from {env_path}")

# ── Validate Chroma Cloud credentials ────────────────────────────────────────
api_key  = os.environ.get("CHROMA_API_KEY", "")
tenant   = os.environ.get("CHROMA_TENANT",  "688bc2df-d727-4a69-9f2e-5fa46471ce1c")
database = os.environ.get("CHROMA_DATABASE", "abhyasAI")

if not api_key:
    sys.exit(
        "[migrate] ✗ CHROMA_API_KEY is not set.\n"
        "  Copy it from https://www.trychroma.com/asmit01052005/aws-us-east-1/abhyasAI/sdk?tab=env\n"
        "  and add CHROMA_API_KEY=<value> to your .env file."
    )

# ── Connect to local (source) ChromaDB ───────────────────────────────────────
import chromadb

LOCAL_CHROMA_PATH = os.path.join(os.path.dirname(__file__), "data", "chroma")

if not os.path.exists(LOCAL_CHROMA_PATH):
    print(f"[migrate] No local ChromaDB found at {LOCAL_CHROMA_PATH}.")
    print("[migrate] Nothing to migrate — starting fresh on Chroma Cloud.")
    sys.exit(0)

print(f"[migrate] Opening local ChromaDB: {LOCAL_CHROMA_PATH}")
local_client = chromadb.PersistentClient(path=LOCAL_CHROMA_PATH)
local_collections = local_client.list_collections()

if not local_collections:
    print("[migrate] Local ChromaDB has no collections. Nothing to migrate.")
    sys.exit(0)

# ── Connect to Chroma Cloud (destination) ─────────────────────────────────────
print(f"[migrate] Connecting to Chroma Cloud tenant={tenant} db={database}")
cloud_client = chromadb.CloudClient(
    tenant=tenant,
    database=database,
    api_key=api_key,
)
print("[migrate] Connected ✓")

# ── Import Cloud helpers ──────────────────────────────────────────────────────
from services.rag.embeddings import get_hybrid_schema, get_dense_ef

schema = get_hybrid_schema()

# ── Migrate each collection ───────────────────────────────────────────────────
BATCH_SIZE = 50   # Chroma Cloud upsert batch size

total_migrated = 0
total_skipped  = 0
total_errors   = 0

for local_coll in local_collections:
    coll_name = local_coll.name
    count     = local_coll.count()
    print(f"\n[migrate] Collection '{coll_name}' — {count} chunks")

    if count == 0:
        print("  (empty, skipping)")
        continue

    # Get or create the Cloud destination collection
    cloud_coll = cloud_client.get_or_create_collection(
        name=coll_name,
        schema=schema,
        embedding_function=get_dense_ef(),
    )

    # Fetch all docs from local in pages
    offset = 0
    while offset < count:
        limit = min(BATCH_SIZE, count - offset)
        page  = local_coll.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )

        ids       = page.get("ids", [])
        documents = page.get("documents", []) or []
        metadatas = page.get("metadatas", []) or [{}] * len(ids)

        # Filter out empty documents (Chroma Cloud rejects them)
        valid = [
            (i, d, m)
            for i, d, m in zip(ids, documents, metadatas)
            if d and d.strip()
        ]
        skipped_empty = len(ids) - len(valid)
        total_skipped += skipped_empty

        if valid:
            v_ids  = [x[0] for x in valid]
            v_docs = [x[1] for x in valid]
            v_mets = [x[2] for x in valid]

            try:
                cloud_coll.upsert(ids=v_ids, documents=v_docs, metadatas=v_mets)
                total_migrated += len(v_ids)
                print(f"  ✓ batch [{offset+1}–{offset+len(ids)}] — {len(v_ids)} upserted", flush=True)
            except Exception as e:
                total_errors += len(v_ids)
                print(f"  ✗ batch [{offset+1}–{offset+len(ids)}] error: {e}")

        offset += limit
        time.sleep(0.25)   # gentle rate-limit respect

print("\n" + "=" * 60)
print(f"Migration complete.")
print(f"  Migrated : {total_migrated} chunks")
print(f"  Skipped  : {total_skipped} empty chunks")
print(f"  Errors   : {total_errors} chunks")
print("=" * 60)

if total_migrated > 0:
    print("\n✅ Your data is now in Chroma Cloud with hybrid search enabled.")
    print("   The local data/chroma directory can be kept as a backup.")
