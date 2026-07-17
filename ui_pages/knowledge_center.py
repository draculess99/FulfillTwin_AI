from __future__ import annotations

import streamlit as st

from fulfilltwin.ui_helpers import get_client

st.title("RAG Knowledge Center")
st.write("Search the internal warehouse playbooks used by the agent council. Retrieval remains local and auditable.")
client = get_client()

query = st.text_input("Ask the internal knowledge base", "What should incident command do during a conveyor failure and demand surge?")
top_k = st.slider("Evidence chunks", 1, 10, 5)
left, right = st.columns([1, 1])
search = left.button("Search knowledge", type="primary")
refresh = right.button("Refresh index")

if refresh:
    try:
        response = client.refresh_rag()
        st.success(f"Index refreshed: {response['knowledge_chunks']} chunks")
    except Exception as exc:
        st.error(str(exc))

if search and query.strip():
    try:
        results = client.search_rag(query, top_k)["results"]
        if not results:
            st.info("No matching evidence found.")
        for result in results:
            st.subheader(result["citation"])
            st.caption(f"Relevance score: {result['score']:.3f}")
            st.write(result["text"])
    except Exception as exc:
        st.error(str(exc))

st.divider()
st.caption("Add or edit Markdown files under fulfilltwin/backend/data/knowledge, then refresh the index.")
