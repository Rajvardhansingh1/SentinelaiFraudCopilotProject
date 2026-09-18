import proxy.eval.grounding as grounding_module
from proxy.eval.grounding import ChromaStore, InMemoryTFIDFStore, get_grounding_store


def test_query_returns_most_relevant_doc():
    store = InMemoryTFIDFStore()
    store.add("receipts", "r1", "Vendor Acme Corp total 42.50 office supplies")
    store.add("receipts", "r2", "Vendor Globex total 900.00 hardware")
    results = store.query("receipts", "what did Acme charge for supplies", k=1)
    assert results == ["Vendor Acme Corp total 42.50 office supplies"]


def test_query_empty_collection_returns_empty():
    store = InMemoryTFIDFStore()
    assert store.query("nothing", "anything") == []


def test_query_no_overlap_returns_empty():
    store = InMemoryTFIDFStore()
    store.add("c", "d1", "completely unrelated words here")
    assert store.query("c", "zzz yyy xxx") == []


def test_chroma_store_add_and_query(tmp_path):
    store = ChromaStore(str(tmp_path))
    store.add("receipts", "r1", "Vendor Acme Corp total 42.50 office supplies")
    store.add("receipts", "r2", "Vendor Globex total 900.00 hardware")
    results = store.query("receipts", "Acme office supplies", k=1)
    assert results == ["Vendor Acme Corp total 42.50 office supplies"]


def test_chroma_store_persists_across_reopened_client(tmp_path):
    store1 = ChromaStore(str(tmp_path))
    store1.add("receipts", "r1", "Vendor Acme Corp total 42.50")
    store2 = ChromaStore(str(tmp_path))
    assert store2.query("receipts", "Acme total") != []


def test_get_grounding_store_returns_working_store(monkeypatch, tmp_path):
    monkeypatch.setattr(grounding_module, "_store", None)
    monkeypatch.setattr("proxy.config.settings.chroma_persist_dir", str(tmp_path))
    store = get_grounding_store()
    store.add("test_collection", "d1", "hello world")
    assert store.query("test_collection", "hello") == ["hello world"]
    monkeypatch.setattr(grounding_module, "_store", None)
