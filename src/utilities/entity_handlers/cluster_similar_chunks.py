from collections import defaultdict
from sentence_transformers import (
    SentenceTransformer
)

from sklearn.cluster import (
    AgglomerativeClustering
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

import numpy as np


# =========================================================
# EMBEDDING MODEL
# =========================================================
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# =========================================================
# CREATE EMBEDDINGS
# =========================================================
def create_embeddings(chunks):

    texts = [

        chunk["text"]

        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        show_progress_bar=True
    )

    return embeddings


# =========================================================
# CLUSTER CHUNKS
# =========================================================
def cluster_chunks(

    chunks,

    similarity_threshold=0.75
):

    # ---------------------------------------------
    # Create embeddings
    # ---------------------------------------------
    embeddings = create_embeddings(
        chunks
    )

    # ---------------------------------------------
    # Cosine distance matrix
    # ---------------------------------------------
    similarity_matrix = cosine_similarity(
        embeddings
    )

    distance_matrix = (
        1 - similarity_matrix
    )

    # ---------------------------------------------
    # Agglomerative clustering
    # ---------------------------------------------
    clustering = (
        AgglomerativeClustering(

            metric="precomputed",

            linkage="average",

            distance_threshold=(
                1 - similarity_threshold
            ),

            n_clusters=None
        )
    )

    labels = clustering.fit_predict(
        distance_matrix
    )

    # ---------------------------------------------
    # Group chunks
    # ---------------------------------------------
    clustered = defaultdict(list)

    for label, chunk in zip(
        labels,
        chunks
    ):

        clustered[label].append(
            chunk
        )

    return clustered


# =========================================================
# MERGE ENTITIES
# =========================================================
def merge_entities(cluster_chunks):

    entity_frequency = defaultdict(int)

    for chunk in cluster_chunks:

        entities = chunk.get(
            "entities",
            []
        )

        for entity in entities:

            entity = entity.lower().strip()

            entity_frequency[
                entity
            ] += 1

    # ---------------------------------------------
    # Sort by importance
    # ---------------------------------------------
    merged_entities = sorted(

        entity_frequency.items(),

        key=lambda x: x[1],

        reverse=True
    )

    return [

        entity

        for entity, freq in (
            merged_entities
        )
    ]


# =========================================================
# MERGE RELATIONSHIPS
# =========================================================
def merge_relationships(cluster_chunks):

    relationship_frequency = (
        defaultdict(int)
    )

    merged_relationships = []

    for chunk in cluster_chunks:

        relationships = chunk.get(
            "relationships",
            []
        )

        for rel in relationships:

            source = rel.get(
                "source",
                ""
            ).lower().strip()

            relation = rel.get(
                "relation",
                ""
            ).upper().strip()

            target = rel.get(
                "target",
                ""
            ).lower().strip()

            key = (
                source,
                relation,
                target
            )

            relationship_frequency[
                key
            ] += 1

    # ---------------------------------------------
    # Consolidate
    # ---------------------------------------------
    for (

        source,
        relation,
        target

    ), freq in (
        relationship_frequency.items()
    ):

        merged_relationships.append({

            "source": source,

            "relation": relation,

            "target": target,

            "weight": freq
        })

    # ---------------------------------------------
    # Sort strongest first
    # ---------------------------------------------
    merged_relationships = sorted(

        merged_relationships,

        key=lambda x: x["weight"],

        reverse=True
    )

    return merged_relationships


# =========================================================
# MERGE CLUSTER
# =========================================================
def merge_cluster(

    cluster_id,

    cluster_chunks
):

    merged_text = "\n\n".join([

        chunk["text"]

        for chunk in cluster_chunks
    ])

    merged_entities = merge_entities(
        cluster_chunks
    )

    merged_relationships = (
        merge_relationships(
            cluster_chunks
        )
    )

    return {

        "cluster_id": cluster_id,

        "text": merged_text,

        "entities": (
            merged_entities
        ),

        "relationships": (
            merged_relationships
        ),

        "chunk_count": len(
            cluster_chunks
        )
    }


# =========================================================
# MAIN PIPELINE
# =========================================================
def consolidate_chunks(

    chunks,

    similarity_threshold=0.75
):

    # ---------------------------------------------
    # Cluster
    # ---------------------------------------------
    clustered = cluster_chunks(

        chunks,

        similarity_threshold
    )

    consolidated = []

    # ---------------------------------------------
    # Merge each cluster
    # ---------------------------------------------
    for (

        cluster_id,

        cluster_group

    ) in clustered.items():

        merged = merge_cluster(

            cluster_id,

            cluster_group
        )

        consolidated.append(
            merged
        )

    return consolidated
