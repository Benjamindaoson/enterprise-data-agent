"""Tests for dependency-light hybrid retrieval used by governed NL2SQL."""

from eiw.nl2sql.retrieval import (
    DeterministicDenseRetriever,
    HeuristicReranker,
    HybridRetrievalService,
    InMemoryBM25Retriever,
    RetrievalCandidate,
    RetrievalHit,
    reciprocal_rank_fusion,
)


def _candidates() -> list[RetrievalCandidate]:
    return [
        RetrievalCandidate(
            object_id="metric:net_sales",
            object_type="metric",
            text="net sales revenue sales amount business revenue",
            metadata={"name": "Net Sales"},
        ),
        RetrievalCandidate(
            object_id="metric:units",
            object_type="metric",
            text="units quantity bottles ordered volume",
            metadata={"name": "Units"},
        ),
        RetrievalCandidate(
            object_id="dimension:region",
            object_type="dimension",
            text="region geography market territory",
            metadata={"name": "Region"},
        ),
    ]


def test_bm25_prefers_explicit_sales_match() -> None:
    hits = InMemoryBM25Retriever().retrieve("sales revenue", _candidates(), top_k=3)
    assert hits[0].candidate.object_id == "metric:net_sales"


def test_dense_retriever_is_deterministic() -> None:
    retriever = DeterministicDenseRetriever()
    first = retriever.retrieve("regional revenue", _candidates(), top_k=3)
    second = retriever.retrieve("regional revenue", _candidates(), top_k=3)
    assert [(hit.candidate.object_id, hit.score) for hit in first] == [
        (hit.candidate.object_id, hit.score) for hit in second
    ]


def test_rrf_deduplicates_and_preserves_source_ranks() -> None:
    candidates = _candidates()
    lexical = [
        RetrievalHit(candidates[0], 3.0),
        RetrievalHit(candidates[2], 2.0),
    ]
    dense = [
        RetrievalHit(candidates[2], 0.9),
        RetrievalHit(candidates[0], 0.8),
    ]
    fused = reciprocal_rank_fusion(
        {"lexical": lexical, "dense": dense},
        k=60,
    )
    assert len(fused) == 2
    by_id = {hit.candidate.object_id: hit for hit in fused}
    assert by_id["metric:net_sales"].source_ranks == {"lexical": 1, "dense": 2}
    assert by_id["dimension:region"].source_ranks == {"lexical": 2, "dense": 1}


def test_reranker_rewards_explicit_business_phrase() -> None:
    candidates = _candidates()
    hits = [
        RetrievalHit(candidates[1], 0.5),
        RetrievalHit(candidates[0], 0.4),
    ]
    reranked = HeuristicReranker().rerank("show net sales", hits, top_n=2)
    assert reranked[0].candidate.object_id == "metric:net_sales"


def test_all_retrieval_modes_are_supported() -> None:
    service = HybridRetrievalService()
    for mode in sorted(service.MODES):
        hits = service.retrieve("sales by region", _candidates(), top_k=2, mode=mode)
        assert len(hits) <= 2
        assert hits


def test_protected_candidate_gets_rerank_bonus() -> None:
    candidate = RetrievalCandidate(
        object_id="metric:approved",
        object_type="metric",
        text="metric",
        protected=True,
    )
    result = HeuristicReranker().rerank(
        "metric",
        [RetrievalHit(candidate, 0.1)],
        top_n=1,
    )
    assert result[0].score > 0.1
