import json
import os
import re
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import chromadb
from sentence_transformers import SentenceTransformer
import requests
import networkx as nx


EMBED_MODEL_NAME = "all-MiniLM-L6-v2"   
GROQ_MODEL = "openai/gpt-oss-20b"
CHROMA_PATH      = "./chroma_store"
DATA_DIR         = "./data"            
PARENT_SIZE  = 400   
CHILD_SIZE   = 100  
OVERLAP      = 20  
TOP_K_VECTOR = 15  
TOP_K_GRAPH  = 4   
TOP_K_FINAL  = 10

print("Loading embedding model...")
embedder = SentenceTransformer(EMBED_MODEL_NAME)

# Connect to the ChromaDB SERVER (run separately with: chroma run --path ./chroma_store --port 8000)
# Falls back to embedded mode if the server isn't running.
try:
    chroma = chromadb.HttpClient(host="localhost", port=8000)
    chroma.heartbeat()  # test the connection
    print("Connected to ChromaDB server on port 8000 (live mode).")
except Exception:
    print("ChromaDB server not found — using embedded mode (restart needed for re-index).")
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
child_col  = chroma.get_or_create_collection("child_chunks")
parent_col = chroma.get_or_create_collection("parent_chunks")

knowledge_graph = nx.DiGraph()

def _word_count(text: str) -> int:
    return len(text.split())

def _token_estimate(text: str) -> int:
    """Rough token count: words / 0.75"""
    return int(_word_count(text) / 0.75)

def hierarchical_chunk(
    text: str,
    metadata: dict,
    parent_size: int = PARENT_SIZE,
    child_size: int  = CHILD_SIZE,
    overlap: int     = OVERLAP
) -> List[dict]:
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    parents = []
    buf, buf_tok = [], 0
    for sent in sentences:
        tok = _token_estimate(sent)
        if buf_tok + tok > parent_size and buf:
            parents.append(" ".join(buf))
            # overlap: carry last few sentences forward
            overlap_sents = []
            carry = 0
            for s in reversed(buf):
                carry += _token_estimate(s)
                overlap_sents.insert(0, s)
                if carry >= overlap:
                    break
            buf, buf_tok = overlap_sents, carry
        buf.append(sent)
        buf_tok += tok
    if buf:
        parents.append(" ".join(buf))

    chunks = []
    for p_idx, parent_text in enumerate(parents):
        p_id = f"{metadata['doc_id']}_p{p_idx}"
        chunks.append({
            "chunk_id":   p_id,
            "text":       parent_text,
            "level":      "parent",
            "parent_id":  None,
            "metadata":   {**metadata, "chunk_type": "parent", "parent_idx": p_idx},
        })

        p_sents = re.split(r'(?<=[.!?])\s+|\n+', parent_text.strip())
        p_sents = [s.strip() for s in p_sents if s.strip()]

        cbuf, ctok = [], 0
        c_idx = 0
        for sent in p_sents:
            tok = _token_estimate(sent)
            if ctok + tok > child_size and cbuf:
                c_id = f"{p_id}_c{c_idx}"
                chunks.append({
                    "chunk_id":  c_id,
                    "text":      " ".join(cbuf),
                    "level":     "child",
                    "parent_id": p_id,
                    "metadata":  {**metadata, "chunk_type": "child",
                                  "parent_idx": p_idx, "child_idx": c_idx},
                })
                c_idx += 1
                overlap_sents = []
                carry = 0
                for s in reversed(cbuf):
                    carry += _token_estimate(s)
                    overlap_sents.insert(0, s)
                    if carry >= overlap:
                        break
                cbuf, ctok = overlap_sents, carry
            cbuf.append(sent)
            ctok += tok
        if cbuf:
            c_id = f"{p_id}_c{c_idx}"
            chunks.append({
                "chunk_id":  c_id,
                "text":      " ".join(cbuf),
                "level":     "child",
                "parent_id": p_id,
                "metadata":  {**metadata, "chunk_type": "child",
                              "parent_idx": p_idx, "child_idx": c_idx},
            })
    return chunks

