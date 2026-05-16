"""
Graph Semantic Retrieval Engine
-------------------------------
Features:
1. Entity Consolidation
2. Neighborhood Embeddings
3. Graph Traversal Retrieval
4. Query Expansion
5. Semantic Reranking

Requirements:
pip install neo4j sentence-transformers scikit-learn numpy

Architecture:
Neo4j Graph
    ↓
Semantic Expansion
    ↓
Neighborhood Embeddings
    ↓
Cross-Entity Retrieval
"""

from neo4j import GraphDatabase

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

import numpy as np
import json


# =========================================================
# MODELS
# =========================================================
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

cross_encoder = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


# =========================================================
# GRAPH ENGINE
# =========================================================
class SemanticGraphRetriever:

    def __init__(self):

        with open(
            "neo4j_settings.json",
            "r"
        ) as f:

            settings = json.load(f)

        self.driver = (
            GraphDatabase.driver(

                settings["NEO4J_URI"],

                auth=(

                    settings[
                        "NEO4J_USERNAME"
                    ],

                    settings[
                        "NEO4J_PASSWORD"
                    ]
                )
            )
        )

    # =====================================================
    # CLOSE
    # =====================================================
    def close(self):

        self.driver.close()

    # =====================================================
    # ENTITY EMBEDDING
    # =====================================================
    def create_entity_embedding(

        self,

        entity_data
    ):

        text = f"""
        Entity:
        {entity_data.get("name", "")}

        Domain:
        {entity_data.get("domain", "")}

        Subdomain:
        {entity_data.get("subdomain", "")}

        Topics:
        {", ".join(
            entity_data.get(
                "topics",
                []
            )
        )}

        Description:
        {entity_data.get(
            "description",
            ""
        )}

        Context:
        {entity_data.get(
            "text",
            ""
        )}
        """

        embedding = (
            embedding_model.encode(
                text
            )
        )

        return embedding

    # =====================================================
    # GET ALL ENTITIES
    # =====================================================
    def get_all_entities(self):

        query = """
        MATCH (e:Entity)

        OPTIONAL MATCH
        (e)-[:HAS_TOPIC]->(t)

        RETURN
            e.name AS name,
            e.description AS description,
            e.text AS text,
            e.subdomain AS subdomain,
            collect(t.name) AS topics
        """

        with self.driver.session() as session:

            results = session.run(
                query
            )

            return [

                record.data()

                for record in results
            ]

    # =====================================================
    # ENTITY CONSOLIDATION
    # =====================================================
    def consolidate_entities(

        self,

        similarity_threshold=0.85
    ):

        entities = self.get_all_entities()

        embeddings = []

        for entity in entities:

            embeddings.append(

                self.create_entity_embedding(
                    entity
                )
            )

        embeddings = np.array(
            embeddings
        )

        similarity_matrix = (
            cosine_similarity(
                embeddings
            )
        )

        merged_pairs = []

        for i in range(
            len(entities)
        ):

            for j in range(
                i + 1,
                len(entities)
            ):

                similarity = (
                    similarity_matrix[i][j]
                )

                if similarity < similarity_threshold:
                    continue

                # ---------------------------------
                # Subdomain check
                # ---------------------------------
                if (
                    entities[i][
                        "subdomain"
                    ]
                    !=
                    entities[j][
                        "subdomain"
                    ]
                ):
                    continue

                merged_pairs.append({

                    "entity_1":
                        entities[i]["name"],

                    "entity_2":
                        entities[j]["name"],

                    "similarity":
                        float(similarity)
                })

        return merged_pairs

    # =====================================================
    # NEIGHBORHOOD EMBEDDING
    # =====================================================
    def create_neighborhood_embedding(

        self,

        entity_name
    ):

        query = """
        MATCH (e:Entity {
            name: $entity_name
        })

        OPTIONAL MATCH
        (e)-[r]-(neighbor)

        RETURN
            e.name AS entity,
            e.description AS description,
            e.text AS text,
            collect(neighbor.name)
                AS neighbors
        """

        with self.driver.session() as session:

            result = session.run(

                query,

                entity_name=entity_name
            ).single()

        if not result:
            return None

        data = result.data()

        neighborhood_text = f"""
        Entity:
        {data["entity"]}

        Description:
        {data["description"]}

        Context:
        {data["text"]}

        Neighbors:
        {", ".join(
            data["neighbors"]
        )}
        """

        embedding = (
            embedding_model.encode(
                neighborhood_text
            )
        )

        return {

            "entity": entity_name,

            "embedding": embedding,

            "neighbors":
                data["neighbors"]
        }

    # =====================================================
    # QUERY EXPANSION
    # =====================================================
    def expand_query(

        self,

        query_entity,

        depth=2
    ):

        cypher = f"""
        MATCH path = (

            e:Entity {{
                name: $query_entity
            }}

        )-[*1..{depth}]-(related)

        RETURN DISTINCT
            related.name AS entity
        """

        with self.driver.session() as session:

            results = session.run(

                cypher,

                query_entity=query_entity
            )

            expanded_entities = [

                record["entity"]

                for record in results
            ]

        return expanded_entities

    # =====================================================
    # GRAPH TRAVERSAL RETRIEVAL
    # =====================================================
    def graph_traversal_retrieval(

        self,

        entity_name,

        depth=2
    ):

        cypher = f"""
        MATCH path = (

            e:Entity {{
                name: $entity_name
            }}

        )-[*1..{depth}]-(related)

        RETURN DISTINCT
            related.name AS entity,
            related.description
                AS description,
            related.text AS text
        """

        with self.driver.session() as session:

            results = session.run(

                cypher,

                entity_name=entity_name
            )

            retrieved = [

                record.data()

                for record in results
            ]

        return retrieved

    # =====================================================
    # SEMANTIC RERANKING
    # =====================================================
    def semantic_rerank(

        self,

        query,

        retrieved_entities,

        top_k=10
    ):

        pairs = []

        for entity in retrieved_entities:

            text = f"""
            Entity:
            {entity.get("entity", "")}

            Description:
            {entity.get(
                "description",
                ""
            )}

            Context:
            {entity.get(
                "text",
                ""
            )}
            """

            pairs.append(
                (query, text)
            )

        scores = cross_encoder.predict(
            pairs
        )

        reranked = []

        for entity, score in zip(

            retrieved_entities,

            scores
        ):

            entity[
                "semantic_score"
            ] = float(score)

            reranked.append(entity)

        reranked = sorted(

            reranked,

            key=lambda x:
                x["semantic_score"],

            reverse=True
        )

        return reranked[:top_k]

    # =========================================================
    # COMPLETE RETRIEVAL (MULTI ENTITY)
    # =========================================================
    def retrieve(

        self,

        query_entities,

        depth=2,

        top_k=10
    ):

        """
        Supports:
        - single entity string
        - list of entities

        Example:
            "transformer"

        OR

            [
                "transformer",
                "machine translation"
            ]
        """

        # =====================================================
        # NORMALIZE INPUT
        # =====================================================
        if isinstance(
            query_entities,
            str
        ):

            query_entities = [
                query_entities
            ]

        # =====================================================
        # EXPANDED ENTITIES
        # =====================================================
        all_expanded_entities = set()

        # =====================================================
        # RETRIEVED RESULTS
        # =====================================================
        all_retrieved = []

        # =====================================================
        # PROCESS EACH ENTITY
        # =====================================================
        for entity in query_entities:

            # -------------------------------------------------
            # Query expansion
            # -------------------------------------------------
            expanded = self.expand_query(

                entity,

                depth
            )

            all_expanded_entities.update(
                expanded
            )

            # -------------------------------------------------
            # Graph traversal retrieval
            # -------------------------------------------------
            retrieved = (
                self.graph_traversal_retrieval(

                    entity,

                    depth
                )
            )

            all_retrieved.extend(
                retrieved
            )

        # =====================================================
        # DEDUPLICATE RETRIEVED
        # =====================================================
        unique_results = {}

        for result in all_retrieved:

            entity_name = result.get(
                "entity",
                ""
            )

            if not entity_name:
                continue

            unique_results[
                entity_name
            ] = result

        unique_results = list(
            unique_results.values()
        )

        # =====================================================
        # QUERY STRING
        # =====================================================
        combined_query = " ".join(
            query_entities
        )

        # =====================================================
        # SEMANTIC RERANKING
        # =====================================================
        reranked = self.semantic_rerank(

            combined_query,

            unique_results,

            top_k
        )

        # =====================================================
        # RETURN
        # =====================================================
        return {

            "query_entities":
                query_entities,

            "expanded_entities":
                list(
                    all_expanded_entities
                ),

            "results":
                reranked
        }


# =========================================================
# EXAMPLE
# =========================================================
if __name__ == "__main__":

    retriever = (
        SemanticGraphRetriever()
    )

    # =====================================================
    # ENTITY CONSOLIDATION
    # =====================================================
    merged = retriever.consolidate_entities()

    print("\nMERGE CANDIDATES:\n")

    for item in merged[:10]:

        print(item)

    # =====================================================
    # QUERY EXPANSION
    # =====================================================
    expanded = retriever.expand_query(
        "transformer"
    )

    print("\nEXPANDED:\n")

    print(expanded)

    # =====================================================
    # COMPLETE RETRIEVAL
    # =====================================================
    results = retriever.retrieve(

        query_entity="transformer",

        depth=2,

        top_k=5
    )

    print("\nRESULTS:\n")

    for result in results["results"]:

        print("=" * 80)

        print(
            result["entity"]
        )

        print(
            result[
                "semantic_score"
            ]
        )

        print(
            result["description"]
        )