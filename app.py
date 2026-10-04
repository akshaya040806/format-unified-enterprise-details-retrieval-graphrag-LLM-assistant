import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from rag_engine import index_dataset, ask, knowledge_graph


st.set_page_config(
    page_title="Veltrix · Knowledge Assistant",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: #0A0F1E; }
  .block-container { padding: 1rem 1rem 0 1rem !important; max-width: 100% !important; }

  [data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: 1px solid #1E293B;
  }

  .main-header {
    background: #0F172A;
    border-bottom: 1px solid #1E293B;
    padding: 16px 24px;
    border-radius: 8px;
    margin-bottom: 16px;
  }
  .header-title { font-size: 16px; font-weight: 700; color: #F1F5F9; }
  .header-sub   { font-size: 12px; color: #64748B; margin-top: 2px; }

  /* Source cards */
  .source-card {
    background: #0A0F1E;
    border: 1px solid #1E293B;
    border-left: 3px solid #14B8A6;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
  }
  .badge {
    font-size: 10px; font-weight: 500; padding: 2px 7px;
    border-radius: 4px; font-family: monospace;
    display: inline-block; margin-right: 4px; margin-bottom: 4px;
  }
  .badge-platform { background: #164E63; color: #67E8F9; }
  .badge-project  { background: #1E1B4B; color: #A5B4FC; }
  .badge-stage    { background: #14532D; color: #86EFAC; }
  .badge-pct      { background: #27272A; color: #A1A1AA; }
  .source-preview { font-size: 12px; color: #64748B; line-height: 1.5; font-style: italic; margin-top: 6px; }

  /* Stchat message overrides */
  .stChatMessage { background: #0F172A !important; border: 1px solid #1E293B !important; border-radius: 12px !important; }

  /* hide streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


if "messages"  not in st.session_state: st.session_state.messages  = []
if "indexed"   not in st.session_state: st.session_state.indexed   = False
if "data_path" not in st.session_state: st.session_state.data_path = "./data/_all_conversations.json"

if not st.session_state.indexed:
    with st.spinner("Loading and indexing project communications…"):
        index_dataset(st.session_state.data_path)
        st.session_state.indexed = True

with st.sidebar:
    st.markdown("### ⬡ Veltrix Systems\n")
    st.markdown("---")

    st.markdown("**Dataset**")
    try:
        from rag_engine import child_col, parent_col
        cc = child_col.count()
        pc = parent_col.count()
        gn = knowledge_graph.number_of_nodes()
        ge = knowledge_graph.number_of_edges()
        col1, col2 = st.columns(2)
        col1.metric("Child chunks",  f"{cc:,}")
        col2.metric("Parent chunks", f"{pc:,}")
        col1.metric("Graph nodes", f"{gn:,}")
        col2.metric("Graph edges", f"{ge:,}")
    except Exception:
        st.info("Dataset not yet indexed.")

    st.markdown("---")
    st.markdown("**Chunking Strategy**")
    st.info("Using **Hierarchical chunking** (S5 — best for conversational data).\n\nParent chunks (≈400 tokens) carry context. Child chunks (≈100 tokens) are searched. Retrieval is precise, answers are rich.")

    st.markdown("---")
    st.markdown("**Retrieval**")
    st.markdown("Vector search (semantic similarity)\n\n🕸 Graph traversal (entity connections)\n\n⚖ Reciprocal Rank Fusion (merged)\n\n📄 Parent expansion (full context)")

    st.markdown("---")
    data_path_input = st.text_input("Dataset path", value=st.session_state.data_path)
    if data_path_input != st.session_state.data_path:
        st.session_state.data_path = data_path_input
        st.session_state.indexed   = False
        st.rerun()

    if st.button("🗑 Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <div class="header-title">⬡ Project Knowledge Assistant</div>
  <div class="header-sub">Ask anything about ongoing projects, team members, decisions, and timelines</div>
</div>
""", unsafe_allow_html=True)

# ── Layout: chat + sources ────────────────────────────────────────────────────
chat_col, source_col = st.columns([3, 2], gap="medium")

SUGGESTED = [
    "What is the production status of Project Orion?",
    "Who is responsible for QA on Project Orion?",
    "What delayed the project and by how many days?",
    "Who joined the team recently and who mentored her?",
    "Why was OmniPay chosen over SecurePay?",
    "What critical bugs were found and who fixed them?",
    "What is the current test coverage?",
    "What stage is Project Orion at?",
]

with chat_col:
    if not st.session_state.messages:
        st.markdown("### Hi, I'm your Project Assistant")
        st.markdown("Ask me anything - status updates, team members, decisions or even about timelines!")
        st.markdown("**Try asking:**")
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTED[:6]):
            with cols[i % 2]:
                if st.button(q, key=f"sug_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.rerun()

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                answer = msg.get("content", "")
                if answer:
                    st.markdown(answer)
                else:
                    st.warning("No answer was generated for this question.")

                # Confidence bar using native Streamlit progress
                conf     = msg.get("confidence", 0)
                conf_pct = int(conf * 100)
                conf_color = "🟢" if conf > 0.7 else "🟡" if conf > 0.4 else "🔴"
                st.progress(conf, text=f"{conf_color} Confidence: {conf_pct}%")

    # Input
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    input_col, btn_col = st.columns([5, 1])
    with input_col:
        user_input = st.chat_input("Ask about projects, people, decisions, timelines…")
    with btn_col:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

with source_col:
    st.markdown("#### 📎 Source Attribution")
    st.caption("Every answer can be traced to real team communications")

    if st.session_state.messages:
        last_bot = None
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "assistant" and "sources" in msg:
                last_bot = msg
                break

        if last_bot and last_bot.get("sources"):
            # Entity chips
            entities = last_bot.get("graph_entities", [])
            if entities:
                st.markdown("**Detected entities**")
                entity_text = " ".join([f"`{e['entity']}`" for e in entities[:10]])
                st.markdown(entity_text)

            st.markdown("**Retrieved sources**")
            for src in last_bot["sources"]:
                platform = src.get("platform", "").upper()
                project  = src.get("project", "")
                stage    = src.get("stage", "")[:35]
                pct      = src.get("completion", "")
                score    = src.get("score", 0)
                preview  = src.get("text_preview", "")[:180]

                st.markdown(f"""
<div class="source-card">
  <div>
    <span class="badge badge-platform">{platform}</span>
    <span class="badge badge-project">{project}</span>
    <span class="badge badge-stage">{stage}{'…' if len(src.get('stage',''))>35 else ''}</span>
    <span class="badge badge-pct">{pct}%</span>
    <span style="font-size:10px;color:#475569;font-family:monospace">RRF {score:.3f}</span>
  </div>
  <div class="source-preview">"{preview}{'...' if len(src.get('text_preview',''))>180 else ''}"</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("Sources from the last answer will appear here.")
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px 16px">
          <div style="font-size:32px;margin-bottom:12px">🕸</div>
          <div style="font-size:13px;color:#64748B;line-height:1.6">
            When you ask a question, the knowledge graph and vector index will be searched.
            Every answer will show exactly which conversation it came from.
          </div>
        </div>
        """, unsafe_allow_html=True)

if user_input and user_input.strip():
    question = user_input.strip()
    st.session_state.messages.append({"role": "user", "content": question})

    with st.spinner("Searching project communications…"):
        result = ask(question)

    st.session_state.messages.append({
        "role":           "assistant",
        "content":        result["answer"],
        "sources":        result["sources"],
        "confidence":     result["confidence"],
        "graph_entities": result["graph_entities"],
    })
    st.rerun()