def normalise_conversation(conv: dict) -> Tuple[str, dict]:
    """
    Convert a conversation record (any platform) into normalised text + metadata.
    This is your Format-Unified layer.
    """
    platform = conv.get("platform", "unknown")
    project  = conv.get("project", "unknown")
    stage    = conv.get("stage_title", conv.get("scenario", "unknown"))
    pct      = conv.get("completion_pct", "")
    conv_id  = conv.get("conversation_id", "unknown")
    participants = conv.get("participants", [])

    lines = []
    for msg in conv.get("messages", []):
        sender = msg.get("sender", "Unknown")
        text   = msg.get("text", "").strip()
        ts     = msg.get("timestamp", "")
        if text:
            lines.append(f"[{ts}] {sender}: {text}")

    normalised_text = "\n".join(lines)

    metadata = {
        "doc_id":       conv_id,
        "platform":     platform,
        "project":      project,
        "stage_title":  stage,
        "completion_pct": str(pct),
        "participants": ", ".join(participants) if isinstance(participants, list) else str(participants),
        "source_type":  "chat",
    }
    return normalised_text, metadata

ENTITY_PATTERNS = [
    (r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', "person"),          # Maya Thompson
    (r'\bProject ([A-Z][a-z]+)\b',       "project"),        # Project Orion
    (r'\b([A-Z][A-Z]+(?:-\d+)?)\b',      "identifier"),     # ORION-123, OmniPay
    (r'\b(\d+)%\b',                       "percentage"),     # 75%
    (r'\b([A-Z][a-z]+Pay|[A-Z][a-z]+Soft|[A-Z][a-z]+Corp)\b', "vendor"),
]

def extract_entities(text: str) -> List[Tuple[str, str]]:
    entities = []
    for pattern, etype in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text):
            ent = match.group(1)
            if len(ent) > 2:
                entities.append((ent, etype))
    return list(set(entities))

def build_knowledge_graph_from_chunk(chunk: dict):
    entities = extract_entities(chunk["text"])
    chunk_id = chunk["chunk_id"]

    for ent, etype in entities:
        if not knowledge_graph.has_node(ent):
            knowledge_graph.add_node(ent, type=etype, chunks=[])
        knowledge_graph.nodes[ent]["chunks"].append(chunk_id)

    # Connect every entity pair that co-occurs in this chunk
    for i, (ent_a, _) in enumerate(entities):
        for ent_b, _ in entities[i+1:]:
            if ent_a != ent_b:
                if knowledge_graph.has_edge(ent_a, ent_b):
                    knowledge_graph[ent_a][ent_b]["weight"] += 1
                else:
                    knowledge_graph.add_edge(ent_a, ent_b, weight=1, chunks=[chunk_id])

def index_dataset(data_file: str = None):
    if data_file is None:
        data_file = os.path.join(DATA_DIR, "_all_conversations.json")

    print(f"Loading dataset from {data_file}...")
    with open(data_file) as f:
        conversations = json.load(f)

    print(f"Found {len(conversations)} conversations.")

    existing = child_col.count()
    if existing > 0:
        print(f"Index already exists ({existing} child chunks). Skipping re-indexing.")
        print("Delete ./chroma_store/ to force re-index.")
        _rebuild_graph_from_chroma()
        return

    all_child_texts, all_child_ids, all_child_metas = [], [], []
    all_parent_texts, all_parent_ids, all_parent_metas = [], [], []

    for conv in conversations:
        text, metadata = normalise_conversation(conv)
        if not text.strip():
            continue

        chunks = hierarchical_chunk(text, metadata)

        for chunk in chunks:
            build_knowledge_graph_from_chunk(chunk)
            if chunk["level"] == "child":
                all_child_texts.append(chunk["text"])
                all_child_ids.append(chunk["chunk_id"])
                m = {**chunk["metadata"], "parent_id": chunk["parent_id"] or ""}
                all_child_metas.append({k: str(v) for k, v in m.items()})
            else:
                all_parent_texts.append(chunk["text"])
                all_parent_ids.append(chunk["chunk_id"])
                all_parent_metas.append({k: str(v) for k, v in chunk["metadata"].items()})

    BATCH = 64
    print(f"Embedding {len(all_child_texts)} child chunks...")
    for i in range(0, len(all_child_texts), BATCH):
        batch_texts = all_child_texts[i:i+BATCH]
        batch_ids   = all_child_ids[i:i+BATCH]
        batch_metas = all_child_metas[i:i+BATCH]
        embeddings  = embedder.encode(batch_texts, show_progress_bar=False).tolist()
        child_col.add(ids=batch_ids, embeddings=embeddings,
                      documents=batch_texts, metadatas=batch_metas)

    print(f"Storing {len(all_parent_texts)} parent chunks...")
    for i in range(0, len(all_parent_texts), BATCH):
        parent_col.add(
            ids       = all_parent_ids[i:i+BATCH],
            documents = all_parent_texts[i:i+BATCH],
            metadatas = all_parent_metas[i:i+BATCH],
        )

    print(f"Knowledge graph: {knowledge_graph.number_of_nodes()} nodes, "
          f"{knowledge_graph.number_of_edges()} edges")
    print("Indexing complete.")

