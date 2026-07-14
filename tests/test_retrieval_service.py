"""Tests for the shared retrieval backend lifecycle."""

from research_agent.retrieval.service import RetrievalService


class FakeVectorStore:
    def __init__(self):
        self.rows = [
            ("chunk-1", "医疗影像中的 Transformer", {"file_name": "a.md"}),
            ("chunk-2", "药物研发中的图神经网络", {"file_name": "b.md"}),
            ("chunk-3", "医疗影像 CT 诊断", {"file_name": "c.md"}),
        ]
        self.rebuild_calls = 0

    def get_all_documents(self):
        self.rebuild_calls += 1
        return (
            [row[0] for row in self.rows],
            [row[1] for row in self.rows],
            [row[2] for row in self.rows],
        )


def test_bm25_is_built_lazily_from_the_shared_vector_store():
    store = FakeVectorStore()
    service = RetrievalService(lambda: store)

    first = service.get_bm25()
    second = service.get_bm25()

    assert first is second
    assert first.is_indexed
    assert store.rebuild_calls == 1
    assert first.search("医疗影像 CT")


def test_rebuild_refreshes_the_existing_bm25_instance():
    store = FakeVectorStore()
    service = RetrievalService(lambda: store)
    bm25 = service.get_bm25()

    store.rows.append(("chunk-4", "临床试验数据", {"file_name": "d.md"}))
    count = service.rebuild_bm25()

    assert count == 4
    assert service.get_bm25() is bm25
    assert bm25.search("临床试验")
