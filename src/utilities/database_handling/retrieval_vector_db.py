"""
Hybrid Retrieval Pipeline
-------------------------
Features:
- Dense Retrieval
- BM25 Retrieval
- Reciprocal Rank Fusion (RRF)
- Cross Encoder Reranking

Works with:
- ChromaDB
- Persistent vector DB
- PKMS Graph RAG

Install:
pip install chromadb sentence-transformers rank-bm25 torch
"""

import chromadb
import numpy as np
import re

from rank_bm25 import BM25Okapi

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)


# =========================================================
# EMBEDDING MODEL
# =========================================================
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# =========================================================
# CROSS ENCODER
# =========================================================
cross_encoder = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


# =========================================================
# CHROMA CLIENT
# =========================================================
client = chromadb.PersistentClient(
    path="./vector_db"
)

DEFAULT_COLLECTION_NAME = "pkms"


def _normalize_collection_name(domain=None):

    if not domain:
        return DEFAULT_COLLECTION_NAME

    normalized = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(domain).strip().lower()
    ).strip("_")

    if not normalized:
        return DEFAULT_COLLECTION_NAME

    return f"{DEFAULT_COLLECTION_NAME}_{normalized}"


def _get_collection(domain=None):

    return client.get_or_create_collection(
        _normalize_collection_name(domain)
    )


# =========================================================
# BM25 INDEX
# =========================================================
class BM25Retriever:

    def __init__(self, domain=None):

        self.collection = _get_collection(domain)

        self.documents = []

        self.ids = []

        self.tokenized_docs = []

        self.bm25 = None

    # =====================================================
    # LOAD FROM CHROMA
    # =====================================================
    def load_documents(self):

        results = self.collection.get(
            include=[
                "documents",
                "metadatas"
            ]
        )
       
        self.metadatas = results[
        "metadatas"
        ]
        self.documents = results[
            "documents"
        ]

        self.ids = results["ids"]

        self.tokenized_docs = [

            doc.lower().split()

            for doc in self.documents
        ]

        if len(self.tokenized_docs) > 0:
            self.bm25 = BM25Okapi(
                self.tokenized_docs
            )

    # =====================================================
    # SEARCH
    # =====================================================
    def search(

        self,

        query,

        top_k=10
    ):

        if not self.bm25:
            return []

        tokenized_query = (
            query.lower().split()
        )

        scores = self.bm25.get_scores(
            tokenized_query
        )

        ranked_indices = np.argsort(
            scores
        )[::-1][:top_k]

        results = []

        for idx in ranked_indices:

            results.append({

                "id": self.ids[idx],

                "document":
                    self.documents[idx],
                    
                "metadata":
                    self.metadatas[idx],

                "entities":
                    self.metadatas[idx].get(
                    "entities",
                    ""
                ),
                    
                "tags":
                    self.metadatas[idx].get(
                    "tags",
                    ""
                ),

                "score":
                    float(scores[idx]),

                "retrieval":
                    "bm25"
            })

        return results


# =========================================================
# DENSE RETRIEVAL
# =========================================================
def dense_search(

    query,

    domain=None,

    top_k=10
):

    collection = _get_collection(domain)

    query_embedding = (
        embedding_model.encode(
            query
        ).tolist()
    )

    results = collection.query(

        query_embeddings=[
            query_embedding
        ],

        n_results=top_k,

        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    dense_results = []

    for i in range(

        len(results["ids"][0])
    ):

        dense_results.append({

            "id":
                results["ids"][0][i],

            "document":
                results["documents"][0][i],

            "metadata":
                results["metadatas"][0][i],
                
            "entities":
                results["metadatas"][0][i].get(
                "entities",
                ""
                ),

            "tags":
                results["metadatas"][0][i].get(
                "tags",
                ""
                ),

            "score": float(
                    results["distances"][0][i]),


            "retrieval":
                "dense"
        })

    return dense_results


# =========================================================
# RRF FUSION
# =========================================================
def reciprocal_rank_fusion(

    result_lists,

    k=60
):

    fused_scores = {}

    document_map = {}

    # ---------------------------------------------
    # Combine rankings
    # ---------------------------------------------
    for results in result_lists:

        for rank, result in enumerate(results):

            doc_id = result["id"]

            document_map[
                doc_id
            ] = result

            score = 1 / (
                k + rank + 1
            )

            fused_scores[
                doc_id
            ] = fused_scores.get(
                doc_id,
                0
            ) + score

    # ---------------------------------------------
    # Sort
    # ---------------------------------------------
    ranked = sorted(

        fused_scores.items(),

        key=lambda x: x[1],

        reverse=True
    )

    fused_results = []

    for doc_id, score in ranked:

        result = document_map[
            doc_id
        ]

        result["rrf_score"] = score

        fused_results.append(
            result
        )

    return fused_results


# =========================================================
# CROSS ENCODER RERANK
# =========================================================
def rerank_cross_encoder(

    query,

    results,

    top_k=10
):

    pairs = [

        (
            query,
            result["document"]
        )

        for result in results
    ]

    scores = cross_encoder.predict(
        pairs
    )

    reranked = []

    for result, score in zip(
        results,
        scores
    ):

        result[
            "cross_score"
        ] = float(score)

        reranked.append(
            result
        )

    reranked = sorted(

        reranked,

        key=lambda x: x[
            "cross_score"
        ],

        reverse=True
    )

    return reranked[:top_k]


# =========================================================
# MAIN RETRIEVAL
# =========================================================
class HybridRetriever:

    def __init__(self, domain=None):

        self.domain = domain

        self.bm25 = BM25Retriever(domain=domain)

        self.bm25.load_documents()

    # =====================================================
    # SEARCH
    # =====================================================
    def search(

        self,

        query,

        domain=None,

        dense_k=15,

        bm25_k=15,

        final_k=5
    ):

        active_domain = domain if domain is not None else self.domain

        bm25_retriever = self.bm25
        if active_domain != self.domain:
            bm25_retriever = BM25Retriever(domain=active_domain)
            bm25_retriever.load_documents()

        # -----------------------------------------
        # Dense retrieval
        # -----------------------------------------
        dense_results = dense_search(

            query,

            domain=active_domain,

            top_k=dense_k
        )

        # -----------------------------------------
        # BM25 retrieval
        # -----------------------------------------
        bm25_results = bm25_retriever.search(

            query,

            top_k=bm25_k
        )

        # -----------------------------------------
        # RRF fusion
        # -----------------------------------------
        fused_results = (
            reciprocal_rank_fusion([

                dense_results,

                bm25_results
            ])
        )

        # -----------------------------------------
        # Cross encoder reranking
        # -----------------------------------------
        reranked = rerank_cross_encoder(

            query,

            fused_results,

            top_k=final_k
        )

        return reranked