def _rebuild_graph_from_chroma():
    print("Rebuilding knowledge graph from index...")
    results = child_col.get(include=["documents"])
    for doc in results["documents"]:
        chunk = {"text": doc, "chunk_id": "rebuild"}
        build_knowledge_graph_from_chunk(chunk)
    print(f"Graph rebuilt: {knowledge_graph.number_of_nodes()} nodes")

def vector_retrieve(query: str, top_k: int = TOP_K_VECTOR) -> List[dict]:
    q_emb = embedder.encode([query]).tolist()
    results = child_col.query(query_embeddings=q_emb, n_results=min(top_k, child_col.count()))
    hits = []
    for i, doc in enumerate(results["documents"][0]):
        hits.append({
            "text":      doc,
            "chunk_id":  results["ids"][0][i],
            "metadata":  results["metadatas"][0][i],
            "distance":  results["distances"][0][i],
            "score":     1 / (1 + results["distances"][0][i]),
        })
    return hits

def graph_retrieve(query: str, top_k: int = TOP_K_GRAPH) -> List[dict]:
    query_entities = [ent for ent, _ in extract_entities(query)]
    if not query_entities:
        return []

    candidate_chunk_ids = set()
    for ent in query_entities:
        if knowledge_graph.has_node(ent):
            candidate_chunk_ids.update(knowledge_graph.nodes[ent].get("chunks", []))
            for neighbour in knowledge_graph.neighbors(ent):
                candidate_chunk_ids.update(knowledge_graph.nodes[neighbour].get("chunks", []))

    if not candidate_chunk_ids:
        return []

    id_list = list(candidate_chunk_ids)[:top_k * 4]
    try:
        results = child_col.get(ids=id_list, include=["documents", "metadatas"])
    except Exception:
        return []

    hits = []
    for i, doc in enumerate(results["documents"]):
        hits.append({
            "text":     doc,
            "chunk_id": results["ids"][i],
            "metadata": results["metadatas"][i],
            "distance": 0.0,
            "score":    0.7,   # graph hits get a base score
        })
    return hits[:top_k]

def expand_to_parent(child_hits: List[dict]) -> List[dict]:
    parent_ids = list(set(
        h["metadata"].get("parent_id", "")
        for h in child_hits
        if h["metadata"].get("parent_id")))
    if not parent_ids:
        return child_hits

    try:
        results = parent_col.get(ids=parent_ids, include=["documents", "metadatas"])
    except Exception:
        return child_hits

    expanded = []
    for i, doc in enumerate(results["documents"]):
        expanded.append({
            "text":     doc,
            "chunk_id": results["ids"][i],
            "metadata": results["metadatas"][i],
            "score":    0.85,
        })
    return expanded

def reciprocal_rank_fusion(vector_hits: List[dict], graph_hits: List[dict],k: int = 60) -> List[dict]:
    scores = defaultdict(float)
    all_chunks = {}

    for rank, hit in enumerate(vector_hits):
        cid = hit["chunk_id"]
        scores[cid] += 1.0 / (k + rank + 1)
        all_chunks[cid] = hit

    for rank, hit in enumerate(graph_hits):
        cid = hit["chunk_id"]
        scores[cid] += 1.0 / (k + rank + 1)
        if cid not in all_chunks:
            all_chunks[cid] = hit

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for cid, rrf_score in ranked:
        chunk = all_chunks[cid].copy()
        chunk["rrf_score"] = rrf_score
        result.append(chunk)
    return result

def retrieve(query: str, top_k: int = TOP_K_FINAL) -> List[dict]:
    import time
    t0 = time.time()
    vec_hits = vector_retrieve(query, top_k=TOP_K_VECTOR)
    print(f"Vector retrieval: {time.time()-t0:.2f}s")
    t1 = time.time()
    graph_hits = graph_retrieve(query, top_k=TOP_K_GRAPH)
    print(f"Graph retrieval: {time.time()-t1:.2f}s")
    t2 = time.time()
    fused = reciprocal_rank_fusion(vec_hits, graph_hits)
    expanded = expand_to_parent(fused[:top_k])
    print(f"Fusion+expand: {time.time()-t2:.2f}s")
    return expanded[:top_k]

