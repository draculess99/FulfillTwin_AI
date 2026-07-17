from fulfilltwin.config import KNOWLEDGE_DIR
from fulfilltwin.backend.services.rag import LocalRagEngine


def test_rag_returns_conveyor_evidence():
    rag = LocalRagEngine(KNOWLEDGE_DIR)
    results = rag.search("conveyor failure bypass release rate", top_k=3)
    assert results
    assert any("conveyor" in result["source"].lower() for result in results)
