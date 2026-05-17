"""
semantic_entity_notes_manager.py
--------------------------------
Features:
- Hybrid semantic entity search
- Exact entity matching
- Temporal user notes
- Timeline retrieval
- Note updates
- Note deletion
- Semantic entity resolution

Graph Structure:

(:Entity)
    -[:HAS_NOTE]->
(:Note)

Install:
pip install neo4j sentence-transformers scikit-learn numpy
"""

from neo4j import GraphDatabase

from sentence_transformers import (
    SentenceTransformer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

from datetime import datetime

import numpy as np
import uuid
import json


# =========================================================
# EMBEDDING MODEL
# =========================================================
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# =========================================================
# ENTITY NOTES MANAGER
# =========================================================
class SemanticEntityNotesManager:

    # =====================================================
    # INIT
    # =====================================================
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
    # FETCH ALL ENTITIES
    # =====================================================
    def fetch_all_entities(self):

        query = """
        MATCH (e:Entity)

        RETURN
            e.name AS entity,
            e.description AS description,
            e.subdomain AS subdomain
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
    # HYBRID ENTITY SEARCH
    # =====================================================
    def search_entities(

        self,

        query_text,

        top_k=10
    ):

        entities = (
            self.fetch_all_entities()
        )

        if not entities:
            return []

        query_lower = (
            query_text.lower()
            .strip()
        )

        # -------------------------------------------------
        # Entity semantic texts
        # -------------------------------------------------
        entity_texts = []

        for item in entities:

            text = f"""
            Entity:
            {item.get("entity", "")}

            Description:
            {item.get("description", "")}
            """

            entity_texts.append(text)

        # -------------------------------------------------
        # Embeddings
        # -------------------------------------------------
        query_embedding = (
            embedding_model.encode(
                query_text
            )
        )

        entity_embeddings = (
            embedding_model.encode(
                entity_texts
            )
        )

        semantic_scores = (
            cosine_similarity(

                [query_embedding],

                entity_embeddings
            )[0]
        )

        results = []

        # -------------------------------------------------
        # Score entities
        # -------------------------------------------------
        for idx, entity in enumerate(
            entities
        ):

            entity_name = (
                entity.get(
                    "entity",
                    ""
                )
                .lower()
                .strip()
            )

            semantic_score = float(
                semantic_scores[idx]
            )

            # ---------------------------------------------
            # Exact match bonus
            # ---------------------------------------------
            exact_score = 0

            if entity_name == query_lower:

                exact_score = 1.0

            # ---------------------------------------------
            # Substring bonus
            # ---------------------------------------------
            substring_score = 0

            if query_lower in entity_name:

                substring_score = 0.5

            # ---------------------------------------------
            # Token overlap
            # ---------------------------------------------
            query_tokens = set(
                query_lower.split()
            )

            entity_tokens = set(
                entity_name.split()
            )

            overlap = len(

                query_tokens
                &
                entity_tokens
            )

            overlap_score = (
                overlap
                /
                max(
                    len(query_tokens),
                    1
                )
            )

            # ---------------------------------------------
            # Final score
            # ---------------------------------------------
            final_score = (

                0.5 * semantic_score

                +

                0.3 * overlap_score

                +

                exact_score

                +

                substring_score
            )

            results.append({

                "entity":
                    entity[
                        "entity"
                    ],

                "description":
                    entity.get(
                        "description",
                        ""
                    ),

                "subdomain":
                    entity.get(
                        "subdomain",
                        ""
                    ),

                "semantic_score":
                    semantic_score,

                "overlap_score":
                    overlap_score,

                "final_score":
                    final_score
            })

        # -------------------------------------------------
        # Sort
        # -------------------------------------------------
        results = sorted(

            results,

            key=lambda x:
                x["final_score"],

            reverse=True
        )

        return results[:top_k]

    # =====================================================
    # FETCH ENTITY
    # =====================================================
    def fetch_entity(

        self,

        entity_name
    ):

        query = """
        MATCH (e:Entity {
            name: $entity_name
        })

        OPTIONAL MATCH
        (e)-[:HAS_NOTE]->(n:Note)

        RETURN
            e.name AS entity,

            e.description AS description,

            e.subdomain AS subdomain,

            collect({

                note_id: n.note_id,

                text: n.text,

                timestamp: n.timestamp,

                source: n.source,

                confidence: n.confidence

            }) AS notes
        """

        with self.driver.session() as session:

            result = session.run(

                query,

                entity_name=entity_name
            ).single()

            if not result:
                return None

            return result.data()

    # =====================================================
    # FETCH NOTES
    # =====================================================
    def fetch_notes(

        self,

        entity_name
    ):

        query = """
        MATCH (e:Entity {
            name: $entity_name
        })

        OPTIONAL MATCH
        (e)-[:HAS_NOTE]->(n:Note)

        RETURN

            n.note_id AS note_id,

            n.text AS text,

            n.timestamp AS timestamp,

            n.source AS source,

            n.confidence AS confidence

        ORDER BY n.timestamp DESC
        """

        with self.driver.session() as session:

            results = session.run(

                query,

                entity_name=entity_name
            )

            return [

                record.data()

                for record in results
            ]

    # =====================================================
    # FETCH ENTITY TIMELINE
    # =====================================================
    def fetch_entity_timeline(

        self,

        entity_name
    ):

        query = """
        MATCH (e:Entity {
            name: $entity_name
        })

        OPTIONAL MATCH
        (e)-[:HAS_NOTE]->(n:Note)

        RETURN

            n.text AS note,

            n.timestamp AS timestamp

        ORDER BY n.timestamp ASC
        """

        with self.driver.session() as session:

            results = session.run(

                query,

                entity_name=entity_name
            )

            return [

                record.data()

                for record in results
            ]

    # =====================================================
    # ADD NOTE
    # =====================================================
    def add_note(

        self,

        entity_name,

        note_text,

        confidence=1.0
    ):

        timestamp = (
            datetime.utcnow()
            .isoformat()
        )

        note_id = str(
            uuid.uuid4()
        )

        query = """
        MATCH (e:Entity {
            name: $entity_name
        })

        CREATE (n:Note {

            note_id: $note_id,

            text: $note_text,

            timestamp: $timestamp,

            source: "user",

            confidence: $confidence
        })

        MERGE (e)-[:HAS_NOTE]->(n)

        RETURN n
        """

        with self.driver.session() as session:

            result = session.run(

                query,

                entity_name=entity_name,

                note_id=note_id,

                note_text=note_text,

                timestamp=timestamp,

                confidence=confidence
            )

            return result.single()

    # =====================================================
    # UPDATE NOTE
    # =====================================================
    def update_note(

        self,

        note_id,

        updated_text
    ):

        updated_timestamp = (
            datetime.utcnow()
            .isoformat()
        )

        query = """
        MATCH (n:Note {
            note_id: $note_id
        })

        SET

            n.text = $updated_text,

            n.updated_at =
                $updated_timestamp

        RETURN n
        """

        with self.driver.session() as session:

            result = session.run(

                query,

                note_id=note_id,

                updated_text=updated_text,

                updated_timestamp=
                    updated_timestamp
            )

            return result.single()

    # =====================================================
    # DELETE NOTE
    # =====================================================
    def delete_note(

        self,

        note_id
    ):

        query = """
        MATCH (n:Note {
            note_id: $note_id
        })

        DETACH DELETE n
        """

        with self.driver.session() as session:

            session.run(

                query,

                note_id=note_id
            )

    # =====================================================
    # INTERACTIVE ENTITY UPDATE
    # =====================================================
    def interactive_entity_update(

        self,

        query_entity,

        note_text,

        top_k=5
    ):

        candidates = (
            self.search_entities(

                query_entity,

                top_k
            )
        )

        if not candidates:

            print(
                "\nNo matching entities found."
            )

            return

        # -------------------------------------------------
        # Show candidates
        # -------------------------------------------------
        print("\nMATCHING ENTITIES:\n")

        for idx, candidate in enumerate(
            candidates
        ):

            print("=" * 80)

            print(
                f"[{idx}] "
                f"{candidate['entity']}"
            )

            print(
                f"FINAL SCORE: "
                f"{candidate['final_score']:.4f}"
            )

            print(
                f"SEMANTIC SCORE: "
                f"{candidate['semantic_score']:.4f}"
            )

            print(
                f"SUBDOMAIN: "
                f"{candidate['subdomain']}"
            )

            print()

        # -------------------------------------------------
        # User selection
        # -------------------------------------------------
        selected = int(

            input(
                "\nSelect entity index: "
            )
        )

        selected_entity = candidates[
            selected
        ]["entity"]

        # -------------------------------------------------
        # Add note
        # -------------------------------------------------
        self.add_note(

            entity_name=
                selected_entity,

            note_text=note_text
        )

        print(

            f"\nNote added to: "
            f"{selected_entity}"
        )


# =========================================================
# EXAMPLE
# =========================================================
if __name__ == "__main__":

    manager = (
        SemanticEntityNotesManager()
    )

    # =====================================================
    # SEARCH
    # =====================================================
    matches = manager.search_entities(
        "transformer"
    )

    print("\nSEARCH RESULTS:\n")

    for item in matches:

        print(item)

    # =====================================================
    # INTERACTIVE UPDATE
    # =====================================================
    manager.interactive_entity_update(

        query_entity="transformer",

        note_text="""
        Transformers scale efficiently
        for large language models.
        """
    )

    # =====================================================
    # FETCH TIMELINE
    # =====================================================
    timeline = (
        manager.fetch_entity_timeline(
            "transformer model"
        )
    )

    print("\nTIMELINE:\n")

    for item in timeline:

        print(item)

    manager.close()