SYSTEM_PROMPT = """You are the Veltrix Systems internal knowledge assistant, helping new employees understand ongoing projects, team structures, processes, and decisions.

You answer questions based ONLY on the internal communications provided as context. These are real Slack messages, emails, and WhatsApp conversations from the team.

Rules:
1. Answer directly and specifically from the context provided.
2. If the answer is spread across multiple messages, synthesise them into one clear answer.
3. Always mention WHO said something or WHO is responsible when it's relevant.
4. If a specific number, date, or decision is in the context, state it explicitly.
5. If the context does not contain the answer, say clearly: "I don't have that information in the available project communications."
6. Never make up information that isn't in the context.
7. Keep answers concise — maximum 5-6 short points. Do not repeat information. If listing items, list each only once. Stop when you have covered the key facts."""

def generate_answer(query: str, context_chunks: List[dict]) -> Tuple[str, List[dict]]:
    if not context_chunks:
        return ("I couldn't find relevant information.", [])

    context_parts = []
    for i, chunk in enumerate(context_chunks):
        meta = chunk["metadata"]
        source_label = (f"[Source {i+1}: {meta.get('platform','').upper()} | "
                       f"{meta.get('project','Unknown')} | "
                       f"{meta.get('stage_title', '')}]")
        context_parts.append(f"{source_label}\n{chunk['text']}")

    context_text = "\n\n---\n\n".join(context_parts)

    prompt = f"""{SYSTEM_PROMPT}

Context from internal communications:

{context_text}

---

Question: {query}

Answer:"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:0.5b",
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 600,
            }
        },
        timeout=120
    )
    answer = response.json()["response"].strip()
    return answer, context_chunks

def compute_confidence(chunks: List[dict], answer: str) -> float:
    if not chunks:
        return 0.0

    avg_rrf = sum(c.get("rrf_score", 0.5) for c in chunks) / len(chunks)
    coverage = min(1.0, len(chunks) / TOP_K_FINAL)
    entity_overlap = 0.0
    answer_entities = {e for e, _ in extract_entities(answer)}
    if answer_entities:
        chunk_text = " ".join(c["text"] for c in chunks)
        matched = sum(1 for e in answer_entities if e in chunk_text)
        entity_overlap = matched / len(answer_entities)

    confidence = (avg_rrf * 0.4 + coverage * 0.3 + entity_overlap * 0.3)
    return round(min(1.0, confidence), 2)

def ask(query: str) -> dict:
    chunks  = retrieve(query)
    answer, used_chunks = generate_answer(query, chunks)
    confidence = compute_confidence(used_chunks, answer)

    sources = []
    for chunk in used_chunks:
        meta = chunk["metadata"]
        sources.append({
            "platform":     meta.get("platform", ""),
            "project":      meta.get("project", ""),
            "stage":        meta.get("stage_title", meta.get("scenario", "")),
            "completion":   meta.get("completion_pct", ""),
            "participants": meta.get("participants", ""),
            "text_preview": chunk["text"][:200] + ("..." if len(chunk["text"]) > 200 else ""),
            "score":        round(chunk.get("rrf_score", 0.5), 3),
        })

    query_entities = [{"entity": e, "type": t} for e, t in extract_entities(query)]

    return {
        "answer":         answer,
        "sources":        sources,
        "confidence":     confidence,
        "graph_entities": query_entities,
    }


def reindex_live(data_file: str = None):
    """
    Live re-index WITHOUT deleting files or restarting.
    Works when ChromaDB is running as a server.
    Clears both collections via the API, then rebuilds from the dataset.
    """
    global child_col, parent_col, knowledge_graph
    import networkx as nx

    # Delete and recreate collections (works over HTTP, no file lock)
    try:
        chroma.delete_collection("child_chunks")
    except Exception:
        pass
    try:
        chroma.delete_collection("parent_chunks")
    except Exception:
        pass

    child_col  = chroma.get_or_create_collection("child_chunks")
    parent_col = chroma.get_or_create_collection("parent_chunks")
    knowledge_graph = nx.DiGraph()

    # Rebuild from scratch
    index_dataset(data_file)
    print("Live re-index complete.")


if __name__ == "__main__":
    # Quick CLI test
    index_dataset()
    print("\n--- RAG Engine Ready ---\n")
    while True:
        q = input("Ask a question (or 'exit'): ").strip()
        if q.lower() == "exit":
            break
        result = ask(q)
        print(f"\nAnswer: {result['answer']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Sources used: {len(result['sources'])}")
        for s in result['sources'][:3]:
            print(f"  - {s['platform'].upper()} | {s['project']} | {s['stage']}")
        print()
