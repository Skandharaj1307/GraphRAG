"""Load precomputed embeddings onto nodes in graphragv2 and create vector indexes.

Edit the CONFIG block below, then run:
  python load_embeddings.py preflight   # checks only, writes nothing
  python load_embeddings.py load        # writes embeddings (idempotent)
  python load_embeddings.py index       # creates vector indexes
  python load_embeddings.py verify      # counts + a sample similarity query
"""
import os, sys
import numpy as np
import pandas as pd
from neo4j import GraphDatabase

# ======================= CONFIG (edit these) =======================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "qazwsxedc"
TARGET_DATABASE = "graphragv2"            # never neo4j / system

DATA_DIR = r"E:\GraphRAG-1\embedding\data"     # folder holding the CSVs and .npy files
EMBEDDING_MODEL = "Qwen3-Embedding-0.6B"
DIM = 1024                                 # set to your .npy's actual width
BATCH = 500

# label, id property in graph, id csv, id column, vector file (rows aligned to the csv)
SPECS = [
    ("Defect",     "defect_id",     "defect_ids.csv",     "defect_id",     "defect_embeddings.npy"),
    ("Screenshot", "screenshot_id", "screenshot_ids.csv", "screenshot_id", "screenshot_embeddings.npy"),
    ("TestCase",   "test_case_id",  "testcase_ids.csv",   "test_case_id",  "testcase_embeddings.npy"),
]
# ===================================================================

if TARGET_DATABASE in ("neo4j", "system"):
    sys.exit("Refusing to write to v1/system.")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def resolve_file(filename):
    """Resolve file in DATA_DIR, workspace root, or embedding/data."""
    candidates = [
        os.path.join(DATA_DIR, filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "embedding", "data", filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"Could not find '{filename}'. Searched: {candidates}")


def load_spec(csv, col, npy):
    csv_path = resolve_file(csv)
    npy_path = resolve_file(npy)
    ids = pd.read_csv(csv_path)[col].astype(str).str.strip().tolist()
    vecs = np.load(npy_path).astype(np.float32)
    assert len(ids) == len(vecs), f"{csv}: {len(ids)} ids vs {len(vecs)} vectors"
    assert vecs.shape[1] == DIM, f"{npy}: dim {vecs.shape[1]} != {DIM}"
    assert len(set(ids)) == len(ids), f"{csv}: duplicate ids"
    assert np.isfinite(vecs).all(), f"{npy}: NaN/inf in vectors"
    return ids, vecs


def preflight():
    with driver.session(database=TARGET_DATABASE) as s:
        for label, prop, csv, col, npy in SPECS:
            ids, vecs = load_spec(csv, col, npy)
            n = s.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            found = s.run(
                f"UNWIND $ids AS i MATCH (n:{label} {{{prop}: i}}) RETURN count(n) AS c",
                ids=ids,
            ).single()["c"]
            print(f"{label}: csv={len(ids)} vectors={vecs.shape} graph={n} matched={found}")
            assert found == len(ids) == n, f"{label}: ids do not match graph"
    print("preflight OK")


def load():
    q = """
    UNWIND $rows AS r
    MATCH (n:%s {%s: r.id})
    CALL db.create.setNodeVectorProperty(n, 'embedding', r.vec)
    SET n.embedding_model = $model
    """
    with driver.session(database=TARGET_DATABASE) as s:
        for label, prop, csv, col, npy in SPECS:
            ids, vecs = load_spec(csv, col, npy)
            for i in range(0, len(ids), BATCH):
                rows = [{"id": ids[j], "vec": vecs[j].tolist()}
                        for j in range(i, min(i + BATCH, len(ids)))]
                s.run(q % (label, prop), rows=rows, model=EMBEDDING_MODEL).consume()
                print(f"{label}: {min(i + BATCH, len(ids))}/{len(ids)}", end="\r")
            print(f"\n{label}: loaded {len(ids)}")


def index():
    with driver.session(database=TARGET_DATABASE) as s:
        for label, *_ in SPECS:
            s.run(
                f"""CREATE VECTOR INDEX {label.lower()}_embedding IF NOT EXISTS
                FOR (n:{label}) ON (n.embedding)
                OPTIONS {{indexConfig: {{`vector.dimensions`: {DIM},
                                         `vector.similarity_function`: 'cosine'}}}}"""
            ).consume()
        s.run("CALL db.awaitIndexes(300)").consume()
        for r in s.run("SHOW INDEXES YIELD name, type, state, populationPercent "
                       "WHERE type = 'VECTOR' RETURN *"):
            print(dict(r))


def verify():
    with driver.session(database=TARGET_DATABASE) as s:
        for label, *_ in SPECS:
            r = s.run(
                f"MATCH (n:{label}) RETURN count(n) AS total, "
                f"count(n.embedding) AS with_emb, "
                f"count(DISTINCT n.embedding_model) AS models"
            ).single()
            print(label, dict(r))
        # self-query: a node's nearest neighbour should be itself with score ~1.0
        r = s.run(
            """MATCH (d:Defect) WITH d LIMIT 1
               CALL db.index.vector.queryNodes('defect_embedding', 3, d.embedding)
               YIELD node, score RETURN d.defect_id AS q, node.defect_id AS hit, score"""
        )
        for row in r:
            print(dict(row))


if __name__ == "__main__":
    cmds = {"preflight": preflight, "load": load, "index": index, "verify": verify}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit("usage: python load_embeddings.py [preflight|load|index|verify]")
    cmds[sys.argv[1]]()
    driver.close()
