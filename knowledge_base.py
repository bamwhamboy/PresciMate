"""
Everything to do with retrieval and storage lives here:

  - search_drug_knowledge()  vector search over the drug info Qdrant
                             collection that build_knowledge_base.ipynb
                             already built
  - check_interactions()     the GraphRAG part - walks a small networkx
                             graph of known drug interactions, because
                             "does A affect B" is a connections question,
                             not something a text similarity search
                             answers well
  - save_prescription() /
    get_user_history()       chunks and stores each prescription in its
                             own Qdrant collection, tagged with the
                             username, so a user's history query only
                             ever returns their own data
"""
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from functools import lru_cache

import networkx as nx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


@lru_cache(maxsize=1)
def _embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=config.DENSE_MODEL)


_client_lock = threading.Lock()
_cached_client: QdrantClient | None = None


def _client() -> QdrantClient:
    global _cached_client
    # Fast path: once someone has succeeded, everyone just reuses it -
    # no lock needed to read a variable that's only ever set once.
    if _cached_client is not None:
        return _cached_client

    with _client_lock:
        # Someone else may have finished constructing it while we were
        # waiting for the lock - if so, use that instead of also trying
        # to open a second connection ourselves. This is the part a
        # plain lock-around-the-retry-loop got wrong: it stopped threads
        # from retrying at the same time, but each one still went on to
        # attempt its OWN separate connection afterward, colliding with
        # the one a previous thread was still holding open on purpose.
        if _cached_client is not None:
            return _cached_client

        if config.QDRANT_URL:
            _cached_client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY or None)
            return _cached_client

        # Local file-based storage only allows one process to hold it at
        # a time. During a Railway redeploy, the old container briefly
        # overlaps with the new one before actually shutting down - if
        # this new process starts up during that window, the lock
        # genuinely is still held by something about to go away, not
        # stuck forever. Retrying with a short wait lets that resolve
        # itself instead of crashing on the very first attempt.
        last_error = None
        for attempt in range(5):
            try:
                _cached_client = QdrantClient(path=config.QDRANT_PATH)
                return _cached_client
            except RuntimeError as e:
                if "already accessed by another instance" not in str(e):
                    raise
                last_error = e
                wait = 2 * (attempt + 1)
                print(f"[warn] Qdrant storage locked (attempt {attempt + 1}/5) - retrying in {wait}s...")
                time.sleep(wait)
        raise last_error


# ---------------------------------------------------------------- #
# Drug knowledge (dense vector search against the notebook's collection)
# ---------------------------------------------------------------- #

def search_drug_knowledge(query: str, top_k: int = 3) -> str:
    vector = _embeddings().embed_query(query)
    hits = _client().query_points(
        collection_name=config.DRUG_COLLECTION,
        query=vector,
        using="dense",
        limit=top_k,
    ).points
    return "\n\n".join(h.payload.get("text", "") for h in hits)


# ---------------------------------------------------------------- #
# GraphRAG - drug interaction graph, built from the same SQLite tables
# ---------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _interaction_graph() -> nx.Graph:
    g = nx.Graph()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    for row in conn.execute("SELECT DISTINCT drug_a, drug_b, severity, description FROM interactions"):
        g.add_edge(row["drug_a"], row["drug_b"], severity=row["severity"], description=row["description"])
    conn.close()
    return g


def lookup_generic_name(brand_name: str) -> str:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT generic_name FROM drugs WHERE LOWER(brand_name) LIKE LOWER(?) LIMIT 1",
        (f"%{brand_name}%",),
    ).fetchone()
    conn.close()
    return row["generic_name"] if row else brand_name


def get_dosage(generic_name: str) -> dict | None:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM dosage_ranges WHERE LOWER(generic_name) = LOWER(?) LIMIT 1",
        (generic_name.split()[0],),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def check_interactions(drug_names: list[str]) -> list[dict]:
    """Walks the interaction graph for every pair of drugs on this
    prescription. This is the actual GraphRAG step."""
    g = _interaction_graph()
    generics = [lookup_generic_name(d).split("+")[0].strip() for d in drug_names]

    found, seen = [], set()
    for i in range(len(generics)):
        for j in range(i + 1, len(generics)):
            a, b = generics[i], generics[j]
            key = tuple(sorted([a.lower(), b.lower()]))
            if key in seen:
                continue
            if g.has_edge(a, b):
                seen.add(key)
                edge = g[a][b]
                found.append({
                    "drug_a": a, "drug_b": b,
                    "severity": edge["severity"], "description": edge["description"],
                })
    return found


# ---------------------------------------------------------------- #
# Per-user prescription history (chunked + stored in Qdrant)
# ---------------------------------------------------------------- #

def _ensure_user_collection():
    existing = [c.name for c in _client().get_collections().collections]
    if config.USER_COLLECTION not in existing:
        _client().create_collection(
            collection_name=config.USER_COLLECTION,
            vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
        )


def _store():
    _ensure_user_collection()
    return QdrantVectorStore(
        client=_client(), collection_name=config.USER_COLLECTION, embedding=_embeddings()
    )


def save_prescription(username: str, medicines: list[dict], explanation: str, language: str) -> str:
    """Chunks this prescription's text and stores it in Qdrant, tagged
    with the username - that tag is what makes the history private."""
    prescription_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    medicine_lines = "\n".join(
        f"{m['name']} - {m.get('dosage') or ''} {m.get('frequency') or ''} {m.get('duration') or ''}"
        for m in medicines
    )
    full_text = f"{medicine_lines}\n\n{explanation}"

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(full_text)

    _store().add_texts(
        texts=chunks,
        metadatas=[{
            "username": username,
            "prescription_id": prescription_id,
            "chunk_index": i,
            "medicines": ", ".join(m["name"] for m in medicines),
            "explanation": explanation,
            "language": language,
            "created_at": created_at,
        } for i in range(len(chunks))],
    )
    return prescription_id


def get_user_history(username: str) -> list[dict]:
    """Only ever returns this user's own prescriptions - the Qdrant
    filter on 'username' is what enforces that."""
    try:
        points, _ = _client().scroll(
            collection_name=config.USER_COLLECTION,
            scroll_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="metadata.username", match=qmodels.MatchValue(value=username))]
            ),
            limit=500,
        )
    except Exception:
        return []

    by_prescription = {}
    for p in points:
        meta = p.payload.get("metadata", {})
        pid = meta.get("prescription_id")
        if pid and meta.get("chunk_index") == 0:
            by_prescription[pid] = meta

    return sorted(by_prescription.values(), key=lambda m: m.get("created_at", ""), reverse=True)
