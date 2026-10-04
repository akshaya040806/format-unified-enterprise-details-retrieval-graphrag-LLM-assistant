# Format-Unified GraphRAG — Knowledge Assistant

## Virtual Environment Setup (one time)

```bash
python -m venv rag_env
rag_env\Scripts\activate
```

## Setup (one time)

```bash
pip install -r requirements.txt
```

## Get the API key from Groq for the dataset generation

```powershell
$env:GROQ_API_KEY="your_key_here"
```

## Run the generator code for datasets (one time)

```bash
python generator.py
```

## Place your dataset

```
rag_system/
  data/
    _all_conversations.json   ← put your file here
  rag_engine.py
  app.py
```

Copy both your company dataset and random chat dataset into one combined file:

```python
import json

with open('company_dataset/_all_conversations.json') as f:
    company = json.load(f)
with open('synthetic_chats/_all_conversations.json') as f:
    chats = json.load(f)

combined = company + chats
with open('rag_system/data/_all_conversations.json', 'w') as f:
    json.dump(combined, f)
```

## Download the Ollama Desktop Version and get the phi3 in powershell and verify

```powershell
ollama pull phi3
ollama list
ollama run phi3 "say hello"
```

## Run

```bash
streamlit run app.py
```

Opens at http://localhost:8501

## First run

The first run indexes your entire dataset — this takes 2-5 minutes
depending on dataset size. After that the index is cached in `./chroma_store/`
and loads instantly on subsequent runs.

To re-index (if you add new conversations):
```bash
rm -rf chroma_store/
streamlit run app.py
```

## What the RAG uses

- **Chunking**: Hierarchical (S5 — best for conversational/chat data)
  - Parent chunks ~400 tokens (context)
  - Child chunks ~100 tokens (searched)
- **Embedding**: all-MiniLM-L6-v2 (90MB, CPU-friendly)
- **Vector store**: ChromaDB (local, persistent)
- **Knowledge graph**: NetworkX (entity co-occurrence)
- **Retrieval**: Reciprocal Rank Fusion of vector + graph results
- **Generation**: Groq API, llama-3.3-70b-versatile
- **Confidence scoring**: RRF score + entity overlap
